import { Component, OnInit, OnDestroy, signal, inject } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { Subscription, interval } from 'rxjs';
import { switchMap } from 'rxjs/operators';
import { ApiService } from '../../../services/api.service';
import { WsService } from '../../../services/ws.service';

@Component({
  selector: 'app-sidebar',
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './sidebar.component.html',
})
export class SidebarComponent implements OnInit, OnDestroy {
  private readonly api = inject(ApiService);
  private readonly ws = inject(WsService);

  protected apiOnline = signal(false);
  protected wsLive = signal(false);
  protected activeCount = signal(0);

  private subs = new Subscription();

  ngOnInit(): void {
    // Poll API status every 10s
    this.subs.add(
      interval(10_000).pipe(
        switchMap(() => this.api.getStatus()),
      ).subscribe({
        next: (s) => {
          this.apiOnline.set(true);
          this.activeCount.set(s.active + s.queue_size);
        },
        error: () => this.apiOnline.set(false),
      })
    );

    // Initial status check
    this.api.getStatus().subscribe({
      next: (s) => {
        this.apiOnline.set(true);
        this.activeCount.set(s.active + s.queue_size);
      },
      error: () => this.apiOnline.set(false),
    });

    // Watch WS queue for live indicator
    this.subs.add(
      this.ws.watchQueue().subscribe({
        next: () => this.wsLive.set(true),
        error: () => this.wsLive.set(false),
      })
    );
  }

  ngOnDestroy(): void {
    this.subs.unsubscribe();
    this.ws.closeQueue();
  }
}
