export interface Notification {
  id: string;
  title: string;
  url: string;
  source: string;
  poster_url: string | null;
  last_episode_count: number;
  last_checked_at: string | null;
  auto_download: boolean;
  discord_notify: boolean;
}

export interface NotificationCreate {
  title: string;
  url: string;
  source: string;
  poster_url?: string | null;
}

export interface NotificationPatch {
  auto_download?: boolean;
  discord_notify?: boolean;
}
