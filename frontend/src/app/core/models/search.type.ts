export type SearchResult = {
  title: string;
  url: string;
  year: number | null;
  category: string | null;
  quality: string | null;
  language: string | null;
  source: string;
  poster_url: string | null;
};

export type SearchResponse = {
  results: SearchResult[];
  total: number;
  source: string;
};
