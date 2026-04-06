export type Favorite = {
  id: string;
  title: string;
  url: string;
  category: string | null;
  year: number | null;
  quality: string | null;
  language: string | null;
  source: string;
  poster_url: string | null;
  added_at: string;
};

export type FavoriteCreate = Omit<Favorite, 'id' | 'added_at'>;
