export const SCRAPER_SOURCES = ['wawacity'] as const;
export type ScraperSource = (typeof SCRAPER_SOURCES)[number];

export const DEBRID_PROVIDERS = ['alldebrid', 'realdebrid'] as const;
export type DebridProvider = (typeof DEBRID_PROVIDERS)[number];

export const HISTORY_SOURCES = [...SCRAPER_SOURCES, ...DEBRID_PROVIDERS] as const;
export type HistorySource = (typeof HISTORY_SOURCES)[number];
