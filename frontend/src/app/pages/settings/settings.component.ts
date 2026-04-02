import { Component, OnInit, signal, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-settings',
  imports: [FormsModule],
  templateUrl: './settings.component.html',
})
export class SettingsComponent implements OnInit {
  private readonly api = inject(ApiService);

  // Flat key→value map built from the API's [{key,value}] array
  protected settings = signal<Record<string, string>>({});
  protected loading = signal(true);
  protected saving = signal(false);
  protected saved = signal(false);
  protected showApiKey = signal(false);

  protected readonly categories = ['films', 'series', 'mangas'];
  protected readonly allProviders = ['1fichier', 'Turbobit', 'Rapidgator'];

  ngOnInit(): void {
    this.api.getSettings().subscribe({
      next: (list) => {
        const map: Record<string, string> = {};
        list.forEach(s => map[s.key] = s.value);
        this.settings.set(map);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  get(key: string, fallback = ''): string {
    return this.settings()[key] ?? fallback;
  }

  set(key: string, value: string): void {
    this.settings.update(s => ({ ...s, [key]: value }));
  }

  save(): void {
    this.saving.set(true);
    this.api.saveSettings(this.settings()).subscribe({
      next: (list) => {
        const map: Record<string, string> = {};
        list.forEach(s => map[s.key] = s.value);
        this.settings.set(map);
        this.saving.set(false);
        this.saved.set(true);
        setTimeout(() => this.saved.set(false), 2000);
      },
      error: () => this.saving.set(false),
    });
  }

  enabledProviders(): string[] {
    const v = this.get('default_providers');
    try { return v ? JSON.parse(v) : this.allProviders; } catch { return this.allProviders; }
  }

  isProviderEnabled(p: string): boolean {
    return this.enabledProviders().includes(p);
  }

  toggleProvider(p: string): void {
    const cur = this.enabledProviders();
    const next = cur.includes(p) ? cur.filter(x => x !== p) : [...cur, p];
    this.set('default_providers', JSON.stringify(next));
  }
}
