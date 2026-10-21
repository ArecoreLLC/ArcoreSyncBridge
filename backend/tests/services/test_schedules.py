from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.core import CeleryPeriodicTask, SyncDefinition
from app.services.schedule_dispatch import dispatch_due_schedules
from app.services.schedule_service import ScheduleService
from conftest import TestingSessionLocal

NOW = datetime(2026, 1, 15, 12, tzinfo=UTC)


@pytest.fixture
def db():
    with TestingSessionLocal() as session:
        yield session


def make_definition(db):
    definition = SyncDefinition(name='Scheduled sync', source_table_id=uuid4(), sync_mode='ONE_WAY_PUSH', key_strategy='PRIMARY_KEY')
    db.add(definition)
    db.commit()
    return definition


@pytest.mark.parametrize('month,expected_hour', [(1, 14), (7, 13)])
def test_cron_uses_local_timezone_in_winter_and_summer(month, expected_hour):
    runs = ScheduleService.preview_schedule(
        'CRON', cron_expression='0 9 * * *', timezone='America/New_York',
        now=datetime(2026, month, 15, 12, tzinfo=UTC),
    )
    assert len(runs) == 5
    assert runs[0] == datetime(2026, month, 15, expected_hour, tzinfo=UTC)
    assert all(run.tzinfo == UTC for run in runs)


def test_cron_keeps_local_hour_across_daylight_saving_transition():
    runs = ScheduleService.preview_schedule(
        'CRON', cron_expression='0 9 * * *', timezone='America/New_York',
        now=datetime(2026, 3, 7, 12, tzinfo=UTC), count=3,
    )
    assert runs == [
        datetime(2026, 3, 7, 14, tzinfo=UTC),
        datetime(2026, 3, 8, 13, tzinfo=UTC),
        datetime(2026, 3, 9, 13, tzinfo=UTC),
    ]


def test_interval_preview():
    assert ScheduleService.preview_schedule('INTERVAL', 120, now=NOW, count=2) == [
        NOW + timedelta(minutes=2), NOW + timedelta(minutes=4),
    ]


@pytest.mark.parametrize('config', [
    {'schedule_type': 'CRON', 'cron_expression': '@daily'},
    {'schedule_type': 'CRON', 'cron_expression': '* * * * * *'},
    {'schedule_type': 'CRON', 'cron_expression': '0 0 31 2 *'},
    {'schedule_type': 'CRON', 'cron_expression': 'nonsense'},
    {'schedule_type': 'INTERVAL', 'interval_seconds': 59},
    {'schedule_type': 'INTERVAL', 'interval_seconds': 60, 'timezone': 'Invalid/Zone'},
    {'schedule_type': 'INTERVAL', 'interval_seconds': 10**30},
    {'schedule_type': 'UNKNOWN'},
])
def test_invalid_schedule_does_not_mutate_session(db, config):
    definition = make_definition(db)
    with pytest.raises(ValueError):
        ScheduleService(db).enable_schedule(definition.id, **config)
    assert not definition.schedule_enabled
    assert not db.dirty
    assert not db.new


def test_enable_update_disable_and_delete(db):
    definition = make_definition(db)
    service = ScheduleService(db)
    result = service.enable_schedule(definition.id, 'INTERVAL', 120)
    assert result['next_run'].tzinfo == UTC
    task = db.query(CeleryPeriodicTask).one()
    service.enable_schedule(definition.id, 'CRON', cron_expression='0 9 * * *')
    assert db.query(CeleryPeriodicTask).count() == 1
    assert task.interval_seconds is None
    assert task.crontab_hour == '9'
    service.disable_schedule(definition.id)
    assert not task.enabled
    assert definition.next_scheduled_run is None
    assert definition.schedule_type == 'CRON'
    service.delete_schedule(definition.id)
    assert definition.schedule_type is None
    assert definition.schedule_cron_expression is None
    assert definition.schedule_interval_seconds is None
    assert db.query(CeleryPeriodicTask).count() == 0


def make_due(db):
    definition = make_definition(db)
    ScheduleService(db).enable_schedule(definition.id, 'INTERVAL', 120)
    definition.next_scheduled_run = NOW - timedelta(minutes=10)
    db.commit()
    return definition


def test_dispatch_enqueues_once_and_advances_next_run(db):
    definition = make_due(db)
    enqueue = Mock()
    assert dispatch_due_schedules(db, enqueue, now=NOW) == 1
    enqueue.assert_called_once_with(str(definition.id))
    assert dispatch_due_schedules(db, enqueue, now=NOW) == 0
    assert db.query(CeleryPeriodicTask).one().total_run_count == 1
    assert definition.next_scheduled_run == (NOW + timedelta(seconds=120)).replace(tzinfo=None)


@pytest.mark.parametrize('state', ['paused', 'disabled', 'task_disabled', 'future', 'uninitialized'])
def test_dispatch_does_not_enqueue_ineligible_schedules(db, state):
    definition = make_due(db)
    if state == 'paused':
        definition.is_paused = True
    elif state == 'disabled':
        definition.schedule_enabled = False
    elif state == 'task_disabled':
        db.query(CeleryPeriodicTask).one().enabled = False
    elif state == 'future':
        definition.next_scheduled_run = NOW + timedelta(hours=1)
    else:
        definition.next_scheduled_run = None
    db.commit()
    enqueue = Mock()
    assert dispatch_due_schedules(db, enqueue, now=NOW) == 0
    enqueue.assert_not_called()


def test_failed_publish_leaves_schedule_due(db):
    definition = make_due(db)
    original_due = definition.next_scheduled_run
    assert dispatch_due_schedules(db, Mock(side_effect=RuntimeError('Broker unavailable')), now=NOW) == 0
    assert definition.next_scheduled_run == original_due
    assert db.query(CeleryPeriodicTask).one().total_run_count == 0
    assert dispatch_due_schedules(db, Mock(), now=NOW) == 1


def test_preview_api_is_read_only(db):
    client = TestClient(app)
    response = client.post('/api/v1/schedules/preview', json={
        'schedule_type': 'INTERVAL', 'interval_seconds': 120,
    })
    assert response.status_code == 200
    assert len(response.json()) == 5
    assert response.json()[0].endswith('Z')
    assert db.query(CeleryPeriodicTask).count() == 0
    assert db.query(SyncDefinition).count() == 0


def test_preview_api_rejects_bad_timezone():
    response = TestClient(app).post('/api/v1/schedules/preview', json={
        'schedule_type': 'CRON', 'cron_expression': '0 9 * * *', 'timezone': 'Invalid/Zone',
    })
    assert response.status_code == 400
    assert 'timezone' in response.json()['detail']


def test_schedule_api_uses_shared_database_dependency(db):
    definition = make_definition(db)
    response = TestClient(app).post(f'/api/v1/schedules/{definition.id}/enable', json={
        'schedule_type': 'INTERVAL', 'interval_seconds': 60,
    })
    assert response.status_code == 200
    assert db.query(CeleryPeriodicTask).count() == 1
    response = TestClient(app).get(f'/api/v1/schedules/{definition.id}/audit?limit=-1')
    assert response.status_code == 422


def test_preview_requires_authentication(monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, 'AUTH_MODE', 'header')
    response = TestClient(app).post('/api/v1/schedules/preview', json={
        'schedule_type': 'INTERVAL', 'interval_seconds': 60,
    })
    assert response.status_code == 401
