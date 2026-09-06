export const DOWNLOAD_STATUSES = [
  'queued',
  'scraping',
  'resolving',
  'debriding',
  'downloading',
  'completed',
  'error',
  'cancelled',
  'ready_for_client',
] as const;

export type DownloadStatus = (typeof DOWNLOAD_STATUSES)[number];
export type HistoryStatus = Extract<DownloadStatus, 'completed' | 'error'>;

export const ACTIVE_STATUSES = ['scraping', 'resolving', 'debriding', 'downloading'] as const satisfies readonly DownloadStatus[];
export const PENDING_STATUSES = ['queued', ...ACTIVE_STATUSES] as const satisfies readonly DownloadStatus[];
export const COMPLETED_STATUSES = ['completed', 'error', 'cancelled', 'ready_for_client'] as const satisfies readonly DownloadStatus[];

export const STATUS_LABEL: Record<DownloadStatus, string> = {
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
