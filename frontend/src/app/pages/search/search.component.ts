import { Component, signal, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService, SearchResult, StartDownloadPayload } from '../../services/api.service';

@Component({
  selector: 'app-search',
  imports: [FormsModule],
  templateUrl: './search.component.html',
})
export class SearchComponent {
  private readonly api = inject(ApiService);
  private readonly router = inject(Router);

  protected query = signal('');
  protected category = signal('films');
  protected year = signal('');
  protected sort = signal('');
  protected results = signal<SearchResult[]>([]);
  protected loading = signal(false);
  protected error = signal('');

  protected modalOpen = signal(false);
  protected selectedResult = signal<SearchResult | null>(null);
  protected selectedDestination = signal<'server' | 'client'>('server');
  protected launching = signal(false);
  protected launchError = signal('');

  protected readonly categories = ['films', 'series', 'mangas'];

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

  search(): void {
    const q = this.query();
    if (!q.trim()) return;
    this.loading.set(true);
    this.error.set('');
    this.results.set([]);
    this.api.search(q, this.category(), this.year() || undefined, 20, this.sort() || undefined).subscribe({
      next: (res) => { this.results.set(res.results); this.loading.set(false); },
      error: () => { this.error.set('Search failed — is the backend running?'); this.loading.set(false); },
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
      next: () => { this.launching.set(false); this.closeModal(); this.router.navigate(['/downloads']); },
      error: () => { this.launchError.set('Failed to start download'); this.launching.set(false); },
    });
  }

  qualityColor(quality: string | null): string {
    if (!quality) return '#8a9a55';
    if (quality === '4K' || quality === '2160p') return '#e8d62a';
    if (quality === '1080p') return 'var(--lime)';
    return '#8a9a55';
  }
}
