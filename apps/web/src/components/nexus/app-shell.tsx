"use client";

import { useMutation } from "@tanstack/react-query";
import { FolderTree, Gauge, LibraryBig, LogOut, MessageSquareText, ScrollText, Search, Users } from "lucide-react";
import { motion } from "motion/react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { LIQUID, SPRING } from "@/components/fx/motion";
import { CommandPalette } from "@/components/nexus/command-palette";
import { RecentConversations } from "@/components/nexus/recent-conversations";
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
import { usePipelineStats } from "@/lib/pipeline-stats";
import { cn } from "@/lib/utils";

function navigationFor(role: Me["user"]["role"]) {
  return [
    { href: "/painel", label: "Painel", icon: Gauge },
    { href: "/perguntar", label: "Perguntar", icon: MessageSquareText },
    { href: "/biblioteca", label: "Biblioteca", icon: LibraryBig },
    ...(role !== "MEMBER"
      ? [
          { href: "/colecoes", label: "Coleções", icon: FolderTree },
          { href: "/usuarios", label: "Usuários", icon: Users },
        ]
      : []),
    ...(role === "ADMIN" ? [{ href: "/auditoria", label: "Auditoria", icon: ScrollText }] : []),
  ];
}

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
  const [searchOpen, setSearchOpen] = useState(false);
  const navigation = navigationFor(me.user.role);
  const logout = useMutation({
    mutationFn: () => api.POST("/api/v1/auth/logout"),
    onSettled: () => router.replace("/entrar"),
  });

  const isActive = (href: string) => pathname === href || pathname.startsWith(`${href}/`);

  return (
    <MeProvider value={me}>
      <div className="min-h-dvh md:grid md:grid-cols-[17rem_minmax(0,1fr)]">
        <a
          href="#conteudo"
          className="sr-only z-50 rounded-md bg-primary px-3 py-2 text-primary-foreground focus:not-sr-only focus:fixed focus:top-3 focus:left-3"
        >
          Pular para o conteúdo
        </a>

        {/* Barra lateral em cápsula: flutua a 12px das bordas, em vidro fosco. */}
        <div className="sticky top-0 hidden h-dvh p-3 md:block">
          <aside className="glass flex h-full flex-col rounded-2xl shadow-[0_20px_60px_-20px_rgb(0_0_0/0.7)]">
            <div className="px-5 pt-5 pb-4">
              <Wordmark className="text-base" />
            </div>

            <button
              type="button"
              onClick={() => setSearchOpen(true)}
              className="mx-3 mb-3 flex h-10 items-center gap-2.5 rounded-xl border border-white/10 bg-white/[0.03] px-3 text-left text-[14px] text-muted-foreground transition-colors hover:border-neon-indigo/50 hover:text-foreground"
            >
              <Search className="size-4" aria-hidden />
              <span className="flex-1">Buscar</span>
              <kbd className="rounded-md border border-white/10 px-1.5 text-[11px]">Ctrl K</kbd>
            </button>

            <nav aria-label="Principal" className="space-y-1 px-3">
              {navigation.map(({ href, label, icon: Icon }) => {
                const active = isActive(href);
                return (
                  <Link
                    key={href}
                    href={href}
                    aria-current={active ? "page" : undefined}
                    className="group/nav relative flex h-10 items-center gap-3 rounded-xl px-3 text-[14px] text-sidebar-foreground/75 transition-colors hover:text-sidebar-foreground"
                  >
                    {/* Indicador líquido: o mesmo layoutId "escorre" de um item ao outro numa mola. */}
                    {active && (
                      <motion.span
                        layoutId="nav-drop"
                        transition={LIQUID}
                        className="absolute inset-0 rounded-xl bg-gradient-to-r from-neon-violet/30 to-neon-indigo/10 ring-1 ring-neon-violet/40"
                      />
                    )}
                    {/* Ícone sobe e acende em neon ao passar o mouse. */}
                    <motion.span
                      className="relative"
                      whileHover={{ y: -2, scale: 1.12 }}
                      transition={SPRING}
                    >
                      <Icon
                        className={cn(
                          "size-[18px] transition-[filter,color] group-hover/nav:text-neon-cyan group-hover/nav:drop-shadow-[0_0_8px_var(--neon-cyan)]",
                          active && "text-primary",
                        )}
                        aria-hidden
                      />
                    </motion.span>
                    <span className={cn("relative", active && "font-medium text-sidebar-foreground")}>{label}</span>
                  </Link>
                );
              })}
            </nav>

            <RecentConversations />

            <div className="border-t border-sidebar-border p-3">
              <DropdownMenu>
                <DropdownMenuTrigger className="flex w-full items-center gap-2.5 rounded-xl p-2 text-left transition-colors hover:bg-white/5">
                  <span className="grid size-9 shrink-0 place-items-center rounded-full bg-gradient-to-br from-neon-violet to-neon-indigo text-[12px] font-semibold text-white">
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
        </div>

        <div className="flex min-h-dvh min-w-0 flex-col pb-20 md:pb-0">
          <TopBar me={me} onSearch={() => setSearchOpen(true)} onLogout={() => logout.mutate()} />
          <main id="conteudo" className="flex min-h-0 flex-1 flex-col">
            {children}
          </main>
        </div>

        {/* Barra do celular: também uma cápsula flutuante, com a mesma gota de seleção. */}
        <nav
          aria-label="Principal"
          style={{ gridTemplateColumns: `repeat(${navigation.length}, minmax(0, 1fr))` }}
          className="glass fixed inset-x-3 bottom-3 z-40 grid h-16 rounded-2xl md:hidden"
        >
          {navigation.map(({ href, label, icon: Icon }) => {
            const active = isActive(href);
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={cn(
                  "relative flex flex-col items-center justify-center gap-1 text-[11px] text-muted-foreground",
                  active && "font-medium text-foreground",
                )}
              >
                {active && (
                  <motion.span
                    layoutId="nav-drop-mobile"
                    transition={LIQUID}
                    className="absolute inset-1.5 rounded-xl bg-neon-violet/20 ring-1 ring-neon-violet/40"
                  />
                )}
                <Icon className={cn("relative size-5", active && "text-primary")} aria-hidden />
                <span className="relative">{label}</span>
              </Link>
            );
          })}
        </nav>

        <CommandPalette open={searchOpen} onOpenChange={setSearchOpen} />
      </div>
    </MeProvider>
  );
}

