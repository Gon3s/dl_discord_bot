import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import type { SearchResponse } from '../models/search.type';
import type { Download, DownloadCreated, StartDownloadPayload } from '../models/download.type';
import type { HistoryList } from '../models/history.type';
import type { SettingRead } from '../models/setting.type';
import type { ApiStatus } from '../models/api-status.type';
import type { Episode } from '../models/episode.type';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly base = '/api/v1';

  search(query: string, category: string, year?: string, limit = 20, sort?: string): Observable<SearchResponse> {
    let params = new HttpParams().set('q', query).set('category', category).set('limit', limit);
    if (year) params = params.set('year', year);
    if (sort) params = params.set('sort', sort);
    return this.http.get<SearchResponse>(`${this.base}/search`, { params });
  }

  startDownload(payload: StartDownloadPayload): Observable<DownloadCreated> {
    return this.http.post<DownloadCreated>(`${this.base}/downloads`, payload);
  }

  getDownloads(): Observable<Download[]> {
    return this.http.get<Download[]>(`${this.base}/downloads`);
  }

  getDownload(id: string): Observable<Download> {
    return this.http.get<Download>(`${this.base}/downloads/${id}`);
  }

  cancelDownload(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/downloads/${id}`);
  }

  getHistory(params?: {
    q?: string;
    status?: string;
    provider?: string;
    from?: string;
    to?: string;
    page?: number;
    page_size?: number;
  }): Observable<HistoryList> {
    let p = new HttpParams();
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== '') p = p.set(k, String(v));
      });
    }
    return this.http.get<HistoryList>(`${this.base}/history`, { params: p });
  }

  deleteHistory(id: string): Observable<void> {
    return this.http.delete<void>(`${this.base}/history/${id}`);
  }

  getSettings(): Observable<SettingRead[]> {
    return this.http.get<SettingRead[]>(`${this.base}/settings`);
  }

  saveSettings(settings: Record<string, string>): Observable<SettingRead[]> {
    return this.http.put<SettingRead[]>(`${this.base}/settings`, { settings });
  }

  getStatus(): Observable<ApiStatus> {
    return this.http.get<ApiStatus>(`${this.base}/status`);
  }

  getEpisodes(url: string, source = 'wawacity', providers?: string[]): Observable<Episode[]> {
    let params = new HttpParams().set('url', url).set('source', source);
    if (providers?.length) params = params.set('providers', providers.join(','));
    return this.http.get<Episode[]>(`${this.base}/episodes`, { params });
  }
}
