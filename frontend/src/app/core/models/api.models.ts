export interface SearchResult {
  title: string;
  url: string;
  year: number | null;
  category: string | null;
  quality: string | null;
  language: string | null;
  source: string;
  poster_url: string | null;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  source: string;
}

export interface Download {
  id: string;
  title: string;
  source_url: string;
  media_type: string;
  destination: string;
  status: string;
  progress_pct: number;
  speed_mbps: number | null;
  filename: string | null;
  created_at: string;
  completed_at: string | null;
  error: string | null;
}

export interface DownloadCreated {
  download_id: string;
  status: string;
}

export interface HistoryRead {
  id: string;
  title: string;
  source_url: string;
  filename: string | null;
  media_type: string;
  source: string;
  downloaded_at: string;
}

export interface HistoryList {
  items: HistoryRead[];
  total: number;
  page: number;
  limit: number;
}

export interface SettingRead {
  key: string;
  value: string;
}

export interface StartDownloadPayload {
  source_url: string;
  title: string;
  media_type: string;
  destination: 'server' | 'client';
}

export interface ApiStatus {
  queue_size: number;
  active: number;
  disk_free_gb: number;
  alldebrid_ok: boolean;
}
