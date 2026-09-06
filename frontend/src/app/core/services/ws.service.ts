import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { defer, retry } from 'rxjs';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';
import type { DownloadStatus } from '../constants/download-status';

export interface QueueEvent {
  type: string;
  download_id: string;
  status: DownloadStatus;
  progress_pct?: number;
  speed_mbps?: number;
  eta_s?: number;
  filename?: string;
  debrid_url?: string;
  error?: string;
}

@Injectable({ providedIn: 'root' })
export class WsService {
  private readonly wsBase = `ws://${window.location.host}/ws`;
  private queueSocket?: WebSocketSubject<QueueEvent>;

  watchQueue(): Observable<QueueEvent> {
    return defer(() => {
      this.queueSocket = webSocket<QueueEvent>(`${this.wsBase}/queue`);
      return this.queueSocket;
    }).pipe(retry({ delay: 3000 }));
  }

  watchDownload(id: string): Observable<QueueEvent> {
    return webSocket<QueueEvent>(`${this.wsBase}/downloads/${id}`);
  }

  closeQueue(): void {
    this.queueSocket?.complete();
  }
}
