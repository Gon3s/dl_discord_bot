import { Component, computed, linkedSignal, inject, ChangeDetectionStrategy } from '@angular/core';
import { rxResource, takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DecimalPipe } from '@angular/common';
import { ApiService } from '../../core/services/api.service';
import { WsService } from '../../core/services/ws.service';
import type { Download } from '../../core/models/api.models';

@Component({
  selector: 'app-downloads',
  imports: [DecimalPipe],
  templateUrl: './downloads.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DownloadsComponent {
  private readonly api = inject(ApiService);
  private readonly ws = inject(WsService);

  private readonly resource = rxResource({
    stream: () => this.api.getDownloads(),
  });

  // Mutable copy — auto-resets on resource reload, patchable by WS events
  protected downloads = linkedSignal<Download[]>(() => this.resource.value() ?? []);

  protected active = computed(() =>
    this.downloads().filter(d =>
      ['scraping', 'resolving', 'debriding', 'downloading'].includes(d.status)
    )
  );
  protected queued = computed(() => this.downloads().filter(d => d.status === 'queued'));
  protected done = computed(() => this.downloads().filter(d => d.status === 'completed'));
  protected failed = computed(() =>
    this.downloads().filter(d => ['error', 'cancelled'].includes(d.status))
  );
  protected completed = computed(() =>
    this.downloads().filter(d => ['completed', 'error', 'cancelled'].includes(d.status))
  );

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
                }
              : d
          )
        );
        if (['completed', 'error', 'cancelled', 'queued'].includes(event.status)) {
          this.resource.reload();
        }
      },
      error: () => {},
    });
  }

  cancel(id: string): void {
    this.api.cancelDownload(id).subscribe({ next: () => this.resource.reload() });
  }

  remove(id: string): void {
    this.api.cancelDownload(id).subscribe({
      next: () => this.downloads.update(list => list.filter(d => d.id !== id)),
    });
  }

  statusLabel(status: string): string {
    const map: Record<string, string> = {
      queued: 'WAITING',
      scraping: 'SCRAPING…',
      resolving: 'RESOLVING…',
      debriding: 'DEBRIDING…',
      downloading: 'DOWNLOADING',
      completed: '✓ DONE',
      error: '✕ ERROR',
      cancelled: 'CANCELLED',
      ready_for_client: 'READY',
    };
    return map[status] ?? status.toUpperCase();
  }
}
