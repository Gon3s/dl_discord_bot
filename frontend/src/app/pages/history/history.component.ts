import { Component, OnInit, signal, inject, computed } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SlicePipe } from '@angular/common';
import { ApiService, HistoryRead } from '../../services/api.service';

@Component({
  selector: 'app-history',
  imports: [FormsModule, SlicePipe],
  templateUrl: './history.component.html',
})
export class HistoryComponent implements OnInit {
  protected readonly Math = Math;
  private readonly api = inject(ApiService);

  protected items = signal<HistoryRead[]>([]);
  protected total = signal(0);
  protected loading = signal(false);

  protected filterQuery = signal('');
  protected filterStatus = signal('');
  protected filterProvider = signal('');
  protected filterFrom = signal('');
  protected filterTo = signal('');

  protected page = signal(1);
  protected pageSize = signal(10);

  protected readonly pageSizes = [10, 25, 50];
  protected readonly providers = ['', '1fichier', 'Turbobit', 'Rapidgator'];

  protected totalPages = computed(() => Math.ceil(this.total() / this.pageSize()) || 1);

  protected activeFilters = computed(() => {
    const f: { label: string; key: string }[] = [];
    if (this.filterQuery()) f.push({ label: `"${this.filterQuery()}"`, key: 'query' });
    if (this.filterStatus()) f.push({ label: this.filterStatus().toUpperCase(), key: 'status' });
    if (this.filterProvider()) f.push({ label: this.filterProvider(), key: 'provider' });
    return f;
  });

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading.set(true);
    this.api.getHistory({
      q: this.filterQuery() || undefined,
      status: this.filterStatus() || undefined,
      provider: this.filterProvider() || undefined,
      from: this.filterFrom() || undefined,
      to: this.filterTo() || undefined,
      page: this.page(),
      page_size: this.pageSize(),
    }).subscribe({
      next: (res) => {
        this.items.set(res.items);
        this.total.set(res.total);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  applyFilters(): void {
    this.page.set(1);
    this.load();
  }

  clearFilter(key: string): void {
    if (key === 'query') this.filterQuery.set('');
    if (key === 'status') this.filterStatus.set('');
    if (key === 'provider') this.filterProvider.set('');
    this.applyFilters();
  }

  goPage(p: number): void {
    if (p < 1 || p > this.totalPages()) return;
    this.page.set(p);
    this.load();
  }

  delete(id: string): void {
    this.api.deleteHistory(id).subscribe({ next: () => this.load() });
  }

  pageNumbers(): number[] {
    const tp = this.totalPages();
    const cur = this.page();
    const pages: number[] = [];
    if (tp <= 5) {
      for (let i = 1; i <= tp; i++) pages.push(i);
    } else {
      pages.push(1);
      if (cur > 3) pages.push(-1);
      for (let i = Math.max(2, cur - 1); i <= Math.min(tp - 1, cur + 1); i++) pages.push(i);
      if (cur < tp - 2) pages.push(-1);
      pages.push(tp);
    }
    return pages;
  }
}
