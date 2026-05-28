let sidebarExpanded = $state(false);
let activeModule = $state<string | null>(null);

export const consoleState = {
  get sidebarExpanded() {
    return sidebarExpanded;
  },
  set sidebarExpanded(v: boolean) {
    sidebarExpanded = v;
  },
  get activeModule() {
    return activeModule;
  },
  set activeModule(v: string | null) {
    activeModule = v;
  },
  toggleSidebar() {
    sidebarExpanded = !sidebarExpanded;
  },
};
