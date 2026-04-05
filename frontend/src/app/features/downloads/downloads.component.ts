import { Component, computed, linkedSignal, effect, inject, ChangeDetectionStrategy, DestroyRef, DOCUMENT } from '@angular/core';
import { rxResource, takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DecimalPipe } from '@angular/common';
import { ApiService } from '#core/services/api.service';
import { WsService } from '#core/services/ws.service';
import { ACTIVE_STATUSES, COMPLETED_STATUSES, STATUS_LABEL } from '#core/constants/download-status';
import type { Download } from '#core/models/download.type';

@Component({
  selector: 'app-downloads',
  imports: [DecimalPipe],
  templateUrl: './downloads.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DownloadsComponent {
  private readonly api = inject(ApiService);
  private readonly ws = inject(WsService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly document = inject(DOCUMENT);

  private readonly resource = rxResource({
    stream: () => this.api.getDownloads(),
  });

  // Mutable copy — auto-resets on resource reload, patchable by WS events
  protected downloads = linkedSignal<Download[]>(() => this.resource.value() ?? []);

  protected active = computed(() =>
    this.downloads().filter(d => (ACTIVE_STATUSES as readonly string[]).includes(d.status))
  );
  protected queued = computed(() => this.downloads().filter(d => d.status === 'queued'));
  protected done = computed(() => this.downloads().filter(d => d.status === 'completed'));
  protected failed = computed(() =>
    this.downloads().filter(d => ['error', 'cancelled'].includes(d.status))
  );
  protected completed = computed(() =>
    this.downloads().filter(d => (COMPLETED_STATUSES as readonly string[]).includes(d.status))
  );

  private readonly subscribedIds = new Set<string>();

  constructor() {
    this.ws.watchQueue().pipe(takeUntilDestroyed()).subscribe({
      next: (event) => {
        this.downloads.update(list =>
          list.map(d =>
            d.id === event.download_id
              ? {
                  ...d,
                  status: event.status ?? d.status,
                  progress_pct: event.progress_pct ?? d.progress_pct,
                  speed_mbps: event.speed_mbps ?? d.speed_mbps,
                  eta_s: event.eta_s ?? d.eta_s,
                  debrid_url: event.debrid_url ?? d.debrid_url,
                  error: event.error ?? d.error,
                }
              : d
          )
        );
        if (event.debrid_url) {
          this.triggerBrowserDownload(event.debrid_url, event.filename ?? undefined);
        }
        if (['completed', 'error', 'cancelled', 'queued'].includes(event.status)) {
          this.resource.reload();
        }
      },
      error: () => {},
    });

    // Subscribe to individual WS for each active download (granular progress)
    effect(() => {
      for (const d of this.active()) {
        this.subscribeToDownload(d.id);
      }
    });
  }

  private subscribeToDownload(id: string): void {
    if (this.subscribedIds.has(id)) return;
    this.subscribedIds.add(id);
    this.ws.watchDownload(id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (event) => {
        this.downloads.update(list =>
          list.map(d =>
            d.id === id
              ? {
                  ...d,
                  progress_pct: event.progress_pct ?? d.progress_pct,
                  speed_mbps: event.speed_mbps ?? d.speed_mbps,
                  eta_s: event.eta_s ?? d.eta_s,
                  status: event.status ?? d.status,
                }
              : d
          )
        );
      },
      error: () => this.subscribedIds.delete(id),
      complete: () => this.subscribedIds.delete(id),
    });
  }

  triggerBrowserDownload(url: string, filename?: string): void {
    const a = this.document.createElement('a');
    a.href = url;
    if (filename) a.download = filename;
    a.target = '_blank';
    a.rel = 'noopener';
    this.document.body.appendChild(a);
    a.click();
    this.document.body.removeChild(a);
  }

  formatEta(seconds: number): string {
    if (seconds <= 0) return '';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
  }

  cancel(id: string): void {
    this.api.cancelDownload(id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => this.resource.reload(),
    });
  }

  retry(id: string): void {
    this.api.retryDownload(id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => this.resource.reload(),
    });
  }

  remove(id: string): void {
    this.api.cancelDownload(id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => this.downloads.update(list => list.filter(d => d.id !== id)),
    });
  }

  statusLabel(status: string): string {
    return STATUS_LABEL[status] ?? status.toUpperCase();
  }
}
