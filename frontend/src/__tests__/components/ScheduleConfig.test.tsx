import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ScheduleConfig from '@/components/ScheduleConfig';

jest.mock('@/services/api', () => ({
  previewSchedule: jest.fn(),
  enableSchedule: jest.fn(),
  disableSchedule: jest.fn(),
  deleteSchedule: jest.fn(),
  getScheduleAudit: jest.fn(),
}));
jest.mock('@/components/ui/ToastProvider', () => ({
  useToast: () => ({ showToast: jest.fn() }),
}));
jest.mock('@/components/ui/ConfirmDialogProvider', () => ({
  useConfirmDialog: () => ({ confirm: jest.fn() }),
}));

const { previewSchedule, enableSchedule } = jest.requireMock('@/services/api');

beforeEach(() => {
  jest.resetAllMocks();
});

test('previews without enabling and saves the selected configuration', async () => {
  previewSchedule.mockResolvedValue(['2026-01-15T14:00:00Z']);
  enableSchedule.mockResolvedValue({ message: 'Schedule enabled' });
  render(<ScheduleConfig syncDefId="sync-1" />);
  await waitFor(() => expect(previewSchedule).toHaveBeenCalledWith({
    schedule_type: 'INTERVAL', interval_seconds: 300, timezone: 'UTC',
  }));
  expect(enableSchedule).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole('button', { name: 'Enable Schedule' }));
  expect(enableSchedule).toHaveBeenCalledWith('sync-1', {
    schedule_type: 'INTERVAL', interval_seconds: 300, timezone: 'UTC',
  });
});

test('discards a pending preview after the configuration changes', async () => {
  let resolveOld: (runs: string[]) => void = () => {};
  previewSchedule.mockImplementationOnce(() => new Promise<string[]>((resolve) => { resolveOld = resolve; }));
  previewSchedule.mockResolvedValue(['2026-01-16T09:00:00Z']);
  render(<ScheduleConfig syncDefId="sync-1" />);
  await waitFor(() => expect(previewSchedule).toHaveBeenCalledTimes(1));
  await userEvent.click(screen.getByRole('button', { name: 'Cron Expression' }));
  await waitFor(() => expect(previewSchedule).toHaveBeenCalledTimes(2));
  await waitFor(() => expect(screen.queryByText('Calculating preview...')).not.toBeInTheDocument());
  resolveOld(['2026-01-01T00:00:00Z']);
  await waitFor(() => expect(screen.getAllByRole('listitem')).toHaveLength(1));
  expect(screen.getByRole('listitem')).toHaveTextContent('1/16/2026');
});

test('shows guidance when the server rejects a preview', async () => {
  previewSchedule.mockRejectedValue(new Error('Invalid schedule'));
  render(<ScheduleConfig syncDefId="sync-1" />);
  expect(await screen.findByText('Enter a valid schedule to preview upcoming runs.')).toBeInTheDocument();
});
