import { Injectable, computed, effect, inject, linkedSignal, signal } from '@angular/core';
import { toSignal, rxResource } from '@angular/core/rxjs-interop';
import { BehaviorSubject, switchMap, map } from 'rxjs';
import { ApiService } from './api.service';
import type { SearchResult } from '../models/search.type';

const ACTIVE_STATUSES = new Set(['queued', 'scraping', 'resolving', 'debriding', 'downloading']);
const DEFAULT_SOURCE = 'wawacity';
const ENABLED_SOURCES = new Set([DEFAULT_SOURCE]);

function initialSource(): string {
  const stored = localStorage.getItem('dl_source');
  return stored && ENABLED_SOURCES.has(stored) ? stored : DEFAULT_SOURCE;
}

export type SearchParams = {
  q: string;
  category: string;
  year?: string;
  sort?: string;
  source: string;
};

@Injectable({ providedIn: 'root' })
export class SearchStateService {
  private readonly api = inject(ApiService);

  readonly query = signal('');
  readonly category = signal('films');
  readonly year = signal('');
  readonly source = signal<string>(initialSource());
  readonly sort = linkedSignal<string>(() => { this.category(); this.source(); return ''; });
  readonly searchParams = signal<SearchParams | undefined>(undefined);

  private readonly settingsResource = rxResource({
    stream: () => this.api.getSettings(),
  });

  constructor() {
    // Applique default_category depuis les settings une seule fois,
    // uniquement si l'utilisateur n'a pas encore lancé de recherche.
    effect(() => {
      const settings = this.settingsResource.value();
      if (!settings || this.searchParams()) return;
      const defaultCat = settings.find(s => s.key === 'default_category')?.value;
      if (defaultCat) this.category.set(defaultCat);
    });
  }
  readonly destination = signal<'server' | 'client'>(
    (localStorage.getItem('dl_destination') as 'server' | 'client') ?? 'server'
  );

  // Historique chargé une fois au démarrage — singleton, pas de rechargement à chaque navigation
  private readonly historyResource = rxResource({
    stream: () => this.api.getHistory({ page_size: 1000 }),
  });

  // Téléchargements actifs — BehaviorSubject + toSignal pour une réactivité garantie
  private readonly refreshTrigger$ = new BehaviorSubject<void>(undefined);

  readonly activeTitles = toSignal(
    this.refreshTrigger$.pipe(
      switchMap(() => this.api.getDownloads()),
      map(downloads => new Set(
        downloads
          .filter(d => ACTIVE_STATUSES.has(d.status))
          .map(d => d.title.toLowerCase())
      ))
    ),
    { initialValue: new Set<string>() }
  );

  refreshDownloads(): void {
    this.refreshTrigger$.next();
  }

  // Set des source_url téléchargées — lookup O(1)
  readonly downloadedUrls = computed(() =>
    new Set((this.historyResource.value()?.items ?? []).map(h => h.source_url))
  );

  // Set des titres en minuscules — pour matcher les séries par préfixe
  // (les épisodes sont stockés "Titre — Épisode 01")
  private readonly downloadedTitles = computed(() =>
    (this.historyResource.value()?.items ?? []).map(h => h.title.toLowerCase())
  );

  /** Film/manga : match par URL. Série : match si au moins un épisode a été téléchargé. */
  isDownloaded(url: string, title: string): boolean {
    if (this.downloadedUrls().has(url)) return true;
    const prefix = title.toLowerCase() + ' —';
    return this.downloadedTitles().some(t => t.startsWith(prefix));
  }

  /** Épisode individuel : match exact sur le titre complet "Série — Épisode XX". */
  isEpisodeDownloaded(fullTitle: string): boolean {
    return this.downloadedTitles().includes(fullTitle.toLowerCase());
  }

  /** Résultat à ouvrir automatiquement lors de la prochaine visite de SearchComponent (depuis Favoris). */
  readonly pendingResult = signal<SearchResult | null>(null);

  setDestination(value: 'server' | 'client'): void {
    this.destination.set(value);
    localStorage.setItem('dl_destination', value);
  }

  setSource(value: string): void {
    const source = ENABLED_SOURCES.has(value) ? value : DEFAULT_SOURCE;
    this.source.set(source);
    localStorage.setItem('dl_source', source);
  }
}
