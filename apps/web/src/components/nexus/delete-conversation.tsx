"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { api, errorMessage } from "@/lib/api/client";
import { cn } from "@/lib/utils";

type Props = {
  conversationId: string;
  title?: string | null;
  /** Para onde ir depois de excluir. Sem valor, fica na tela atual. */
  redirectTo?: string;
  /** "icon" para listas; "text" para o cabeçalho da conversa. */
  variant?: "icon" | "text";
  className?: string;
};

/** Exclui uma conversa (e as citações dela) depois de uma confirmação. */
export function DeleteConversation({ conversationId, title, redirectTo, variant = "icon", className }: Props) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const remove = useMutation({
    mutationFn: async () => {
      const result = await api.DELETE("/api/v1/chat/conversations/{conversation_id}", {
        params: { path: { conversation_id: conversationId } },
      });
      if (result.error) throw new Error(errorMessage(result.error));
    },
    onSuccess: async () => {
      setOpen(false);
      toast.success("Conversa excluída.");
      await queryClient.invalidateQueries({ queryKey: ["conversations"] });
      queryClient.removeQueries({ queryKey: ["conversation", conversationId] });
      if (redirectTo) router.replace(redirectTo);
    },
    onError: (error) => toast.error(error instanceof Error ? error.message : "Não foi possível excluir."),
  });

  return (
    <AlertDialog open={open} onOpenChange={setOpen}>
      <AlertDialogTrigger asChild>
        {variant === "icon" ? (
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label={`Excluir a conversa${title ? ` “${title}”` : ""}`}
            className={cn("text-muted-foreground hover:text-destructive", className)}
          >
            <Trash2 aria-hidden />
          </Button>
        ) : (
          <Button variant="ghost" size="sm" className={cn("text-muted-foreground hover:text-destructive", className)}>
            <Trash2 aria-hidden />
            Excluir conversa
          </Button>
        )}
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Excluir esta conversa?</AlertDialogTitle>
          <AlertDialogDescription>
            {title ? `“${title}” ` : "A conversa "}
            e as respostas dela serão apagadas. Isso não pode ser desfeito. Os documentos não são afetados.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancelar</AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            disabled={remove.isPending}
            onClick={(event) => {
              event.preventDefault();
              remove.mutate();
            }}
          >
            {remove.isPending ? "Excluindo…" : "Excluir"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
