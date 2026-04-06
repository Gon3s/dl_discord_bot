import { Component, ChangeDetectionStrategy, inject, signal, computed, linkedSignal } from '@angular/core';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { FavoriteService } from '#core/services/favorite.service';
import { SearchStateService } from '#core/services/search-state.service';
import { CATEGORIES } from '#core/constants/media';
import type { Favorite } from '#core/models/favorite.type';
import type { SearchResult } from '#core/models/search.type';

type SortOption = 'added_at' | 'title';

@Component({
  selector: 'app-favorites',
  imports: [FormsModule],
  templateUrl: './favorites.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class FavoritesComponent {
  private readonly router = inject(Router);
  protected readonly favoriteService = inject(FavoriteService);
  private readonly state = inject(SearchStateService);

  protected readonly categories = ['tous', ...CATEGORIES];
  protected readonly filterCategory = signal<string>('tous');
  protected readonly sortBy = linkedSignal<SortOption>(() => { this.filterCategory(); return 'added_at'; });

  protected readonly filtered = computed(() => {
    const cat = this.filterCategory();
    const sort = this.sortBy();
    let items = [...this.favoriteService.favorites()];

    if (cat !== 'tous') {
      items = items.filter(f => f.category === cat);
    }

    if (sort === 'title') {
      items.sort((a, b) => a.title.localeCompare(b.title));
    }
    // 'added_at' is already desc from the API

    return items;
  });

  qualityColor(quality: string | null): string {
    if (!quality) return '#8a9a55';
    if (quality === '4K' || quality === '2160p') return '#e8d62a';
    if (quality === '1080p') return 'var(--lime)';
    return '#8a9a55';
  }

  openFavorite(fav: Favorite): void {
    const result: SearchResult = {
      title: fav.title,
      url: fav.url,
      category: fav.category,
      year: fav.year,
      quality: fav.quality,
      language: fav.language,
      source: fav.source,
      poster_url: fav.poster_url,
    };
    this.state.category.set(fav.category ?? 'films');
    this.state.pendingResult.set(result);
    this.router.navigate(['/search']);
  }
}
