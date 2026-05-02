export type HistoryRead = {
  id: string;
  title: string;
  source_url: string;
  filename: string | null;
  media_type: string;
  source: string;
  destination: string | null;
  status: string;
  error: string | null;
  downloaded_at: string;
};

export type HistoryList = {
  items: HistoryRead[];
  total: number;
  page: number;
  limit: number;
};
