import { Component, signal, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService, SearchResult, StartDownloadPayload } from '../../services/api.service';

@Component({
  selector: 'app-search',
  imports: [FormsModule],
  templateUrl: './search.component.html',
})
export class SearchComponent {
  private readonly api = inject(ApiService);

  protected query = signal('');
  protected category = signal('serie');
  protected year = signal('');
  protected results = signal<SearchResult[]>([]);
  protected loading = signal(false);
  protected error = signal('');

  protected modalOpen = signal(false);
  protected selectedResult = signal<SearchResult | null>(null);
  protected selectedDestination = signal<'server' | 'client'>('server');
  protected launching = signal(false);
  protected launchError = signal('');

  protected readonly categories = ['film', 'serie', 'manga'];

  protected readonly skeletons = Array.from({ length: 6 });

  search(): void {
    const q = this.query();
    if (!q.trim()) return;
    this.loading.set(true);
    this.error.set('');
    this.results.set([]);
    this.api.search(q, this.category(), this.year() || undefined).subscribe({
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
      next: () => { this.launching.set(false); this.closeModal(); },
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
