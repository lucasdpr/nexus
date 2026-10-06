"use client";

import { useMutation } from "@tanstack/react-query";
import { LibraryBig, LogOut, MessageSquareText } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

import { Wordmark } from "@/components/nexus/wordmark";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { api, type Me } from "@/lib/api/client";
import { MeProvider } from "@/lib/me-context";
import { cn } from "@/lib/utils";

const NAVIGATION = [
  { href: "/perguntar", label: "Perguntar", icon: MessageSquareText },
  { href: "/biblioteca", label: "Biblioteca", icon: LibraryBig },
] as const;

const ROLE_NAMES: Record<Me["user"]["role"], string> = {
  ADMIN: "Administração",
  MANAGER: "Gestão",
  MEMBER: "Consulta",
};

function initials(name: string): string {
  const parts = name.trim().split(/\s+/);
  return ((parts[0]?.[0] ?? "") + (parts.length > 1 ? (parts.at(-1)?.[0] ?? "") : "")).toUpperCase();
}

export function AppShell({ me, children }: { me: Me; children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const logout = useMutation({
    mutationFn: () => api.POST("/api/v1/auth/logout"),
    onSettled: () => router.replace("/entrar"),
  });

  const isActive = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

  return (
    <div className="min-h-dvh md:grid md:grid-cols-[15rem_minmax(0,1fr)]">
      <a
        href="#conteudo"
        className="sr-only z-50 rounded-md bg-primary px-3 py-2 text-primary-foreground focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
      >
        Pular para o conteúdo
      </a>

      <aside className="sticky top-0 hidden h-dvh flex-col border-r border-sidebar-border bg-sidebar md:flex">
        <div className="px-5 pt-5 pb-4">
          <Wordmark className="text-base" />
          <p className="mt-2 truncate text-[13px] text-muted-foreground">{me.organization.name}</p>
          {me.organization.is_demo && (
            <p className="mt-2 rounded-sm bg-evidence-soft px-2 py-1 text-[12px] leading-snug text-foreground">
              Demonstração com documentos fictícios
            </p>
          )}
        </div>

        <nav aria-label="Principal" className="flex-1 space-y-0.5 px-3">
          {NAVIGATION.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              aria-current={isActive(href) ? "page" : undefined}
              className={cn(
                "flex h-9 items-center gap-2.5 rounded-md px-2.5 text-[14px] text-sidebar-foreground/80 transition-colors hover:bg-sidebar-accent hover:text-sidebar-foreground",
                isActive(href) && "bg-sidebar-accent font-medium text-sidebar-foreground",
              )}
            >
              <Icon className="size-4" aria-hidden />
              {label}
            </Link>
          ))}
        </nav>

        <div className="border-t border-sidebar-border p-3">
          <DropdownMenu>
            <DropdownMenuTrigger className="flex w-full items-center gap-2.5 rounded-md p-2 text-left hover:bg-sidebar-accent">
              <span className="grid size-8 shrink-0 place-items-center rounded-full bg-primary text-[12px] font-semibold text-primary-foreground">
                {initials(me.user.name)}
              </span>
              <span className="min-w-0">
                <span className="block truncate text-[13px] font-medium">{me.user.name}</span>
                <span className="block truncate text-[12px] text-muted-foreground">{ROLE_NAMES[me.user.role]}</span>
              </span>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="w-56">
              <DropdownMenuLabel className="truncate font-normal text-muted-foreground">
                {me.user.email}
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={() => logout.mutate()} disabled={logout.isPending}>
                <LogOut aria-hidden />
                Sair
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </aside>

      <div className="flex min-h-dvh min-w-0 flex-col pb-16 md:pb-0">
        <header className="flex h-12 items-center justify-between border-b border-border px-4 md:hidden">
          <Wordmark className="text-[15px]" />
          <button
            type="button"
            onClick={() => logout.mutate()}
            className="rounded-md px-2 py-1 text-[13px] text-muted-foreground hover:bg-accent"
          >
            Sair
          </button>
        </header>
        <main id="conteudo" className="flex min-h-0 flex-1 flex-col">
          <MeProvider value={me}>{children}</MeProvider>
        </main>
      </div>

      <nav
        aria-label="Principal"
        className="fixed inset-x-0 bottom-0 z-40 grid h-16 grid-cols-2 border-t border-border bg-background/95 backdrop-blur md:hidden"
      >
        {NAVIGATION.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            aria-current={isActive(href) ? "page" : undefined}
            className={cn(
              "flex flex-col items-center justify-center gap-1 text-[12px] text-muted-foreground",
              isActive(href) && "font-medium text-primary",
            )}
          >
            <Icon className="size-5" aria-hidden />
            {label}
          </Link>
        ))}
      </nav>
    </div>
  );
}
