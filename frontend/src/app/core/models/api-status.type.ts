export type ApiStatus = {
  queue_size: number;
  active: number;
  disk_free_gb: number;
  debrid_ok: boolean;
  debrid_provider: string;
  alldebrid_ok: boolean;
};
