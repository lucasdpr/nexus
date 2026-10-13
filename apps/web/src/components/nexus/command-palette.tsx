"use client";

import { useQuery } from "@tanstack/react-query";
import { FileText, FolderTree, LibraryBig, MessageSquareText, Search, ScrollText, Users } from "lucide-react";
import { useRouter } from "next/navigation";
import { useDeferredValue, useEffect, useState } from "react";

import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandShortcut,
} from "@/components/ui/command";
import { api, unwrap } from "@/lib/api/client";
import { useMe } from "@/lib/me-context";

/** Busca global (Ctrl/⌘ + K): trechos de documentos que o usuário pode ler, mais atalhos de navegação. */
export function CommandPalette({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const router = useRouter();
  const me = useMe();
  const [text, setText] = useState("");
  const query = useDeferredValue(text.trim());

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key.toLowerCase() === "k" && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        onOpenChange(!open);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onOpenChange]);

  const results = useQuery({
    queryKey: ["search", query],
    queryFn: () => unwrap(api.GET("/api/v1/search", { params: { query: { q: query, limit: 8 } } })),
    enabled: open && query.length >= 2,
    staleTime: 30_000,
  });

  const go = (href: string) => {
    onOpenChange(false);
    setText("");
    router.push(href);
  };

  const pages = [
    { href: "/perguntar", label: "Perguntar ao assistente", icon: MessageSquareText },
    { href: "/biblioteca", label: "Biblioteca de documentos", icon: LibraryBig },
    ...(me.user.role !== "MEMBER"
      ? [
          { href: "/colecoes", label: "Coleções", icon: FolderTree },
          { href: "/usuarios", label: "Usuários", icon: Users },
        ]
      : []),
    ...(me.user.role === "ADMIN" ? [{ href: "/auditoria", label: "Auditoria", icon: ScrollText }] : []),
  ];

  const visiblePages = pages.filter((page) => page.label.toLowerCase().includes(text.trim().toLowerCase()));

  return (
    <CommandDialog
      open={open}
      onOpenChange={onOpenChange}
      title="Busca"
      description="Procure trechos nos documentos ou vá a outra tela."
      className="sm:max-w-xl"
    >
      <Command shouldFilter={false}>
        <CommandInputWrapper text={text} onChange={setText} />
        <CommandList className="max-h-[60dvh]">
          {query.length >= 2 && results.isSuccess && results.data.items.length === 0 && (
            <CommandEmpty>Nenhum trecho encontrado para “{query}”.</CommandEmpty>
          )}
          {query.length >= 2 && results.isError && <CommandEmpty>A busca está indisponível agora.</CommandEmpty>}
          {results.data && results.data.items.length > 0 && (
            <CommandGroup heading="Trechos de documentos">
              {results.data.items.map((hit) => (
                <CommandItem
                  key={hit.chunk_id}
                  value={hit.chunk_id}
                  onSelect={() =>
                    go(
                      `/documentos/${hit.document_id}?trecho=${hit.chunk_id}${hit.page ? `&pagina=${hit.page}` : ""}`,
                    )
                  }
                  className="items-start gap-3 py-2"
                >
                  <FileText className="mt-0.5 size-4 shrink-0 text-muted-foreground" aria-hidden />
                  <span className="min-w-0">
                    <span className="block truncate text-[14px] font-medium">
                      {hit.document_title}
                      {hit.page ? <span className="font-normal text-muted-foreground"> · p. {hit.page}</span> : null}
                    </span>
                    <span className="document-voice line-clamp-2 text-[13px] text-muted-foreground">
                      {hit.snippet}
                    </span>
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
          )}
          {visiblePages.length > 0 && (
          <CommandGroup heading="Ir para">
            {visiblePages.map(({ href, label, icon: Icon }) => (
              <CommandItem key={href} value={`ir ${label}`} onSelect={() => go(href)}>
                <Icon aria-hidden />
                {label}
              </CommandItem>
            ))}
          </CommandGroup>
          )}
        </CommandList>
      </Command>
    </CommandDialog>
  );
}

function CommandInputWrapper({ text, onChange }: { text: string; onChange: (value: string) => void }) {
  return <CommandInput value={text} onValueChange={onChange} placeholder="Buscar nos documentos…" />;
}

/** Botão da barra lateral que abre a busca. */
export function SearchButton({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="mx-3 mb-3 flex h-9 items-center gap-2.5 rounded-md border border-input bg-card px-2.5 text-left text-[14px] text-muted-foreground hover:bg-accent"
    >
      <Search className="size-4" aria-hidden />
      <span className="flex-1">Buscar</span>
      <CommandShortcut className="text-[11px]">Ctrl K</CommandShortcut>
    </button>
  );
}
