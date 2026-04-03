import { Component, signal, computed, inject, ChangeDetectionStrategy, DestroyRef } from '@angular/core';
import { rxResource, takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { SlicePipe } from '@angular/common';
import { ApiService } from '#core/services/api.service';
import { ALL_PROVIDERS } from '#core/constants/media';

type HistoryParams = {
  q: string;
  status: string;
  provider: string;
  from: string;
  to: string;
  page: number;
  pageSize: number;
};

@Component({
  selector: 'app-history',
  imports: [FormsModule, SlicePipe],
  templateUrl: './history.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HistoryComponent {
  protected readonly Math = Math;
  private readonly api = inject(ApiService);
  private readonly destroyRef = inject(DestroyRef);

  // Form fields — local editable state, only committed on applyFilters()
  protected filterQuery = signal('');
  protected filterStatus = signal('');
  protected filterProvider = signal('');
  protected filterFrom = signal('');
  protected filterTo = signal('');
  protected pageSize = signal(10);

  // Committed params that drive the resource
  protected params = signal<HistoryParams>({
    q: '', status: '', provider: '', from: '', to: '', page: 1, pageSize: 10,
  });

  protected readonly resource = rxResource({
    params: this.params,
    stream: ({ params }) =>
      this.api.getHistory({
        q: params.q || undefined,
        status: params.status || undefined,
        provider: params.provider || undefined,
        from: params.from || undefined,
        to: params.to || undefined,
        page: params.page,
        page_size: params.pageSize,
      }),
  });

  protected items = computed(() => this.resource.value()?.items ?? []);
  protected total = computed(() => this.resource.value()?.total ?? 0);
  protected loading = computed(() => this.resource.isLoading());
  protected totalPages = computed(() => Math.ceil(this.total() / this.params().pageSize) || 1);

  protected activeFilters = computed(() => {
    const p = this.params();
    const f: { label: string; key: string }[] = [];
    if (p.q) f.push({ label: `"${p.q}"`, key: 'query' });
    if (p.status) f.push({ label: p.status.toUpperCase(), key: 'status' });
    if (p.provider) f.push({ label: p.provider, key: 'provider' });
    return f;
  });

  protected readonly pageSizes = [10, 25, 50];
  protected readonly providers = ['', ...ALL_PROVIDERS];

  applyFilters(): void {
    this.params.set({
      q: this.filterQuery(),
      status: this.filterStatus(),
      provider: this.filterProvider(),
      from: this.filterFrom(),
      to: this.filterTo(),
      page: 1,
      pageSize: this.pageSize(),
    });
  }

  clearFilter(key: string): void {
    if (key === 'query') this.filterQuery.set('');
    if (key === 'status') this.filterStatus.set('');
    if (key === 'provider') this.filterProvider.set('');
    this.applyFilters();
  }

  goPage(p: number): void {
    if (p < 1 || p > this.totalPages()) return;
    this.params.update(prev => ({ ...prev, page: p }));
  }

  delete(id: string): void {
    this.api.deleteHistory(id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => this.resource.reload(),
    });
  }

  pageNumbers(): number[] {
    const tp = this.totalPages();
    const cur = this.params().page;
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
