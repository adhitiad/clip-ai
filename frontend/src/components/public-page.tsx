import type { ReactNode } from 'react'

import { Link } from '@tanstack/react-router'
import { ClapperboardIcon, LayoutDashboardIcon, LogOutIcon } from 'lucide-react'

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
import { authClient } from '#/lib/auth-client'

export const publicLinks = [
  { label: 'Beranda', to: '/landing' },
  { label: 'Tentang', to: '/about' },
  { label: 'Ketentuan', to: '/tos' },
  { label: 'Privasi', to: '/privacy' },
  { label: 'Kontak', to: '/contact' },
] as const

const PublicSessionButton = () => {
  const { data: session, isPending } = authClient.useSession()

  if (isPending) {
    return <div className="size-9 shrink-0" aria-hidden="true" />
  }

  if (!session?.user) {
    return (
      <Button asChild className="shonen-action min-h-9 px-4" size="sm">
        <Link to="/login">Masuk</Link>
      </Button>
    )
  }

  const name = session.user.name
  const email = session.user.email
  const initials = name.slice(0, 2).toUpperCase()

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          className="min-h-9 w-9 rounded-full p-0"
          aria-label="Menu akun"
        >
          <Avatar className="size-9">
            {session.user.image ? (
              <AvatarImage src={session.user.image} alt={name} />
            ) : null}
            <AvatarFallback>{initials}</AvatarFallback>
          </Avatar>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" side="bottom">
        <DropdownMenuLabel>
          <span className="block truncate font-medium">{name}</span>
          <span className="block truncate text-xs text-muted-foreground">
            {email}
          </span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link to="/dashboard">
            <LayoutDashboardIcon aria-hidden="true" />
            Dashboard
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem
          onSelect={() => {
            void authClient.signOut()
          }}
        >
          <LogOutIcon aria-hidden="true" />
          Keluar
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

export const PublicNav = () => (
  <nav
    aria-label="Navigasi publik"
    className="flex flex-wrap items-center justify-end gap-4 text-sm"
  >
    {publicLinks.map((link) => (
      <Link key={link.to} to={link.to}>
        {link.label}
      </Link>
    ))}
    <PublicSessionButton />
  </nav>
)

export const PublicFooter = () => (
  <footer className="m-4 rounded-xl border border-[var(--line)] bg-[var(--panel)]">
    <div className="mx-auto w-full max-w-screen-xl p-4 md:flex md:items-center md:justify-between">
      <span className="text-center text-sm text-[var(--ink-muted)] sm:text-left">
        © 2026 Clip AI. Project pribadi.
      </span>
      <ul className="mt-3 flex flex-wrap items-center gap-4 text-sm font-medium text-[var(--ink-muted)] md:mt-0 md:gap-6">
        {publicLinks.map((link) => (
          <li key={link.to}>
            <Link to={link.to} className="hover:underline">
              {link.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  </footer>
)

export const PublicPage = ({
  title,
  intro,
  children,
}: {
  title: string
  intro: string
  children: ReactNode
}) => (
  <main className="page-wrap pb-16">
    <header className="flex flex-wrap items-center justify-between gap-3 py-6">
      <Link to="/landing" className="flex items-center gap-2">
        <ClapperboardIcon
          className="size-8 text-[var(--neon-soft)]"
          aria-hidden="true"
        />
        <span className="neon-text text-sm font-semibold">Clip AI</span>
      </Link>
      <PublicNav />
    </header>

    <h1 className="neon-text display-title rise-in text-3xl font-bold">
      {title}
    </h1>
    <p className="mt-3 max-w-2xl text-[15px] leading-relaxed text-[var(--ink-muted)]">
      {intro}
    </p>

    <div className="mt-8 space-y-6">{children}</div>

    <PublicFooter />
  </main>
)
