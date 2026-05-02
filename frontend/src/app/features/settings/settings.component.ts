import { Component, signal, computed, linkedSignal, inject, ChangeDetectionStrategy, DestroyRef } from '@angular/core';
import { rxResource, takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DecimalPipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '#core/services/api.service';
import { CATEGORIES } from '#core/constants/media';
import { ALL_PROVIDERS } from '#core/constants/media';

@Component({
  selector: 'app-settings',
  imports: [FormsModule, DecimalPipe],
  templateUrl: './settings.component.html',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SettingsComponent {
  private readonly api = inject(ApiService);
  private readonly destroyRef = inject(DestroyRef);

  protected readonly resource = rxResource({
    stream: () => this.api.getSettings(),
  });

  protected readonly statusResource = rxResource({
    stream: () => this.api.getStatus(),
  });

  protected loading = computed(() => this.resource.isLoading());
  protected debridOk = computed(() => {
    const status = this.statusResource.value();
    return status?.debrid_ok ?? status?.alldebrid_ok;
  });
  protected statusDebridProvider = computed(() => this.statusResource.value()?.debrid_provider);
  protected diskFreeGb = computed(() => this.statusResource.value()?.disk_free_gb);

  private getSetting(key: string, fallback = ''): string {
    return this.resource.value()?.find(s => s.key === key)?.value ?? fallback;
  }

  // Each field auto-initializes from the resource and can be independently edited
  protected downloadPath = linkedSignal(() => this.getSetting('download_path'));
  protected wawacityUrl = linkedSignal(() => this.getSetting('wawacity_url'));
  protected defaultCategory = linkedSignal(() => this.getSetting('default_category', 'films'));
  protected maxConcurrent = linkedSignal(() => this.getSetting('max_concurrent_downloads', '2'));
  protected debridProvider = linkedSignal(() => this.getSetting('debrid_provider', this.statusDebridProvider() ?? 'alldebrid'));
  protected alldebridApiKey = linkedSignal(() => this.getSetting('alldebrid_api_key'));
  protected realdebridApiToken = linkedSignal(() => this.getSetting('realdebrid_api_token'));
  protected enabledProviders = linkedSignal<string[]>(() => {
    const v = this.getSetting('default_providers');
    try { return v ? JSON.parse(v) : [...ALL_PROVIDERS]; } catch { return [...ALL_PROVIDERS]; }
  });

  protected saving = signal(false);
  protected saved = signal(false);
  protected showApiKey = signal(false);

  protected readonly categories = CATEGORIES;
  protected readonly allProviders = ALL_PROVIDERS;
  protected readonly debridProviders = [
    { value: 'alldebrid', label: 'AllDebrid' },
    { value: 'realdebrid', label: 'Real-Debrid' },
  ];
  protected activeDebridSecret = computed(() =>
    this.debridProvider() === 'realdebrid' ? this.realdebridApiToken() : this.alldebridApiKey()
  );
  protected activeDebridSecretLabel = computed(() =>
    this.debridProvider() === 'realdebrid' ? 'API TOKEN' : 'API KEY'
  );

  setActiveDebridSecret(value: string): void {
    if (this.debridProvider() === 'realdebrid') {
      this.realdebridApiToken.set(value);
      return;
    }
    this.alldebridApiKey.set(value);
  }

  isProviderEnabled(p: string): boolean {
    return this.enabledProviders().includes(p);
  }

  toggleProvider(p: string): void {
    this.enabledProviders.update(cur =>
      cur.includes(p) ? cur.filter(x => x !== p) : [...cur, p]
    );
  }

  save(): void {
    this.saving.set(true);
    this.api.saveSettings({
      download_path: this.downloadPath(),
      wawacity_url: this.wawacityUrl(),
      default_category: this.defaultCategory(),
      max_concurrent_downloads: this.maxConcurrent(),
      debrid_provider: this.debridProvider(),
      alldebrid_api_key: this.alldebridApiKey(),
      realdebrid_api_token: this.realdebridApiToken(),
      default_providers: JSON.stringify(this.enabledProviders()),
    }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.resource.reload();
        this.statusResource.reload();
        this.saving.set(false);
        this.saved.set(true);
        setTimeout(() => this.saved.set(false), 2000);
      },
      error: () => this.saving.set(false),
    });
  }
}
