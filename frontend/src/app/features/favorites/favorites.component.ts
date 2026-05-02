import { Component, ChangeDetectionStrategy, inject, signal, computed, linkedSignal, DestroyRef } from '@angular/core';
import { rxResource, takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { NgClass } from '@angular/common';
import { EMPTY, forkJoin } from 'rxjs';
import { FavoriteService } from '#core/services/favorite.service';
import { SearchStateService } from '#core/services/search-state.service';
import { ApiService } from '#core/services/api.service';
import { CATEGORIES } from '#core/constants/media';
import type { Favorite } from '#core/models/favorite.type';
import type { SearchResult } from '#core/models/search.type';
import type { Episode, EpisodeLink } from '#core/models/episode.type';
import type { StartDownloadPayload } from '#core/models/download.type';

const PREFERRED_PROVIDERS = ['Turbobit', 'Rapidgator', '1fichier'];

type SortOption = 'added_at' | 'title';

@Component({
  selector: 'app-favorites',
  imports: [FormsModule, NgClass],
  templateUrl: './favorites.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FavoritesComponent {
  private readonly router = inject(Router);
  private readonly api = inject(ApiService);
  private readonly destroyRef = inject(DestroyRef);
  protected readonly favoriteService = inject(FavoriteService);
  protected readonly state = inject(SearchStateService);

  protected readonly categories = ['tous', ...CATEGORIES];
  protected readonly filterCategory = signal<string>('tous');
  protected readonly sortBy = linkedSignal<SortOption>(() => { this.filterCategory(); return 'added_at'; });

  protected readonly filtered = computed(() => {
    const cat = this.filterCategory();
    const sort = this.sortBy();
    let items = [...this.favoriteService.favorites()];
    if (cat !== 'tous') items = items.filter(f => f.category === cat);
    if (sort === 'title') items.sort((a, b) => a.title.localeCompare(b.title));
    return items;
  });

  // --- Episode panel ---
  protected readonly selectedFav = signal<Favorite | null>(null);
  protected readonly episodePanelOpen = signal(false);
  protected readonly launching = signal(false);
  protected readonly launchingAll = signal(false);
  protected get selectedDestination() { return this.state.destination; }

  protected readonly episodesResource = rxResource({
    params: () => this.episodePanelOpen() ? this.selectedFav() : null,
    stream: ({ params }) => params ? this.api.getEpisodes(params.url) : EMPTY,
  });

  protected episodes = computed(() => this.episodesResource.value() ?? []);
  protected episodesLoading = computed(() => this.episodesResource.isLoading());

  protected lastDownloadedEp = computed(() => {
    const nums = this.episodes()
      .filter(ep => this.state.isEpisodeDownloaded(this.epFullTitle(ep)))
      .map(ep => ep.number);
    return nums.length ? Math.max(...nums) : -1;
  });

  qualityColor(quality: string | null): string {
    if (!quality) return '#8a9a55';
    if (quality === '4K' || quality === '2160p') return '#e8d62a';
    if (quality === '1080p') return 'var(--lime)';
    return '#8a9a55';
  }

  epFullTitle(ep: Episode): string {
    return `${this.selectedFav()!.title} — ${ep.title}`;
  }

  openFavorite(fav: Favorite): void {
    if (fav.category === 'series') {
      this.selectedFav.set(fav);
      this.episodePanelOpen.set(true);
    } else {
      const result: SearchResult = {
        title: fav.title, url: fav.url, category: fav.category,
        year: fav.year, quality: fav.quality, language: fav.language,
        source: fav.source, poster_url: fav.poster_url,
      };
      this.state.category.set(fav.category ?? 'films');
      this.state.pendingResult.set(result);
      this.router.navigate(['/search']);
    }
  }

  closeEpisodePanel(): void {
    this.episodePanelOpen.set(false);
  }

  downloadEpisode(ep: Episode): void {
    const url = this.pickBestLink(ep.links);
    if (!url) return;
    const payload: StartDownloadPayload = {
      source_url: url,
      title: this.epFullTitle(ep),
      media_type: 'series',
      destination: this.selectedDestination(),
      alternative_urls: ep.links.map(l => l.url).filter(u => u !== url),
    };
    this.launching.set(true);
    this.api.startDownload(payload).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.launching.set(false);
        this.state.refreshDownloads();
      },
      error: () => { this.launching.set(false); },
    });
  }

  downloadAll(): void {
    const fav = this.selectedFav();
    const eps = this.episodes();
    if (!fav || !eps.length) return;
    const requests = eps
      .map(ep => ({ ep, url: this.pickBestLink(ep.links) }))
      .filter(({ url }) => !!url)
      .map(({ ep, url }) => this.api.startDownload({
        source_url: url!,
        title: this.epFullTitle(ep),
        media_type: 'series',
        destination: this.selectedDestination(),
        alternative_urls: ep.links.map(l => l.url).filter(u => u !== url),
      }));
    if (!requests.length) return;
    this.launchingAll.set(true);
    forkJoin(requests).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.launchingAll.set(false);
        this.closeEpisodePanel();
        this.router.navigate(['/downloads']);
      },
      error: () => { this.launchingAll.set(false); },
    });
  }

  private pickBestLink(links: EpisodeLink[]): string | null {
    for (const provider of PREFERRED_PROVIDERS) {
      const link = links.find(l => l.provider === provider);
      if (link) return link.url;
    }
    return links[0]?.url ?? null;
  }
}
