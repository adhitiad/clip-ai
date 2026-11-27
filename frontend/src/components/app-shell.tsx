import { Link, useRouterState } from '@tanstack/react-router'
import {
  ClapperboardIcon,
  DatabaseIcon,
  HistoryIcon,
  HouseIcon,
  LayoutDashboardIcon,
  SearchIcon,
  ShieldIcon,
  WrenchIcon,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'

import { Avatar, AvatarFallback, AvatarImage } from '#/components/ui/avatar'
import { Button } from '#/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '#/components/ui/dropdown-menu'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarInset,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
  SidebarRail,
  SidebarTrigger,
} from '#/components/ui/sidebar'
import { authClient } from '#/lib/auth-client'

type RoutePath =
  | '/'
  | '/shorts'
  | '/niche'
  | '/history'
  | '/dashboard'
  | '/tools'
  | '/backend'
  | '/protected'

type NavItem = {
  title: string
  to: RoutePath
}

type NavGroup = { label: string; items: NavItem[] }

const navGroups: NavGroup[] = [
  {
    label: 'Kerja',
    items: [
      { title: 'Beranda', to: '/' },
      { title: 'Shorts', to: '/shorts' },
      { title: 'Penemuan', to: '/niche' },
      { title: 'Riwayat', to: '/history' },
    ],
  },
  {
    label: 'Sistem',
    items: [
      { title: 'Dashboard', to: '/dashboard' },
      { title: 'Alat', to: '/tools' },
      { title: 'Backend', to: '/backend' },
      { title: 'Ruang Kerja', to: '/protected' },
    ],
  },
]

const icons: Record<RoutePath, LucideIcon> = {
  '/': HouseIcon,
  '/shorts': ClapperboardIcon,
  '/niche': SearchIcon,
  '/history': HistoryIcon,
  '/dashboard': LayoutDashboardIcon,
  '/tools': WrenchIcon,
  '/backend': DatabaseIcon,
  '/protected': ShieldIcon,
}

const bottomNav = [
  { title: 'Beranda', to: '/' },
  { title: 'Shorts', to: '/shorts' },
  { title: 'Penemuan', to: '/niche' },
  { title: 'Riwayat', to: '/history' },
  { title: 'Dashboard', to: '/dashboard' },
  { title: 'Alat', to: '/tools' },
  { title: 'Backend', to: '/backend' },
  { title: 'Ruang Kerja', to: '/protected' },
] as const

const navItems = navGroups.flatMap((group) => group.items)

const TopNav = ({ pathname }: { pathname: string }) => (
  <nav
    aria-label="Navigasi utama"
    className="hidden flex-1 items-center gap-1 overflow-x-auto lg:flex"
  >
    {navItems.map((item) => (
      <Link
        key={item.to}
        to={item.to}
        aria-current={pathname === item.to ? 'page' : undefined}
        className={`shrink-0 rounded-md px-2 py-1 text-[13px] transition-colors ${
          pathname === item.to
            ? 'bg-[var(--raised)] text-[var(--neon-soft)]'
            : 'text-[var(--ink-muted)] hover:text-[var(--ink)]'
        }`}
      >
        {item.title}
      </Link>
    ))}
  </nav>
)

const UserMenu = () => {
  const { data: session } = authClient.useSession()
  const user = session?.user
  const name = user?.name ?? 'Owner'
  const initials = user?.name ? name.slice(0, 2).toUpperCase() : 'OW'

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          className="min-h-11 w-full justify-start gap-2 p-2"
        >
          <Avatar>
            {user?.image ? <AvatarImage src={user.image} alt={name} /> : null}
            <AvatarFallback>{initials}</AvatarFallback>
          </Avatar>
          <span className="min-w-0 flex-1 truncate text-sm">{name}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" side="top">
        <DropdownMenuLabel>
          <span className="block truncate">{user?.email ?? 'Belum login'}</span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem
          onSelect={() => {
            void authClient.signOut()
          }}
        >
          Keluar
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

const AppSidebar = () => {
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  })

  return (
    <Sidebar collapsible="icon">
      <SidebarHeader>
        <div className="speed-lines flex items-center gap-2 px-2 py-1">
          <ClapperboardIcon
            className="size-7 shrink-0 text-[var(--neon)]"
            aria-hidden="true"
          />
          <span className="font-display neon-text text-lg">Clip AI</span>
        </div>
      </SidebarHeader>
      <SidebarContent>
        {navGroups.map((group) => (
          <SidebarGroup key={group.label}>
            <SidebarGroupLabel>{group.label}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {group.items.map((item) => {
                  const Icon = icons[item.to]
                  return (
                    <SidebarMenuItem key={item.to}>
                      <SidebarMenuButton
                        asChild
                        isActive={pathname === item.to}
                      >
                        <Link to={item.to} className="text-sidebar-foreground">
                          <Icon className="size-5" aria-hidden="true" />
                          <span>{item.title}</span>
                        </Link>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  )
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>
      <SidebarFooter>
        <UserMenu />
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  )
}

const MobileNav = ({ pathname }: { pathname: string }) => (
  <nav
    aria-label="Navigasi utama"
    className="fixed inset-x-0 bottom-0 z-40 border-t border-[var(--line)] bg-[var(--panel)] pb-[env(safe-area-inset-bottom)] md:hidden"
  >
    <ul className="grid grid-cols-4">
      {bottomNav.map((item) => {
        const active = pathname === item.to
        const Icon = icons[item.to]
        return (
          <li key={item.to} className="px-1 py-1">
            <Link
              to={item.to}
              aria-current={active ? 'page' : undefined}
              className={`flex min-h-14 flex-col items-center justify-center gap-1 rounded-xl py-2 text-[12px] transition-colors ${
                active
                  ? 'bg-[var(--raised)] text-[var(--neon-soft)]'
                  : 'text-[var(--ink-muted)]'
              }`}
            >
              <Icon className="size-5" aria-hidden="true" />
              <span>{item.title}</span>
            </Link>
          </li>
        )
      })}
    </ul>
  </nav>
)

export const AppShell = ({ children }: { children: React.ReactNode }) => {
  const pathname = useRouterState({
    select: (state) => state.location.pathname,
  })
  const dataRoute = pathname === '/history'

  return (
    <>
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-background focus:px-3 focus:py-2 focus:text-sm"
      >
        Lewati ke konten
      </a>
      <SidebarProvider>
        <AppSidebar />
        <SidebarInset>
          <header className="speed-lines flex min-h-12 items-center gap-2 border-b border-[var(--line)] bg-[var(--panel)] px-4">
            <SidebarTrigger />
            <span className="font-display neon-text shrink-0 text-lg">
              Clip AI
            </span>
            <TopNav pathname={pathname} />
          </header>
          <main
            id="main"
            tabIndex={-1}
            className={`rise-in p-4 sm:p-6 ${dataRoute ? 'pb-6' : 'pb-24 md:pb-6'}`}
          >
            {children}
          </main>
        </SidebarInset>
      </SidebarProvider>
      {dataRoute ? null : <MobileNav pathname={pathname} />}
    </>
  )
}
