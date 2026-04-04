export type EpisodeLink = {
  provider: string;
  url: string;
};

export type Episode = {
  title: string;
  number: number;
  links: EpisodeLink[];
};
