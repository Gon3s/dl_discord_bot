import { Component, signal, computed, inject, ChangeDetectionStrategy } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { rxResource, takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { interval } from 'rxjs';
import { ApiService } from '../../../core/services/api.service';
import { WsService } from '../../../core/services/ws.service';

@Component({
  selector: 'app-sidebar',
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './sidebar.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SidebarComponent {
  private readonly api = inject(ApiService);
  private readonly ws = inject(WsService);

  protected readonly statusResource = rxResource({
    stream: () => this.api.getStatus(),
  });

  protected apiOnline = computed(() => !!this.statusResource.value() && !this.statusResource.error());
  protected activeCount = computed(() => {
    const s = this.statusResource.value();
    return s ? s.active + s.queue_size : 0;
  });
  protected wsLive = signal(false);

  constructor() {
    interval(10_000).pipe(takeUntilDestroyed()).subscribe(() => this.statusResource.reload());

    this.ws.watchQueue().pipe(takeUntilDestroyed()).subscribe({
      next: () => this.wsLive.set(true),
      error: () => this.wsLive.set(false),
    });
  }
}
