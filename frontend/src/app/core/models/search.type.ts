import type { ScraperSource } from './source.type';
import type { MediaType } from '../constants/media';

export type SearchResult = {
  title: string;
  url: string;
  year: number | null;
  category: MediaType | null;
  quality: string | null;
  language: string | null;
  source: ScraperSource;
  poster_url: string | null;
};

export type SearchResponse = {
  results: SearchResult[];
  total: number;
  source: ScraperSource;
  page: number;
};
