import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: 'search', pathMatch: 'full' },
  { path: 'search', loadChildren: () => import('./features/search/search.routes') },
  { path: 'downloads', loadChildren: () => import('./features/downloads/downloads.routes') },
  { path: 'history', loadChildren: () => import('./features/history/history.routes') },
  { path: 'favorites', loadChildren: () => import('./features/favorites/favorites.routes') },
  { path: 'settings', loadChildren: () => import('./features/settings/settings.routes') },
];
