import type { ScraperSource } from './source.type';
import type { MediaType } from '../constants/media';

export type Favorite = {
  id: string;
  title: string;
  url: string;
  category: MediaType | null;
  year: number | null;
  quality: string | null;
  language: string | null;
  source: ScraperSource;
  poster_url: string | null;
  added_at: string;
};

export type FavoriteCreate = Omit<Favorite, 'id' | 'added_at'>;
