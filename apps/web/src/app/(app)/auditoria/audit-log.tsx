"use client";

import { useInfiniteQuery } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, errorMessage, unwrap } from "@/lib/api/client";
import { formatDateTime } from "@/lib/format";
import { useMe } from "@/lib/me-context";

/** Rótulos legíveis das ações registradas; ações novas aparecem pelo código até serem traduzidas. */
const ACTION_NAMES: Record<string, string> = {
  "auth.login": "Entrou no sistema",
  "auth.demo_login": "Entrou como visitante da demonstração",
  "auth.login_failed": "Tentativa de login recusada",
  "auth.logout": "Saiu do sistema",
  "auth.signup": "Criou uma conta",
  "document.uploaded": "Enviou um documento",
  "document.deleted": "Excluiu um documento",
  "document.reprocessed": "Reprocessou um documento",
  "document.downloaded": "Baixou um documento",
  "collection.created": "Criou uma coleção",
  "collection.member_added": "Adicionou um membro a uma coleção",
  "collection.member_removed": "Removeu um membro de uma coleção",
  "chat.question": "Fez uma pergunta ao assistente",
  "user.created": "Criou um usuário",
  "user.updated": "Alterou um usuário",
};

export function AuditLog() {
  const me = useMe();
  const events = useInfiniteQuery({
    queryKey: ["audit-events"],
    queryFn: ({ pageParam }) =>
      unwrap(api.GET("/api/v1/audit-events", { params: { query: { limit: 50, cursor: pageParam } } })),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => last.next_cursor ?? undefined,
    enabled: me.user.role === "ADMIN",
  });

  if (me.user.role !== "ADMIN") {
    return (
      <div className="mx-auto max-w-md px-6 py-20 text-center">
        <p className="font-medium">Só administradores veem a auditoria.</p>
      </div>
    );
  }

  const rows = events.data?.pages.flatMap((page) => page.items) ?? [];

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6">
      <h1 className="text-[22px] font-semibold">Auditoria</h1>
      <p className="mt-1 text-muted-foreground">
        Registro de quem fez o quê. Os eventos não podem ser alterados nem apagados.
      </p>

      {events.isLoading && <Skeleton className="mt-6 h-64" />}
      {events.isError && <p className="mt-6 text-destructive">{errorMessage(events.error)}</p>}
      {events.isSuccess && (
        <div className="mt-6 overflow-x-auto rounded-md border border-border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Quando</TableHead>
                <TableHead>Quem</TableHead>
                <TableHead>Ação</TableHead>
                <TableHead className="hidden sm:table-cell">Origem</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.length === 0 && (
                <TableRow>
                  <TableCell colSpan={4} className="py-10 text-center text-muted-foreground">
                    Nenhum evento registrado.
                  </TableCell>
                </TableRow>
              )}
              {rows.map((event) => (
                <TableRow key={event.id}>
                  <TableCell className="whitespace-nowrap">{formatDateTime(event.created_at)}</TableCell>
                  <TableCell>{event.actor_name ?? "Sistema"}</TableCell>
                  <TableCell>{ACTION_NAMES[event.action] ?? event.action}</TableCell>
                  <TableCell className="hidden text-muted-foreground sm:table-cell">{event.ip ?? "—"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
      {events.hasNextPage && (
        <Button variant="outline" className="mt-4" onClick={() => events.fetchNextPage()} disabled={events.isFetchingNextPage}>
          {events.isFetchingNextPage ? "Carregando…" : "Carregar mais"}
        </Button>
      )}
    </div>
  );
}
