"use client";

import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, LayoutGrid, MoreHorizontal, RotateCw, Rows3, Search, Trash2 } from "lucide-react";
import Link from "next/link";
import { useDeferredValue, useState } from "react";
import { toast } from "sonner";

import { isPending, StatusBadge } from "@/components/nexus/status-badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, errorMessage, unwrap, type DocumentSummary } from "@/lib/api/client";
import { formatBytes, formatRelative, pluralize } from "@/lib/format";
import { canManageDocuments, useMe } from "@/lib/me-context";
import { cn } from "@/lib/utils";

import { UploadDialog } from "./upload-dialog";

const ALL = "todas";
type View = "table" | "grid";

export function Library() {
  const me = useMe();
  const canManage = canManageDocuments(me);
  const [query, setQuery] = useState("");
  const [collection, setCollection] = useState(ALL);
  const [view, setView] = useState<View>("table");
  const deferredQuery = useDeferredValue(query.trim());

  const collections = useQuery({
    queryKey: ["collections"],
    queryFn: () => unwrap(api.GET("/api/v1/collections")),
  });

  const documents = useQuery({
    queryKey: ["documents", { q: deferredQuery, collection }],
    queryFn: () =>
      unwrap(
        api.GET("/api/v1/documents", {
          params: {
            query: {
              q: deferredQuery || undefined,
              collection_id: collection === ALL ? undefined : collection,
              limit: 100,
            },
          },
        }),
      ),
    placeholderData: keepPreviousData,
    // Enquanto houver documento na fila ou processando, o status se atualiza sozinho.
    refetchInterval: (current) =>
      current.state.data?.items.some((document) => isPending(document.status)) ? 2000 : false,
  });

  const items = documents.data?.items ?? [];
  const filtering = Boolean(deferredQuery) || collection !== ALL;

  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-8 sm:py-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight">Biblioteca</h1>
          <p className="mt-1 text-muted-foreground">
            {documents.data
              ? pluralize(documents.data.total, "documento disponível", "documentos disponíveis") + " para perguntas"
              : "Documentos das coleções que você acessa"}
          </p>
        </div>
        {canManage && collections.data && collections.data.length > 0 && (
          <UploadDialog collections={collections.data} />
        )}
      </header>

      <div className="mt-6 flex flex-wrap items-center gap-2">
        <div className="relative min-w-56 flex-1">
          <Search aria-hidden className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar pelo título"
            aria-label="Buscar documentos pelo título"
            className="pl-8"
          />
        </div>
        <Select value={collection} onValueChange={setCollection}>
          <SelectTrigger className="w-52" aria-label="Filtrar por coleção">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL}>Todas as coleções</SelectItem>
            {collections.data?.map((item) => (
              <SelectItem key={item.id} value={item.id}>
                {item.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <div className="hidden rounded-md border border-border p-0.5 sm:flex" role="group" aria-label="Visualização">
          {(
            [
              ["table", Rows3, "Tabela"],
              ["grid", LayoutGrid, "Grade"],
            ] as const
          ).map(([value, Icon, label]) => (
            <button
              key={value}
              type="button"
              aria-pressed={view === value}
              onClick={() => setView(value)}
              className={cn(
                "grid size-8 place-items-center rounded-sm text-muted-foreground hover:text-foreground",
                view === value && "bg-secondary text-foreground",
              )}
            >
              <Icon className="size-4" aria-hidden />
              <span className="sr-only">{label}</span>
            </button>
          ))}
        </div>
      </div>

      <section className="mt-4" aria-busy={documents.isLoading}>
        {documents.isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 6 }, (_, index) => (
              <Skeleton key={index} className="h-11 w-full" />
            ))}
          </div>
        ) : documents.isError ? (
          <Empty title="Não foi possível carregar a biblioteca." action={<Button variant="outline" onClick={() => documents.refetch()}>Tentar de novo</Button>}>
            {errorMessage(documents.error)}
          </Empty>
        ) : items.length === 0 ? (
          filtering ? (
            <Empty title="Nenhum documento com esses filtros.">Tente outro título ou todas as coleções.</Empty>
          ) : canManage ? (
            <Empty title="A biblioteca ainda está vazia.">
              Envie manuais, procedimentos ou contratos. Depois de processados, eles passam a
              responder perguntas.
            </Empty>
          ) : (
            <Empty title="Nenhum documento nas coleções que você acessa.">
              Peça a quem administra a organização para incluir você em uma coleção.
            </Empty>
          )
        ) : view === "grid" ? (
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((document) => (
              <li key={document.id}>
                <DocumentTile document={document} canManage={canManage} />
              </li>
            ))}
          </ul>
        ) : (
          <>
            <ul className="divide-y divide-border rounded-md border border-border bg-card sm:hidden">
              {items.map((document) => (
                <li key={document.id} className="flex items-center gap-3 px-3 py-3">
                  <Link href={`/documentos/${document.id}`} className="min-w-0 flex-1">
                    <span className="block truncate font-medium">{document.title}</span>
                    <span className="mt-0.5 flex items-center gap-2 text-[12px] text-muted-foreground">
                      <StatusBadge status={document.status} className="text-[12px]" />
                      {document.collection.name}
                    </span>
                  </Link>
                  <DocumentActions document={document} canManage={canManage} />
                </li>
              ))}
            </ul>
            <div className="hidden overflow-hidden rounded-md border border-border bg-card sm:block">
              <Table>
                <TableHeader>
                  <TableRow className="hover:bg-transparent">
                    <TableHead className="w-[42%] pl-4">Documento</TableHead>
                    <TableHead>Coleção</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Páginas</TableHead>
                    <TableHead className="text-right">Tamanho</TableHead>
                    <TableHead>Enviado</TableHead>
                    <TableHead className="w-10"><span className="sr-only">Ações</span></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((document) => (
                    <TableRow key={document.id}>
                      <TableCell className="max-w-0 pl-4">
                        <Link href={`/documentos/${document.id}`} className="block truncate font-medium hover:underline">
                          {document.title}
                        </Link>
                        <span className="block truncate text-[12px] text-muted-foreground">
                          {document.kind} {document.filename !== `${document.title}.${document.kind.toLowerCase()}` && `– ${document.filename}`}
                        </span>
                      </TableCell>
                      <TableCell className="text-muted-foreground">{document.collection.name}</TableCell>
                      <TableCell>
                        <StatusBadge status={document.status} />
                      </TableCell>
                      <TableCell className="text-right">{document.page_count ?? "–"}</TableCell>
                      <TableCell className="text-right">{formatBytes(document.size_bytes)}</TableCell>
                      <TableCell className="text-muted-foreground">{formatRelative(document.created_at)}</TableCell>
                      <TableCell className="pr-2">
                        <DocumentActions document={document} canManage={canManage} />
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </>
        )}
      </section>
    </div>
  );
}

