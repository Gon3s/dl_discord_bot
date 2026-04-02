import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, map } from 'rxjs';

export interface SearchResult {
  title: string;
  url: string;
  year: number | null;
  category: string | null;
  quality: string | null;
  language: string | null;
  source: string;
  poster_url: string | null;
}

export interface SearchResponse {
  results: SearchResult[];
  total: number;
  source: string;
}

export interface Download {
  id: string;
  title: string;
  source_url: string;
  media_type: string;
  destination: string;
  status: string;
  progress_pct: number;
  speed_mbps: number | null;
  filename: string | null;
  created_at: string;
  completed_at: string | null;
  error: string | null;
}

export interface DownloadCreated {
  download_id: string;
  status: string;
}

export interface HistoryRead {
  id: string;
  title: string;
  source_url: string;
  filename: string | null;
  media_type: string;
  source: string;
  status: string;
  created_at: string;
}

export interface HistoryList {
  items: HistoryRead[];
  total: number;
  page: number;
  limit: number;
}

export interface SettingRead {
  key: string;
  value: string;
}

export interface StartDownloadPayload {
  source_url: string;
  title: string;
  media_type: string;
  destination: 'server' | 'client';
}

export interface ApiStatus {
  queue_size: number;
  active: number;
  disk_free_gb: number;
  alldebrid_ok: boolean;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);
  private readonly base = '/api/v1';

  search(query: string, category: string, year?: string, limit = 20): Observable<SearchResponse> {
    let params = new HttpParams()
      .set('q', query)
      .set('category', category)
      .set('limit', limit);
    if (year) params = params.set('year', year);
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
}
