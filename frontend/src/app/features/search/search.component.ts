import { Component, signal, computed, linkedSignal, inject, ChangeDetectionStrategy, DestroyRef } from '@angular/core';
import { rxResource, takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { EMPTY, forkJoin } from 'rxjs';
import { ApiService } from '#core/services/api.service';
import { CATEGORIES } from '#core/constants/media';
import type { SearchResult } from '#core/models/search.type';
import type { StartDownloadPayload } from '#core/models/download.type';
import type { Episode, EpisodeLink } from '#core/models/episode.type';

type SearchParams = {
  q: string;
  category: string;
  year?: string;
  sort?: string;
};

const PREFERRED_PROVIDERS = ['Turbobit', 'Rapidgator', '1fichier'];

@Component({
  selector: 'app-search',
  imports: [FormsModule],
  templateUrl: './search.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SearchComponent {
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);

  protected query = signal('');
  protected category = signal('films');
  protected year = signal('');

  // Resets automatically when category changes
  protected sort = linkedSignal<string>(() => { this.category(); return ''; });

  // Only triggers resource when user explicitly submits
  protected searchParams = signal<SearchParams | undefined>(undefined);

  constructor() {
    // Restore state from URL query params on init
    const p = this.route.snapshot.queryParamMap;
    const q = p.get('q') ?? '';
    const cat = p.get('category') ?? 'films';
    const yr = p.get('year') ?? '';
    const srt = p.get('sort') ?? '';

    this.query.set(q);
    this.category.set(cat);
    this.year.set(yr);
    this.sort.set(srt);

    if (q) {
      this.searchParams.set({ q, category: cat, year: yr || undefined, sort: srt || undefined });
    }
  }

  protected readonly searchResource = rxResource({
    params: this.searchParams,
    stream: ({ params }) =>
      this.api.search(params.q, params.category, params.year, 20, params.sort),
  });

  protected results = computed(() => this.searchResource.value()?.results ?? []);
  protected loading = computed(() => this.searchResource.isLoading());
  protected errorMsg = computed(() => {
    if (!this.searchParams() || this.searchResource.isLoading()) return '';
    return this.searchResource.error() ? 'Search failed — is the backend running?' : '';
  });

  protected readonly categories = CATEGORIES;

  protected readonly sortOptions: Record<string, { label: string; value: string }[]> = {
    films: [
      { label: 'Tous', value: '' },
      { label: 'Exclusivités', value: 'exclus' },
      { label: 'Blu-Ray 1080p/720p', value: 'blu-ray_1080p-720p' },
      { label: 'ULTRA HD 4K', value: 'ultra-hd-4k' },
      { label: 'Dessins animés', value: 'dessins_animes' },
      { label: 'DVDRIP/BDRIP', value: 'dvdrip-dbrip' },
      { label: 'DVDRIP HQ (.mkv)', value: 'dvdrip-hq' },
      { label: 'DVDSCR/R5/TS/CAM', value: 'dvdsrc-r5-ts-cam' },
      { label: 'VOSTFR', value: 'film-vostfr' },
      { label: 'Films VO', value: '_film-vo' },
      { label: 'Vieux Films', value: 'vieux-films' },
    ],
    series: [
      { label: 'Tous', value: '' },
      { label: 'VOSTFR HQ', value: 'vostfr-hq' },
      { label: 'VF HQ', value: 'vf-hq' },
      { label: 'Full HD', value: 'full-hd' },
    ],
    mangas: [
      { label: 'Tous', value: '' },
      { label: 'VOSTFR HQ', value: 'vostfr-hq' },
    ],
  };

  protected readonly skeletons = Array.from({ length: 6 });

  // --- Film/manga modal ---
  protected modalOpen = signal(false);
  protected selectedResult = signal<SearchResult | null>(null);
  protected selectedDestination = signal<'server' | 'client'>('server');
  protected launching = signal(false);
  protected launchError = signal('');

  // --- Episodes panel ---
  protected episodePanelOpen = signal(false);
  protected launchingAll = signal(false);

  protected readonly episodesResource = rxResource({
    params: () => this.episodePanelOpen() ? this.selectedResult() : null,
    stream: ({ params }) => params ? this.api.getEpisodes(params.url) : EMPTY,
  });

  protected episodes = computed(() => this.episodesResource.value() ?? []);
  protected episodesLoading = computed(() => this.episodesResource.isLoading());

  search(): void {
    const q = this.query().trim();
    if (!q) return;
    const params: SearchParams = {
      q,
      category: this.category(),
      year: this.year() || undefined,
      sort: this.sort() || undefined,
    };
    this.searchParams.set(params);
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { q, category: params.category, year: params.year || null, sort: params.sort || null },
      replaceUrl: true,
    });
  }

  openResult(result: SearchResult): void {
    this.selectedResult.set(result);
    this.selectedDestination.set('server');
    this.launchError.set('');
    if (this.category() === 'series') {
      this.episodePanelOpen.set(true);
    } else {
      this.modalOpen.set(true);
    }
  }

  closeModal(): void {
    this.modalOpen.set(false);
  }

  closeEpisodePanel(): void {
    this.episodePanelOpen.set(false);
  }

  startDownload(): void {
    const r = this.selectedResult();
    if (!r) return;
    const payload: StartDownloadPayload = {
      source_url: r.url,
      title: r.title,
      media_type: this.category(),
      destination: this.selectedDestination(),
    };
    this.launching.set(true);
    this.api.startDownload(payload).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.launching.set(false);
        this.closeModal();
        this.router.navigate(['/downloads']);
      },
      error: () => {
        this.launchError.set('Failed to start download');
        this.launching.set(false);
      },
    });
  }

  downloadEpisode(ep: Episode): void {
    const url = this.pickBestLink(ep.links);
    if (!url) return;
    const r = this.selectedResult()!;
    const payload: StartDownloadPayload = {
      source_url: url,
      title: `${r.title} — ${ep.title}`,
      media_type: 'series',
      destination: this.selectedDestination(),
    };
    this.launching.set(true);
    this.api.startDownload(payload).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.launching.set(false);
        this.closeEpisodePanel();
        this.router.navigate(['/downloads']);
      },
      error: () => {
        this.launching.set(false);
      },
    });
  }

  downloadAll(): void {
    const r = this.selectedResult();
    const eps = this.episodes();
    if (!r || !eps.length) return;

    const requests = eps
      .map(ep => ({ ep, url: this.pickBestLink(ep.links) }))
      .filter(({ url }) => !!url)
      .map(({ ep, url }) =>
        this.api.startDownload({
          source_url: url!,
          title: `${r.title} — ${ep.title}`,
          media_type: 'series',
          destination: this.selectedDestination(),
        })
      );

    if (!requests.length) return;
    this.launchingAll.set(true);
    forkJoin(requests).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.launchingAll.set(false);
        this.closeEpisodePanel();
        this.router.navigate(['/downloads']);
      },
      error: () => {
        this.launchingAll.set(false);
      },
    });
  }

  qualityColor(quality: string | null): string {
    if (!quality) return '#8a9a55';
    if (quality === '4K' || quality === '2160p') return '#e8d62a';
    if (quality === '1080p') return 'var(--lime)';
    return '#8a9a55';
  }

  private pickBestLink(links: EpisodeLink[]): string | null {
    for (const provider of PREFERRED_PROVIDERS) {
      const link = links.find(l => l.provider === provider);
      if (link) return link.url;
    }
    return links[0]?.url ?? null;
  }
}