function DocumentTile({ document, canManage }: { document: DocumentSummary; canManage: boolean }) {
  return (
    <article className="relative flex h-full flex-col rounded-md border border-border bg-card p-4 transition-colors hover:border-primary/50">
      <div className="flex items-start justify-between gap-2">
        <span className="rounded-sm bg-secondary px-1.5 py-0.5 text-[11px] font-semibold text-secondary-foreground">{document.kind}</span>
        <div className="relative z-10">
          <DocumentActions document={document} canManage={canManage} />
        </div>
      </div>
      <Link href={`/documentos/${document.id}`} className="mt-3 line-clamp-2 font-medium after:absolute after:inset-0">
        {document.title}
      </Link>
      <p className="mt-1 text-[13px] text-muted-foreground">{document.collection.name}</p>
      <div className="mt-auto flex items-center justify-between pt-4 text-[13px] text-muted-foreground">
        <StatusBadge status={document.status} />
        <span>{document.page_count ? pluralize(document.page_count, "página", "páginas") : formatBytes(document.size_bytes)}</span>
      </div>
    </article>
  );
}

function DocumentActions({ document, canManage }: { document: DocumentSummary; canManage: boolean }) {
  const queryClient = useQueryClient();
  const [confirming, setConfirming] = useState(false);
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["documents"] });

  const reprocess = useMutation({
    mutationFn: () => unwrap(api.POST("/api/v1/documents/{document_id}/reprocess", { params: { path: { document_id: document.id } } })),
    onSuccess: () => {
      toast.success("Documento na fila para reprocessar.");
      return refresh();
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
  const remove = useMutation({
    mutationFn: () => unwrap(api.DELETE("/api/v1/documents/{document_id}", { params: { path: { document_id: document.id } } })),
    onSuccess: () => {
      toast.success(`"${document.title}" foi excluído.`);
      return refresh();
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" size="icon" className="size-8" aria-label={`Ações de ${document.title}`}>
            <MoreHorizontal aria-hidden />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem asChild>
            <a href={`/api/v1/documents/${document.id}/file`} download>
              <Download aria-hidden />
              Baixar
            </a>
          </DropdownMenuItem>
          {canManage && (
            <>
              <DropdownMenuItem
                disabled={isPending(document.status) || reprocess.isPending}
                onSelect={() => reprocess.mutate()}
              >
                <RotateCw aria-hidden />
                Reprocessar
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem variant="destructive" onSelect={() => setConfirming(true)}>
                <Trash2 aria-hidden />
                Excluir
              </DropdownMenuItem>
            </>
          )}
        </DropdownMenuContent>
      </DropdownMenu>

      <AlertDialog open={confirming} onOpenChange={setConfirming}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Excluir “{document.title}”?</AlertDialogTitle>
            <AlertDialogDescription>
              O arquivo e os trechos indexados são apagados, e o documento deixa de aparecer nas
              respostas. O registro da exclusão continua na auditoria.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={() => remove.mutate()}>
              Excluir documento
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}

function Empty({ title, children, action }: { title: string; children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <div className="rounded-md border border-dashed border-border px-6 py-14 text-center">
      <p className="font-medium">{title}</p>
      <p className="mx-auto mt-1 max-w-md text-muted-foreground">{children}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
