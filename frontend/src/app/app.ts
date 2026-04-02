import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { SidebarComponent } from './shared/components/sidebar/sidebar.component';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, SidebarComponent],
  template: `
    <div class="min-h-screen flex">
      <app-sidebar />
      <div class="ml-52 flex-1 flex flex-col">
        <router-outlet />
      </div>
    </div>
  `,
})
export class App {}
