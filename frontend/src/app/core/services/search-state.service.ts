import { Injectable, linkedSignal, signal } from '@angular/core';

export type SearchParams = {
  q: string;
  category: string;
  year?: string;
  sort?: string;
};

@Injectable({ providedIn: 'root' })
export class SearchStateService {
  readonly query = signal('');
  readonly category = signal('films');
  readonly year = signal('');
  readonly sort = linkedSignal<string>(() => { this.category(); return ''; });
  readonly searchParams = signal<SearchParams | undefined>(undefined);
  readonly destination = signal<'server' | 'client'>(
    (localStorage.getItem('dl_destination') as 'server' | 'client') ?? 'server'
  );

  setDestination(value: 'server' | 'client'): void {
    this.destination.set(value);
    localStorage.setItem('dl_destination', value);
  }
}
