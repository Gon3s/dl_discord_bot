import { Component, signal, computed, linkedSignal, inject, ChangeDetectionStrategy } from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import type { SearchResult, StartDownloadPayload } from '../../core/models/api.models';

interface SearchParams {
  q: string;
  category: string;
  year?: string;
  sort?: string;
}

@Component({
  selector: 'app-search',
  imports: [FormsModule],
  templateUrl: './search.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SearchComponent {
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);

  protected query = signal('');
  protected category = signal('films');
  protected year = signal('');

  // Resets automatically when category changes
  protected sort = linkedSignal<string>(() => { this.category(); return ''; });

  // Only triggers resource when user explicitly submits
  protected searchParams = signal<SearchParams | undefined>(undefined);

  protected readonly searchResource = rxResource({
    params: () => this.searchParams(),
    stream: ({ params }) =>
      this.api.search(params.q, params.category, params.year, 20, params.sort),
  });

  protected results = computed(() => this.searchResource.value()?.results ?? []);
  protected loading = computed(() => this.searchResource.isLoading());
  protected errorMsg = computed(() => {
    if (!this.searchParams() || this.searchResource.isLoading()) return '';
    return this.searchResource.error() ? 'Search failed — is the backend running?' : '';
  });

  protected readonly categories = ['films', 'series', 'mangas'] as const;

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

  // Modal state
  protected modalOpen = signal(false);
  protected selectedResult = signal<SearchResult | null>(null);
  protected selectedDestination = signal<'server' | 'client'>('server');
  protected launching = signal(false);
  protected launchError = signal('');

  search(): void {
    const q = this.query().trim();
    if (!q) return;
    this.searchParams.set({
      q,
      category: this.category(),
      year: this.year() || undefined,
      sort: this.sort() || undefined,
    });
  }

  openModal(result: SearchResult): void {
    this.selectedResult.set(result);
    this.selectedDestination.set('server');
    this.launchError.set('');
    this.modalOpen.set(true);
  }

  closeModal(): void {
    this.modalOpen.set(false);
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
    this.api.startDownload(payload).subscribe({
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

  qualityColor(quality: string | null): string {
    if (!quality) return '#8a9a55';
    if (quality === '4K' || quality === '2160p') return '#e8d62a';
    if (quality === '1080p') return 'var(--lime)';
    return '#8a9a55';
  }
}
