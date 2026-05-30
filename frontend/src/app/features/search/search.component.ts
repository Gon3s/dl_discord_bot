import {
  Component,
  signal,
  computed,
  inject,
  ChangeDetectionStrategy,
  DestroyRef,
  effect,
} from '@angular/core';
import { rxResource, takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { NgClass } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, ActivatedRoute } from '@angular/router';
import { EMPTY, forkJoin } from 'rxjs';
import { ApiService } from '#core/services/api.service';
import { SearchStateService } from '#core/services/search-state.service';
import { FavoriteService } from '#core/services/favorite.service';
import { NotificationWatchService } from '#core/services/notification-watch.service';
import { CATEGORIES } from '#core/constants/media';
import type { SearchResult } from '#core/models/search.type';
import type { StartDownloadPayload } from '#core/models/download.type';
import type { Episode, EpisodeLink } from '#core/models/episode.type';

const PREFERRED_PROVIDERS = ['Turbobit', 'Rapidgator', '1fichier'];

@Component({
  selector: 'app-search',
  imports: [FormsModule, NgClass],
  templateUrl: './search.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SearchComponent {
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly destroyRef = inject(DestroyRef);
  protected readonly state = inject(SearchStateService);
  protected readonly favorites = inject(FavoriteService);
  protected readonly watchService = inject(NotificationWatchService);

  protected get query() {
    return this.state.query;
  }
  protected get category() {
    return this.state.category;
  }
  protected get year() {
    return this.state.year;
  }
  protected get sort() {
    return this.state.sort;
  }
  protected get source() {
    return this.state.source;
  }
  protected get searchParams() {
    return this.state.searchParams;
  }

  protected readonly currentPage = signal(1);
  protected readonly accumulatedResults = signal<SearchResult[]>([]);

  protected readonly searchResource = rxResource({
    params: () => {
      const sp = this.searchParams();
      if (!sp) return undefined;
      return { ...sp, page: this.currentPage() };
    },
    stream: ({ params }) =>
      this.api.search(
        params.q,
        params.category,
        params.year,
        20,
        params.sort,
        params.page,
        params.source,
      ),
  });

  protected results = computed(() => this.accumulatedResults());
  protected loading = computed(() => this.searchResource.isLoading() && this.currentPage() === 1);
  protected loadingMore = computed(() => this.searchResource.isLoading() && this.currentPage() > 1);
  protected hasMore = computed(() => {
    const val = this.searchResource.value();
    return !!val && val.results.length > 0;
  });
  protected errorMsg = computed(() => {
    if (!this.searchParams() || this.searchResource.isLoading()) return '';
    return this.searchResource.error() ? 'Search failed — is the backend running?' : '';
  });

  protected readonly categories = CATEGORIES;
  protected readonly sources = [{ value: 'wawacity', label: 'WAWACITY' }];

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

  constructor() {
    effect(() => {
      const results = this.searchResource.value()?.results;
      if (!results) return;
      if (this.currentPage() === 1) {
        this.accumulatedResults.set(results);
      } else {
        this.accumulatedResults.update((prev) => [...prev, ...results]);
      }
    });

    const pending = this.state.pendingResult();
    if (pending) {
      this.state.pendingResult.set(null);
      this.openResult(pending);
    }

    const params = this.route.snapshot.queryParamMap;
    const q = params.get('q');
    if (q) {
      this.state.query.set(q);
      const cat = params.get('category');
      const src = params.get('source');
      if (cat) this.state.category.set(cat);
      if (src) this.state.setSource(src);
    }
    this.search();
  }

  // --- Film/manga modal ---
  protected modalOpen = signal(false);
  protected selectedResult = signal<SearchResult | null>(null);
  protected get selectedDestination() {
    return this.state.destination;
  }
  protected launching = signal(false);
  protected launchError = signal('');

  // --- Episodes panel ---
  protected episodePanelOpen = signal(false);
  protected launchingAll = signal(false);

  protected readonly episodesResource = rxResource({
    params: () => (this.episodePanelOpen() ? this.selectedResult() : null),
    stream: ({ params }) => (params ? this.api.getEpisodes(params.url, params.source) : EMPTY),
  });

  protected episodes = computed(() => this.episodesResource.value() ?? []);
  protected episodesLoading = computed(() => this.episodesResource.isLoading());
  protected lastDownloadedEp = computed(() => {
    const nums = this.episodes()
      .filter((ep) => this.state.isEpisodeDownloaded(this.epFullTitle(ep)))
      .map((ep) => ep.number);
    return nums.length ? Math.max(...nums) : -1;
  });

  search(): void {
    const q = this.query().trim();
    this.currentPage.set(1);
    this.searchParams.set({
      q,
      category: this.category(),
      year: this.year() || undefined,
      sort: this.sort() || undefined,
      source: this.source(),
    });
  }

  loadMore(): void {
    this.currentPage.update((p) => p + 1);
  }

  openResult(result: SearchResult): void {
    this.selectedResult.set(result);
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
    this.api
      .startDownload(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
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

  epFullTitle(ep: Episode): string {
    return `${this.selectedResult()!.title} — ${ep.title}`;
  }

  downloadEpisode(ep: Episode): void {
    const url = this.pickBestLink(ep.links);
    if (!url) return;
    const payload: StartDownloadPayload = {
      source_url: url,
      title: this.epFullTitle(ep),
      media_type: 'series',
      destination: this.selectedDestination(),
      alternative_urls: ep.links.map((l) => l.url).filter((u) => u !== url),
    };
    this.launching.set(true);
    this.api
      .startDownload(payload)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => {
          this.launching.set(false);
          this.state.refreshDownloads();
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
      .map((ep) => ({ ep, url: this.pickBestLink(ep.links) }))
      .filter(({ url }) => !!url)
      .map(({ ep, url }) =>
        this.api.startDownload({
          source_url: url!,
          title: `${r.title} — ${ep.title}`,
          media_type: 'series',
          destination: this.selectedDestination(),
          alternative_urls: ep.links.map((l) => l.url).filter((u) => u !== url),
        }),
      );

    if (!requests.length) return;
    this.launchingAll.set(true);
    forkJoin(requests)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
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
      const link = links.find((l) => l.provider === provider);
      if (link) return link.url;
    }
    return links[0]?.url ?? null;
  }
}
