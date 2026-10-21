import React, { useState, useEffect } from 'react';
import { Clock, Calendar, Play, Pause, Trash2 } from 'lucide-react';
import { previewSchedule, enableSchedule, disableSchedule, deleteSchedule, getScheduleAudit } from '../services/api';
import { useToast } from './ui/ToastProvider';
import { useConfirmDialog } from './ui/ConfirmDialogProvider';

interface ScheduleConfigProps {
    syncDefId: string;
    currentConfig?: {
        schedule_enabled?: boolean;
        schedule_type?: string;
        schedule_interval_seconds?: number;
        schedule_cron_expression?: string;
        schedule_timezone?: string;
        next_scheduled_run?: string;
    };
    onSave?: () => void;
}

export default function ScheduleConfig({ syncDefId, currentConfig, onSave }: ScheduleConfigProps) {
    const { showToast } = useToast();
    const { confirm } = useConfirmDialog();
    const [scheduleType, setScheduleType] = useState<'INTERVAL' | 'CRON'>('INTERVAL');
    const [intervalMinutes, setIntervalMinutes] = useState<number>(5);
    const [cronExpression, setCronExpression] = useState<string>('0 0 * * *');
    const [timezone, setTimezone] = useState<string>('UTC');
    const [loading, setLoading] = useState(false);
    const [auditLogs, setAuditLogs] = useState<any[]>([]);
    const [showAudit, setShowAudit] = useState(false);
    const [previewRuns, setPreviewRuns] = useState<string[]>([]);
    const [previewLoading, setPreviewLoading] = useState(false);

    // Invalidate results and ignore responses for an older configuration.
    useEffect(() => {
        let active = true;
        setPreviewRuns([]);
        setPreviewLoading(true);
        const timer = setTimeout(async () => {
            try {
                const runs = await previewSchedule({
                    schedule_type: scheduleType,
                    ...(scheduleType === 'INTERVAL'
                        ? { interval_seconds: intervalMinutes * 60 }
                        : { cron_expression: cronExpression }),
                    timezone,
                });
                if (active) setPreviewRuns(runs);
            } catch {
                // Enable validates input and displays the server's error message.
            } finally {
                if (active) setPreviewLoading(false);
            }
        }, 400);
        return () => { active = false; clearTimeout(timer); };
    }, [scheduleType, intervalMinutes, cronExpression, timezone]);

    // Initialize from currentConfig
    useEffect(() => {
        if (currentConfig) {
            if (currentConfig.schedule_type === 'CRON') {
                setScheduleType('CRON');
                setCronExpression(currentConfig.schedule_cron_expression || '0 0 * * *');
            } else {
                setScheduleType('INTERVAL');
                setIntervalMinutes(Math.floor((currentConfig.schedule_interval_seconds || 300) / 60));
            }
            setTimezone(currentConfig.schedule_timezone || 'UTC');
        }
    }, [currentConfig]);

    const handleEnable = async () => {
        setLoading(true);
        try {
            const config = {
                schedule_type: scheduleType,
                ...(scheduleType === 'INTERVAL' ? {
                    interval_seconds: intervalMinutes * 60
                } : {
                    cron_expression: cronExpression
                }),
                timezone
            };
            await enableSchedule(syncDefId, config);
            showToast({
                title: isEnabled ? 'Schedule updated' : 'Schedule enabled',
                description: 'The sync schedule configuration was saved.',
                variant: 'success',
            });
            if (onSave) onSave();
        } catch (e: any) {
            console.error(e);
            showToast({
                title: 'Schedule save failed',
                description: e.response?.data?.detail || e.message,
                variant: 'error',
            });
        } finally {
            setLoading(false);
        }
    };

    const handleDisable = async () => {
        setLoading(true);
        try {
            await disableSchedule(syncDefId);
            showToast({
                title: 'Schedule disabled',
                description: 'Automatic sync execution is now paused.',
                variant: 'success',
            });
            if (onSave) onSave();
        } catch (e: any) {
            console.error(e);
            showToast({
                title: 'Disable failed',
                description: e.response?.data?.detail || e.message,
                variant: 'error',
            });
        } finally {
            setLoading(false);
        }
    };

    const handleDelete = async () => {
        const confirmed = await confirm({
            title: 'Delete schedule?',
            description: 'Remove this schedule configuration and stop future automated runs.',
            confirmLabel: 'Delete schedule',
            tone: 'danger',
        });
        if (!confirmed) return;
        setLoading(true);
        try {
            await deleteSchedule(syncDefId);
            showToast({
                title: 'Schedule deleted',
                description: 'The schedule configuration was removed.',
                variant: 'success',
            });
            if (onSave) onSave();
        } catch (e: any) {
            console.error(e);
            showToast({
                title: 'Delete failed',
                description: e.response?.data?.detail || e.message,
                variant: 'error',
            });
        } finally {
            setLoading(false);
        }
    };

    const loadAuditLogs = async () => {
        try {
            const logs = await getScheduleAudit(syncDefId, 20);
            setAuditLogs(logs);
            setShowAudit(true);
        } catch (e) {
            console.error(e);
            showToast({
                title: 'Audit log load failed',
                description: 'Failed to load schedule audit logs.',
                variant: 'error',
            });
        }
    };

    const isEnabled = currentConfig?.schedule_enabled;

    return (
        <div className="space-y-6">
            <div className="bg-white dark:bg-dark-surface p-6 rounded border border-gray-200 dark:border-gray-700 shadow-sm">
                <div className="flex justify-between items-start mb-6">
                    <div>
                        <h3 className="text-lg font-bold text-light-text-primary dark:text-dark-text-primary">
                            Schedule Configuration
                        </h3>
                        <p className="text-sm text-light-text-secondary dark:text-dark-text-secondary mt-1">
                            Automate sync execution with intervals or cron expressions
                        </p>
                    </div>
                    <div className="flex items-center space-x-2">
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                            isEnabled
                                ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300'
                                : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400'
                        }`}>
                            {isEnabled ? 'Enabled' : 'Disabled'}
                        </span>
                    </div>
                </div>

                {/* Schedule Type Toggle */}
                <div className="mb-6">
                    <label className="block text-sm font-medium text-light-text-primary dark:text-dark-text-primary mb-2">
                        Schedule Type
                    </label>
                    <div className="flex space-x-3">
                        <button
                            onClick={() => setScheduleType('INTERVAL')}
                            className={`flex-1 flex items-center justify-center space-x-2 px-4 py-3 rounded border transition-colors ${
                                scheduleType === 'INTERVAL'
                                    ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-700 text-blue-700 dark:text-blue-300 ring-1 ring-blue-200 dark:ring-blue-700'
                                    : 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                            }`}
                        >
                            <Clock size={18} />
                            <span className="font-medium text-sm">Interval</span>
                        </button>
                        <button
                            onClick={() => setScheduleType('CRON')}
                            className={`flex-1 flex items-center justify-center space-x-2 px-4 py-3 rounded border transition-colors ${
                                scheduleType === 'CRON'
                                    ? 'bg-purple-50 dark:bg-purple-900/30 border-purple-200 dark:border-purple-700 text-purple-700 dark:text-purple-300 ring-1 ring-purple-200 dark:ring-purple-700'
                                    : 'bg-gray-50 dark:bg-gray-800 border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
                            }`}
                        >
                            <Calendar size={18} />
                            <span className="font-medium text-sm">Cron Expression</span>
                        </button>
                    </div>
                </div>

                {/* Interval Configuration */}
                {scheduleType === 'INTERVAL' && (
                    <div className="mb-6">
                        <label className="block text-sm font-medium text-light-text-primary dark:text-dark-text-primary mb-2">
                            Interval (minutes)
                        </label>
                        <input
                            type="number"
                            min="1"
                            value={intervalMinutes}
                            onChange={(e) => setIntervalMinutes(parseInt(e.target.value) || 1)}
                            className="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 bg-white dark:bg-gray-800 text-light-text-primary dark:text-dark-text-primary"
                        />
                        <p className="text-xs text-light-text-secondary dark:text-dark-text-secondary mt-1">
                            Sync will run every {intervalMinutes} minute{intervalMinutes !== 1 ? 's' : ''}
                            {intervalMinutes < 1 && ' (minimum 1 minute)'}
                        </p>
                    </div>
                )}

                {/* Cron Configuration */}
                {scheduleType === 'CRON' && (
                    <div className="mb-6">
                        <label className="block text-sm font-medium text-light-text-primary dark:text-dark-text-primary mb-2">
                            Cron Expression
                        </label>
                        <input
                            type="text"
                            value={cronExpression}
                            onChange={(e) => setCronExpression(e.target.value)}
                            placeholder="0 0 * * *"
                            className="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 bg-white dark:bg-gray-800 text-light-text-primary dark:text-dark-text-primary font-mono text-sm"
                        />
                        <p className="text-xs text-light-text-secondary dark:text-dark-text-secondary mt-1">
                            Standard cron format: minute hour day month weekday
                        </p>
                        <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-800 rounded text-xs space-y-1">
                            <div className="text-light-text-secondary dark:text-dark-text-secondary">Common examples:</div>
                            <div><code className="font-mono">0 0 * * *</code> - Daily at midnight</div>
                            <div><code className="font-mono">0 */6 * * *</code> - Every 6 hours</div>
                            <div><code className="font-mono">0 9 * * 1</code> - Every Monday at 9 AM</div>
                        </div>
                    </div>
                )}

                {/* Timezone */}
                <div className="mb-6">
                    <label className="block text-sm font-medium text-light-text-primary dark:text-dark-text-primary mb-2">
                        Timezone
                    </label>
                    <select
                        value={timezone}
                        onChange={(e) => setTimezone(e.target.value)}
                        className="w-full border border-gray-300 dark:border-gray-600 rounded px-3 py-2 bg-white dark:bg-gray-800 text-light-text-primary dark:text-dark-text-primary"
                    >
                        <option value="UTC">UTC</option>
                        <option value="America/New_York">America/New_York (EST/EDT)</option>
                        <option value="America/Chicago">America/Chicago (CST/CDT)</option>
                        <option value="America/Denver">America/Denver (MST/MDT)</option>
                        <option value="America/Los_Angeles">America/Los_Angeles (PST/PDT)</option>
                        <option value="Europe/London">Europe/London</option>
                        <option value="Asia/Tokyo">Asia/Tokyo</option>
                    </select>
                </div>

                <div className="mb-6 text-sm" aria-live="polite">
                    <h4 className="font-medium">Upcoming runs ({timezone})</h4>
                    {previewLoading ? <p>Calculating preview...</p> : previewRuns.length ? (
                        <ol className="mt-2 space-y-1">
                            {previewRuns.map((run) => (
                                <li key={run}>{new Date(run).toLocaleString(undefined, { timeZone: timezone, timeZoneName: 'short' })}</li>
                            ))}
                        </ol>
                    ) : <p>Enter a valid schedule to preview upcoming runs.</p>}
                </div>

                {/* Next Scheduled Run */}
                {currentConfig?.next_scheduled_run && (
                    <div className="mb-6 p-3 bg-blue-50 dark:bg-blue-900/20 rounded border border-blue-200 dark:border-blue-800">
                        <div className="text-xs font-medium text-blue-700 dark:text-blue-300 mb-1">Next Scheduled Run</div>
                        <div className="text-sm font-mono text-blue-900 dark:text-blue-200">
                            {new Date(currentConfig.next_scheduled_run).toLocaleString()}
                        </div>
                    </div>
                )}

                {/* Action Buttons */}
                <div className="flex space-x-3">
                    {!isEnabled ? (
                        <button
                            onClick={handleEnable}
                            disabled={loading}
                            className="flex-1 flex items-center justify-center space-x-2 px-4 py-2 bg-green-600 dark:bg-green-700 text-white rounded hover:bg-green-700 dark:hover:bg-green-800 disabled:opacity-50 transition-colors"
                        >
                            <Play size={16} />
                            <span>{loading ? 'Enabling...' : 'Enable Schedule'}</span>
                        </button>
                    ) : (
                        <>
                            <button
                                onClick={handleDisable}
                                disabled={loading}
                                className="flex-1 flex items-center justify-center space-x-2 px-4 py-2 bg-orange-600 dark:bg-orange-700 text-white rounded hover:bg-orange-700 dark:hover:bg-orange-800 disabled:opacity-50 transition-colors"
                            >
                                <Pause size={16} />
                                <span>{loading ? 'Disabling...' : 'Disable Schedule'}</span>
                            </button>
                            <button
                                onClick={handleEnable}
                                disabled={loading}
                                className="flex-1 flex items-center justify-center space-x-2 px-4 py-2 bg-blue-600 dark:bg-blue-700 text-white rounded hover:bg-blue-700 dark:hover:bg-blue-800 disabled:opacity-50 transition-colors"
                            >
                                <Play size={16} />
                                <span>{loading ? 'Updating...' : 'Update Schedule'}</span>
                            </button>
                            <button
                                onClick={handleDelete}
                                disabled={loading}
                                className="px-4 py-2 bg-red-600 dark:bg-red-700 text-white rounded hover:bg-red-700 dark:hover:bg-red-800 disabled:opacity-50 transition-colors"
                                title="Delete Schedule"
                            >
                                <Trash2 size={16} />
                            </button>
                        </>
                    )}
                </div>

                {/* Audit Log Toggle */}
                <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                    <button
                        onClick={loadAuditLogs}
                        className="text-sm text-light-primary dark:text-dark-primary hover:underline"
                    >
                        View Audit Logs
                    </button>
                </div>
            </div>

            {/* Audit Logs */}
            {showAudit && (
                <div className="bg-white dark:bg-dark-surface p-6 rounded border border-gray-200 dark:border-gray-700 shadow-sm">
                    <div className="flex justify-between items-center mb-4">
                        <h4 className="text-md font-bold text-light-text-primary dark:text-dark-text-primary">
                            Schedule Audit Logs
                        </h4>
                        <button
                            onClick={() => setShowAudit(false)}
                            className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
                        >
                            Hide
                        </button>
                    </div>
                    {auditLogs.length === 0 ? (
                        <p className="text-sm text-gray-500">No audit logs yet</p>
                    ) : (
                        <div className="overflow-x-auto">
                            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                                <thead className="bg-gray-50 dark:bg-gray-800">
                                    <tr>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-light-text-secondary dark:text-dark-text-secondary uppercase">
                                            Scheduled Time
                                        </th>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-light-text-secondary dark:text-dark-text-secondary uppercase">
                                            Status
                                        </th>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-light-text-secondary dark:text-dark-text-secondary uppercase">
                                            Details
                                        </th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white dark:bg-dark-surface divide-y divide-gray-200 dark:divide-gray-700">
                                    {auditLogs.map((log: any) => (
                                        <tr key={log.id}>
                                            <td className="px-4 py-2 text-sm font-mono text-light-text-primary dark:text-dark-text-primary">
                                                {new Date(log.scheduled_time).toLocaleString()}
                                            </td>
                                            <td className="px-4 py-2 text-sm">
                                                <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                                                    log.status === 'COMPLETED' ? 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300' :
                                                    log.status === 'SKIPPED' ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300' :
                                                    'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300'
                                                }`}>
                                                    {log.status}
                                                </span>
                                            </td>
                                            <td className="px-4 py-2 text-sm text-light-text-secondary dark:text-dark-text-secondary">
                                                {log.skip_reason || '-'}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
