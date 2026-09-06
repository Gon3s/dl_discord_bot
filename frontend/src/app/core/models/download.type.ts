import type { MediaType } from '../constants/media';
import type { DownloadStatus } from '../constants/download-status';

export type Download = {
  id: string;
  title: string;
  source_url: string;
  media_type: MediaType;
  destination: string;
  status: DownloadStatus;
  progress_pct: number;
  speed_mbps: number | null;
  eta_s: number | null;
  filename: string | null;
  debrid_url: string | null;
  created_at: string;
  completed_at: string | null;
  error: string | null;
};

export type DownloadCreated = {
  download_id: string;
  status: DownloadStatus;
};

export type StartDownloadPayload = {
  source_url: string;
  title: string;
  media_type: MediaType;
  destination: 'server' | 'client';
  alternative_urls?: string[];
};
