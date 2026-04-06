import { Injectable, computed, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ApiService } from './api.service';
import type { Favorite } from '../models/favorite.type';
import type { SearchResult } from '../models/search.type';

@Injectable({ providedIn: 'root' })
export class FavoriteService {
  private readonly api = inject(ApiService);

  private readonly _favorites = signal<Favorite[]>([]);

  readonly favorites = this._favorites.asReadonly();

  readonly favoriteUrls = computed(() => new Set(this._favorites().map(f => f.url)));

  constructor() {
    this.api.getFavorites().pipe(takeUntilDestroyed()).subscribe({
      next: favs => this._favorites.set(favs),
    });
  }

  isFavorite(url: string): boolean {
    return this.favoriteUrls().has(url);
  }

  findByUrl(url: string): Favorite | undefined {
    return this._favorites().find(f => f.url === url);
  }

  toggle(result: SearchResult): void {
    const existing = this.findByUrl(result.url);
    if (existing) {
      this.api.removeFavorite(existing.id).subscribe({
        next: () => this._favorites.update(favs => favs.filter(f => f.id !== existing.id)),
      });
    } else {
      this.api.addFavorite({
        title: result.title,
        url: result.url,
        category: result.category,
        year: result.year,
        quality: result.quality,
        language: result.language,
        source: result.source,
        poster_url: result.poster_url,
      }).subscribe({
        next: fav => this._favorites.update(favs => [fav, ...favs]),
      });
    }
  }
}
