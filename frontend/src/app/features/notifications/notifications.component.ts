import { Component, ChangeDetectionStrategy, inject, signal, DestroyRef } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { ApiService } from '#core/services/api.service';
import { NotificationWatchService } from '#core/services/notification-watch.service';
import type { Notification } from '#core/models/notification.type';
import type { SearchResult } from '#core/models/search.type';

@Component({
  selector: 'app-notifications',
  imports: [FormsModule],
  templateUrl: './notifications.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NotificationsComponent {
  private readonly api = inject(ApiService);
  private readonly destroyRef = inject(DestroyRef);
  protected readonly watchService = inject(NotificationWatchService);

  protected readonly addPanelOpen = signal(false);
  protected readonly searchQuery = signal('');
  protected readonly searchSource = signal('wawacity');
  protected readonly searchResults = signal<SearchResult[]>([]);
  protected readonly searching = signal(false);
  protected readonly testingDiscord = signal(false);
  protected readonly testResult = signal<'ok' | 'error' | null>(null);

  protected notifications = this.watchService.notifications;

  formatDate(dateStr: string | null): string {
    if (!dateStr) return 'Jamais';
    const d = new Date(dateStr);
    return d.toLocaleDateString('fr-FR', {
      day: '2-digit', month: '2-digit', year: '2-digit',
      hour: '2-digit', minute: '2-digit',
    });
  }

  toggleAddPanel(): void {
    this.addPanelOpen.update(v => !v);
    if (!this.addPanelOpen()) {
      this.searchQuery.set('');
      this.searchResults.set([]);
    }
  }

  runSearch(): void {
    const q = this.searchQuery().trim();
    if (!q) return;
    this.searching.set(true);
    this.api.search(q, 'series', undefined, 10, undefined, 1, this.searchSource())
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (res) => {
          this.searchResults.set(res.results);
          this.searching.set(false);
        },
        error: () => { this.searching.set(false); },
      });
  }

  addFromSearch(result: SearchResult): void {
    this.watchService.toggle(result);
    this.addPanelOpen.set(false);
    this.searchQuery.set('');
    this.searchResults.set([]);
  }

  remove(notif: Notification): void {
    this.watchService.toggle({ title: notif.title, url: notif.url, source: notif.source });
  }

  testDiscord(): void {
    if (this.testingDiscord()) return;
    this.testingDiscord.set(true);
    this.testResult.set(null);
    this.api.testDiscordNotification()
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: () => { this.testingDiscord.set(false); this.testResult.set('ok'); },
        error: () => { this.testingDiscord.set(false); this.testResult.set('error'); },
      });
  }

  toggleField(notif: Notification, field: 'auto_download' | 'discord_notify'): void {
    const patch = { [field]: !notif[field] };
    this.api.patchNotification(notif.id, patch)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: (updated) => this.watchService.replaceOne(updated) });
  }
}