/** Cabeçalho: organização numa pílula e o pulso do processamento de documentos. */
function TopBar({ me, onSearch, onLogout }: { me: Me; onSearch: () => void; onLogout: () => void }) {
  const stats = usePipelineStats();
  const working = (stats.data?.queued ?? 0) + (stats.data?.processing ?? 0);

  return (
    <header className="flex h-14 items-center gap-2 px-4 md:h-16 md:px-6">
      <span className="md:hidden">
        <Wordmark className="text-[15px]" />
      </span>
      <span className="glass hidden items-center gap-2 rounded-full px-3.5 py-1.5 text-[13px] md:inline-flex">
        <span className="size-2 rounded-full bg-gradient-to-br from-neon-violet to-neon-cyan" aria-hidden />
        {me.organization.name}
        {me.organization.is_demo && <span className="text-muted-foreground">· demonstração</span>}
      </span>

      <Link
        href="/biblioteca"
        className="glass ml-auto inline-flex items-center gap-2 rounded-full px-3.5 py-1.5 text-[13px]"
        aria-live="polite"
      >
        {/* Pulso esmeralda: fila ativa. Parado e cinza quando não há nada processando. */}
        <span className="relative flex size-2.5" aria-hidden>
          {working > 0 && (
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-neon-emerald opacity-75" />
          )}
          <span
            className={cn(
              "relative inline-flex size-2.5 rounded-full",
              working > 0 ? "bg-neon-emerald shadow-[0_0_10px_var(--neon-emerald)]" : "bg-muted-foreground/50",
            )}
          />
        </span>
        {working > 0 ? `Processando ${working}` : "Fila vazia"}
      </Link>

      <button
        type="button"
        onClick={onSearch}
        className="glass rounded-full px-3 py-1.5 text-[13px] text-muted-foreground md:hidden"
      >
        Buscar
      </button>
      <button
        type="button"
        onClick={onLogout}
        className="glass rounded-full px-3 py-1.5 text-[13px] text-muted-foreground md:hidden"
      >
        Sair
      </button>
    </header>
  );
}
