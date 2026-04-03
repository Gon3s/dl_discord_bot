import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { webSocket, WebSocketSubject } from 'rxjs/webSocket';

export interface QueueEvent {
  type: string;
  download_id: string;
  status: string;
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
    if (!this.queueSocket || this.queueSocket.closed) {
      this.queueSocket = webSocket<QueueEvent>(`${this.wsBase}/queue`);
    }
    return this.queueSocket.asObservable();
  }

  watchDownload(id: string): Observable<QueueEvent> {
    const socket = webSocket<QueueEvent>(`${this.wsBase}/downloads/${id}`);
    return socket.asObservable();
  }

  closeQueue(): void {
    this.queueSocket?.complete();
  }
}
