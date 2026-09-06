import { Injectable, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ApiService } from './api.service';
import type { Notification } from '../models/notification.type';
import type { ScraperSource } from '../models/source.type';

interface WatchableResult {
  title: string;
  url: string;
  source: ScraperSource;
  poster_url?: string | null;
}

@Injectable({ providedIn: 'root' })
export class NotificationWatchService {
  private readonly api = inject(ApiService);
  private readonly _notifications = signal<Notification[]>([]);

  readonly notifications = this._notifications.asReadonly();
  readonly watchedUrls = computed(() => new Set(this._notifications().map(n => n.url)));

  constructor() {
    this.api.getNotifications().pipe(takeUntilDestroyed()).subscribe({
      next: notifs => this._notifications.set(notifs),
    });
  }

  isWatching(url: string): boolean {
    return this.watchedUrls().has(url);
  }

  findByUrl(url: string): Notification | undefined {
    return this._notifications().find(n => n.url === url);
  }

  replaceOne(updated: Notification): void {
    this._notifications.update(ns =>
      ns.map(n => n.id === updated.id ? updated : n)
    );
  }

  toggle(result: WatchableResult): void {
    const existing = this.findByUrl(result.url);
    if (existing) {
      this.api.removeNotification(existing.id).subscribe({
        next: () => this._notifications.update(ns => ns.filter(n => n.id !== existing.id)),
      });
    } else {
      this.api.addNotification({
        title: result.title,
        url: result.url,
        source: result.source,
        poster_url: result.poster_url ?? null,
      }).subscribe({
        next: notif => this._notifications.update(ns => [notif, ...ns]),
      });
    }
  }
}
