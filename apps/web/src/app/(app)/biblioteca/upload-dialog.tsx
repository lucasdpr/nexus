"use client";

import { useQueryClient } from "@tanstack/react-query";
import { FileUp } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { errorMessage, type Collection } from "@/lib/api/client";
import { formatBytes } from "@/lib/format";
import { uploadDocument } from "@/lib/upload";
import { cn } from "@/lib/utils";

const ACCEPT = ".pdf,.docx,.txt,.md";
const MAX_BYTES = 25 * 1024 * 1024;

type Item = { file: File; progress: number; error?: string; done?: boolean };

export function UploadDialog({ collections }: { collections: Collection[] }) {
  const queryClient = useQueryClient();
  const input = useRef<HTMLInputElement>(null);
  const [open, setOpen] = useState(false);
  const [collectionId, setCollectionId] = useState<string>(collections[0]?.id ?? "");
  const [items, setItems] = useState<Item[]>([]);
  const [dragging, setDragging] = useState(false);
  const sending = items.some((item) => !item.done && !item.error && item.progress > 0);

  function addFiles(files: FileList | null) {
    if (!files) return;
    const added = Array.from(files).map((file) => ({
      file,
      progress: 0,
      error: file.size > MAX_BYTES ? "Passa do limite de 25 MB." : undefined,
    }));
    setItems((current) => [...current.filter((item) => !item.done), ...added]);
  }

  async function send() {
    const update = (file: File, patch: Partial<Item>) =>
      setItems((current) => current.map((item) => (item.file === file ? { ...item, ...patch } : item)));

    let sent = 0;
    for (const item of items.filter((candidate) => !candidate.error && !candidate.done)) {
      try {
        update(item.file, { progress: 0.01 });
        await uploadDocument(item.file, collectionId, (progress) => update(item.file, { progress }));
        update(item.file, { done: true, progress: 1 });
        sent += 1;
      } catch (error) {
        update(item.file, { error: errorMessage(error) });
      }
    }
    if (sent > 0) {
      await queryClient.invalidateQueries({ queryKey: ["documents"] });
      toast.success(sent === 1 ? "Documento enviado. O processamento começou." : `${sent} documentos enviados. O processamento começou.`);
    }
  }

  const pending = items.filter((item) => !item.error && !item.done);

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        if (!next) setItems([]);
      }}
    >
      <DialogTrigger asChild>
        <Button>
          <FileUp aria-hidden />
          Enviar documentos
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Enviar documentos</DialogTitle>
          <DialogDescription>
            PDF, DOCX, TXT ou MD, até 25 MB cada. Depois do envio, o texto é extraído e indexado
            para as perguntas.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-1.5">
          <Label htmlFor="upload-collection">Coleção</Label>
          <Select value={collectionId} onValueChange={setCollectionId}>
            <SelectTrigger id="upload-collection" className="w-full">
              <SelectValue placeholder="Escolha a coleção" />
            </SelectTrigger>
            <SelectContent>
              {collections.map((collection) => (
                <SelectItem key={collection.id} value={collection.id}>
                  {collection.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-[12px] text-muted-foreground">Só quem integra a coleção pode consultar os arquivos.</p>
        </div>

        <button
          type="button"
          onClick={() => input.current?.click()}
          onDragOver={(event) => {
            event.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault();
            setDragging(false);
            addFiles(event.dataTransfer.files);
          }}
          className={cn(
            "grid min-h-32 place-items-center rounded-lg border border-dashed border-input px-6 py-8 text-center text-[14px] text-muted-foreground transition-colors hover:border-primary hover:text-foreground",
            dragging && "border-primary bg-accent text-foreground",
          )}
        >
          <span>
            Arraste os arquivos para cá ou <span className="font-medium text-primary underline-offset-4 hover:underline">escolha no computador</span>
          </span>
        </button>
        <input ref={input} type="file" accept={ACCEPT} multiple hidden onChange={(event) => addFiles(event.target.files)} />

        {items.length > 0 && (
          <ul className="max-h-56 space-y-2 overflow-y-auto" aria-live="polite">
            {items.map((item) => (
              <li key={`${item.file.name}-${item.file.size}`} className="rounded-md border border-border px-3 py-2">
                <div className="flex items-baseline justify-between gap-3 text-[13px]">
                  <span className="truncate font-medium">{item.file.name}</span>
                  <span className="shrink-0 text-muted-foreground">
                    {item.error ? "" : item.done ? "Enviado" : formatBytes(item.file.size)}
                  </span>
                </div>
                {item.error ? (
                  <p className="mt-1 text-[12px] text-destructive">{item.error}</p>
                ) : (
                  <div className="mt-2 h-1 overflow-hidden rounded-full bg-muted" role="progressbar" aria-label={`Envio de ${item.file.name}`} aria-valuenow={Math.round(item.progress * 100)} aria-valuemin={0} aria-valuemax={100}>
                    <div className="h-full bg-primary transition-[width]" style={{ width: `${item.progress * 100}%` }} />
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>
            {items.some((item) => item.done) ? "Fechar" : "Cancelar"}
          </Button>
          <Button onClick={send} disabled={pending.length === 0 || !collectionId || sending}>
            {sending ? "Enviando…" : pending.length > 1 ? `Enviar ${pending.length} arquivos` : "Enviar"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
