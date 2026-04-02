import { Component, OnInit, OnDestroy, signal, inject, computed } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { Subscription } from 'rxjs';
import { ApiService, Download } from '../../services/api.service';
import { WsService, QueueEvent } from '../../services/ws.service';

@Component({
  selector: 'app-downloads',
  imports: [DecimalPipe],
  templateUrl: './downloads.component.html',
})
export class DownloadsComponent implements OnInit, OnDestroy {
  private readonly api = inject(ApiService);
  private readonly ws = inject(WsService);

  protected downloads = signal<Download[]>([]);
  private subs = new Subscription();

  protected active = computed(() =>
    this.downloads().filter(d => ['downloading', 'scraping', 'debriding'].includes(d.status))
  );
  protected queued = computed(() =>
    this.downloads().filter(d => d.status === 'queued')
  );
  protected completed = computed(() =>
    this.downloads().filter(d => ['completed', 'error', 'cancelled'].includes(d.status))
  );

  ngOnInit(): void {
    this.loadDownloads();
    this.subs.add(
      this.ws.watchQueue().subscribe({
        next: (event: QueueEvent) => {
          // Update progress in-place or reload list on status change
          this.downloads.update(list =>
            list.map(d => d.id === event.download_id ? {
              ...d,
              status: event.status ?? d.status,
              progress_pct: event.progress_pct ?? d.progress_pct,
              speed_mbps: event.speed_mbps ?? d.speed_mbps,
            } : d)
          );
          if (['completed', 'error', 'cancelled', 'queued'].includes(event.status)) {
            this.loadDownloads();
          }
        },
        error: () => {},
      })
    );
  }

  private loadDownloads(): void {
    this.api.getDownloads().subscribe({
      next: (list) => this.downloads.set(list),
      error: () => {},
    });
  }

  cancel(id: string): void {
    this.api.cancelDownload(id).subscribe({ next: () => this.loadDownloads() });
  }

  formatEta(speedMbps: number | null, progressPct: number): string {
    if (!speedMbps || progressPct >= 100) return '';
    return '';  // ETA calculable si on connaît file_size
  }

  statusLabel(status: string): string {
    const map: Record<string, string> = {
      queued: 'WAITING',
      scraping: 'SCRAPING…',
      debriding: 'DEBRIDING…',
      downloading: 'DOWNLOADING',
      completed: '✓ DONE',
      error: '✕ ERROR',
      cancelled: 'CANCELLED',
      ready_for_client: 'READY',
    };
    return map[status] ?? status.toUpperCase();
  }

  ngOnDestroy(): void {
    this.subs.unsubscribe();
  }
}
