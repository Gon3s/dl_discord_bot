export const MEDIA_TYPES = ['films', 'series', 'mangas'] as const;
export type MediaType = (typeof MEDIA_TYPES)[number];

export const CATEGORIES = MEDIA_TYPES;
export type Category = MediaType;

export const ALL_PROVIDERS = ['1fichier', 'Turbobit', 'Rapidgator'] as const;
export type Provider = (typeof ALL_PROVIDERS)[number];
