"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FolderPlus, UserMinus, UserPlus, Users } from "lucide-react";
import { motion } from "motion/react";
import { useState } from "react";
import { toast } from "sonner";

import { GlassCard } from "@/components/fx/glass-card";
import { SPRING } from "@/components/fx/motion";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { api, errorMessage, unwrap, type Collection } from "@/lib/api/client";
import { pluralize } from "@/lib/format";
import { useMe } from "@/lib/me-context";

export function CollectionsAdmin() {
  const me = useMe();
  const collections = useQuery({
    queryKey: ["collections"],
    queryFn: () => unwrap(api.GET("/api/v1/collections")),
    enabled: me.user.role !== "MEMBER",
  });

  if (me.user.role === "MEMBER") {
    return (
      <div className="mx-auto max-w-md px-6 py-20 text-center">
        <p className="font-medium">Só gestores e administradores gerenciam coleções.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-6xl px-4 pb-10 sm:px-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-[26px] leading-tight font-semibold tracking-tight">Coleções</h1>
          <p className="mt-1 max-w-[60ch] text-muted-foreground">
            Cada coleção reúne documentos e define quem pode lê-los. As respostas do assistente só usam o que a
            pessoa que perguntou tem acesso.
          </p>
        </div>
        <CreateCollection />
      </div>

      {collections.isLoading && <Skeleton className="mt-6 h-40" />}
      {collections.isError && <p className="mt-6 text-destructive">{errorMessage(collections.error)}</p>}
      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {collections.data?.map((collection, index) => (
          <motion.div
            key={collection.id}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ ...SPRING, delay: index * 0.05 }}
          >
            <CollectionCard collection={collection} />
          </motion.div>
        ))}
      </div>
    </div>
  );
}

function CollectionCard({ collection }: { collection: Collection }) {
  const documents = useQuery({
    queryKey: ["collection-documents", collection.id],
    queryFn: () =>
      unwrap(api.GET("/api/v1/documents", { params: { query: { collection_id: collection.id, limit: 1 } } })),
  });
  const members = useQuery({
    queryKey: ["collection-members", collection.id],
    queryFn: () =>
      unwrap(api.GET("/api/v1/collections/{collection_id}/members", { params: { path: { collection_id: collection.id } } })),
  });

  return (
    <GlassCard className="flex h-full flex-col p-5">
      <h2 className="text-[16px] font-semibold">{collection.name}</h2>
      <p className="mt-1 line-clamp-3 min-h-[3.75rem] text-[13px] text-muted-foreground">
        {collection.description ?? "Sem descrição."}
      </p>
      <dl className="mt-4 flex gap-6 border-t border-white/10 pt-4 text-[13px]">
        <div>
          <dt className="text-muted-foreground">Documentos</dt>
          <dd className="text-[20px] font-semibold tabular-nums">{documents.data?.total ?? "–"}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Com acesso</dt>
          <dd className="text-[20px] font-semibold tabular-nums">{members.data?.length ?? "–"}</dd>
        </div>
      </dl>
      <div className="mt-4">
        <MembersDialog collection={collection} />
      </div>
    </GlassCard>
  );
}

function MembersDialog({ collection }: { collection: Collection }) {
  const me = useMe();
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [picked, setPicked] = useState<string>();
  const key = ["collection-members", collection.id];
  const members = useQuery({
    queryKey: key,
    queryFn: () =>
      unwrap(api.GET("/api/v1/collections/{collection_id}/members", { params: { path: { collection_id: collection.id } } })),
    enabled: open,
  });
  const users = useQuery({ queryKey: ["users"], queryFn: () => unwrap(api.GET("/api/v1/users")), enabled: open });
  const candidates = users.data?.filter(
    (user) => user.status === "ACTIVE" && !members.data?.some((member) => member.id === user.id),
  );

  const refresh = () => queryClient.invalidateQueries({ queryKey: key });
  const add = useMutation({
    mutationFn: (userId: string) =>
      api.POST("/api/v1/collections/{collection_id}/members", {
        params: { path: { collection_id: collection.id } },
        body: { user_id: userId },
      }),
    onSuccess: (result) => {
      if (result.error) return toast.error(errorMessage(result.error));
      setPicked(undefined);
      return refresh();
    },
  });
  const remove = useMutation({
    mutationFn: (userId: string) =>
      api.DELETE("/api/v1/collections/{collection_id}/members/{user_id}", {
        params: { path: { collection_id: collection.id, user_id: userId } },
      }),
    onSuccess: (result) => {
      if (result.error) return toast.error(errorMessage(result.error));
      return refresh();
    },
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="w-full">
          <Users aria-hidden />
          Quem tem acesso
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{collection.name}</DialogTitle>
          <DialogDescription>
            {pluralize(members.data?.length ?? 0, "pessoa pode", "pessoas podem")} ler os documentos desta coleção.
          </DialogDescription>
        </DialogHeader>

        <ul className="max-h-64 space-y-1 overflow-y-auto">
          {members.data?.map((member) => (
            <li key={member.id} className="flex items-center gap-3 rounded-lg px-2 py-1.5 hover:bg-white/5">
              <span className="min-w-0 flex-1">
                <span className="block truncate text-[14px]">{member.name}</span>
                <span className="block truncate text-[12px] text-muted-foreground">{member.email}</span>
              </span>
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label={`Remover ${member.name} da coleção`}
                disabled={remove.isPending || member.id === me.user.id}
                onClick={() => remove.mutate(member.id)}
              >
                <UserMinus aria-hidden />
              </Button>
            </li>
          ))}
          {members.data?.length === 0 && (
            <li className="px-2 py-3 text-[13px] text-muted-foreground">Ninguém foi adicionado ainda.</li>
          )}
        </ul>

        <DialogFooter className="items-end gap-2 sm:flex-row">
          <div className="min-w-0 flex-1 space-y-1.5">
            <Label>Adicionar pessoa</Label>
            <Select value={picked} onValueChange={setPicked}>
              <SelectTrigger className="w-full">
                <SelectValue placeholder={candidates?.length === 0 ? "Todos já têm acesso" : "Escolher"} />
              </SelectTrigger>
              <SelectContent>
                {candidates?.map((user) => (
                  <SelectItem key={user.id} value={user.id}>
                    {user.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button disabled={!picked || add.isPending} onClick={() => picked && add.mutate(picked)}>
            <UserPlus aria-hidden />
            Adicionar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function CreateCollection() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const create = useMutation({
    mutationFn: (body: { name: string; description: string | null }) =>
      unwrap(api.POST("/api/v1/collections", { body })),
    onSuccess: () => {
      toast.success("Coleção criada.");
      setOpen(false);
      return queryClient.invalidateQueries({ queryKey: ["collections"] });
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <FolderPlus aria-hidden />
          Nova coleção
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            const description = String(data.get("description")).trim();
            create.mutate({ name: String(data.get("name")), description: description || null });
          }}
        >
          <DialogHeader>
            <DialogTitle>Nova coleção</DialogTitle>
            <DialogDescription>Depois de criar, escolha quem pode ler os documentos dela.</DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5">
            <Label htmlFor="collection-name">Nome</Label>
            <Input id="collection-name" name="name" required minLength={2} maxLength={80} autoComplete="off" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="collection-description">Descrição (opcional)</Label>
            <Input id="collection-description" name="description" maxLength={500} autoComplete="off" />
          </div>
          <DialogFooter>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Criando…" : "Criar coleção"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
