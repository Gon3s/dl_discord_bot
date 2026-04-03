export const ACTIVE_STATUSES = ['scraping', 'resolving', 'debriding', 'downloading'] as const;
export const COMPLETED_STATUSES = ['completed', 'error', 'cancelled'] as const;

export const STATUS_LABEL: Record<string, string> = {
  queued: 'WAITING',
  scraping: 'SCRAPING…',
  resolving: 'RESOLVING…',
  debriding: 'DEBRIDING…',
  downloading: 'DOWNLOADING',
  completed: '✓ DONE',
  error: '✕ ERROR',
  cancelled: 'CANCELLED',
  ready_for_client: 'READY',
};
