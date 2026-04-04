export type Download = {
  id: string;
  title: string;
  source_url: string;
  media_type: string;
  destination: string;
  status: string;
  progress_pct: number;
  speed_mbps: number | null;
  eta_s: number | null;
  filename: string | null;
  created_at: string;
  completed_at: string | null;
  error: string | null;
  debrid_url: string | null;
};

export type DownloadCreated = {
  download_id: string;
  status: string;
};

export type StartDownloadPayload = {
  source_url: string;
  title: string;
  media_type: string;
  destination: 'server' | 'client';
};
