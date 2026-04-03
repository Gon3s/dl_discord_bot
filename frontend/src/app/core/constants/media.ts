export const CATEGORIES = ['films', 'series', 'mangas'] as const;
export type Category = (typeof CATEGORIES)[number];

export const ALL_PROVIDERS = ['1fichier', 'Turbobit', 'Rapidgator'] as const;
export type Provider = (typeof ALL_PROVIDERS)[number];
