"use client";

import { useQuery } from "@tanstack/react-query";
import { Paperclip } from "lucide-react";

import { Button } from "@/components/ui/button";
import { api, unwrap } from "@/lib/api/client";
import { canManageDocuments, useMe } from "@/lib/me-context";
import { UploadDialog } from "@/app/(app)/biblioteca/upload-dialog";

/**
 * Clipe do assistente: abre o envio de documentos sem sair da conversa. Só aparece para quem
 * pode enviar (gestão e administração); a API recusa os demais de qualquer forma.
 */
export function AttachDocument() {
  const me = useMe();
  const allowed = canManageDocuments(me);
  const collections = useQuery({
    queryKey: ["collections"],
    queryFn: () => unwrap(api.GET("/api/v1/collections")),
    enabled: allowed,
  });
  if (!allowed || !collections.data || collections.data.length === 0) return null;

  return (
    <UploadDialog
      collections={collections.data}
      trigger={
        <Button
          type="button"
          variant="ghost"
          size="icon"
          className="absolute bottom-2.5 left-2.5 size-9 rounded-xl text-muted-foreground hover:text-foreground"
          aria-label="Anexar documento"
          title="Anexar documento"
        >
          <Paperclip aria-hidden />
        </Button>
      }
    />
  );
}
