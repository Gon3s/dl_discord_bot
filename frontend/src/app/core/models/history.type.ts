import type { MediaType } from '../constants/media';
import type { HistoryStatus } from '../constants/download-status';
import type { HistorySource } from './source.type';

export type HistoryRead = {
  id: string;
  title: string;
  source_url: string;
  filename: string | null;
  media_type: MediaType | 'unknown';
  source: HistorySource;
  destination: string | null;
  status: HistoryStatus;
  error: string | null;
  downloaded_at: string;
};

export type HistoryList = {
  items: HistoryRead[];
  total: number;
  page: number;
  limit: number;
};
