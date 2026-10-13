"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { UserPlus } from "lucide-react";
import { useState } from "react";
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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api, errorMessage, unwrap, type Me } from "@/lib/api/client";
import { formatRelative } from "@/lib/format";
import { useMe } from "@/lib/me-context";

type Role = Me["user"]["role"];

const ROLE_NAMES: Record<Role, string> = { ADMIN: "Administração", MANAGER: "Gestão", MEMBER: "Consulta" };
const ROLES = Object.keys(ROLE_NAMES) as Role[];

export function UsersAdmin() {
  const me = useMe();
  const isAdmin = me.user.role === "ADMIN";
  const queryClient = useQueryClient();
  const users = useQuery({
    queryKey: ["users"],
    queryFn: () => unwrap(api.GET("/api/v1/users")),
    enabled: me.user.role !== "MEMBER",
  });
  const update = useMutation({
    mutationFn: (input: { id: string; role?: Role; status?: "ACTIVE" | "DISABLED" }) =>
      unwrap(
        api.PATCH("/api/v1/users/{user_id}", {
          params: { path: { user_id: input.id } },
          body: { role: input.role, status: input.status },
        }),
      ),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
    onError: (error) => toast.error(errorMessage(error)),
  });

  if (me.user.role === "MEMBER") {
    return (
      <div className="mx-auto max-w-md px-6 py-20 text-center">
        <p className="font-medium">Só gestores e administradores veem os usuários.</p>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-6 sm:px-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold">Usuários</h1>
          <p className="mt-1 text-muted-foreground">Quem tem acesso à {me.organization.name}.</p>
        </div>
        {isAdmin && <CreateUser />}
      </div>

      {users.isLoading && <Skeleton className="mt-6 h-48" />}
      {users.isError && <p className="mt-6 text-destructive">{errorMessage(users.error)}</p>}
      {users.data && (
        <div className="mt-6 overflow-x-auto rounded-md border border-border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nome</TableHead>
                <TableHead>Papel</TableHead>
                <TableHead className="hidden sm:table-cell">Último acesso</TableHead>
                <TableHead>Situação</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {users.data.map((user) => {
                const editable = isAdmin && user.id !== me.user.id;
                return (
                  <TableRow key={user.id}>
                    <TableCell>
                      <span className="block font-medium">{user.name}</span>
                      <span className="block text-[13px] text-muted-foreground">{user.email}</span>
                    </TableCell>
                    <TableCell>
                      {editable ? (
                        <Select
                          value={user.role}
                          onValueChange={(role) => update.mutate({ id: user.id, role: role as Role })}
                        >
                          <SelectTrigger className="w-40" aria-label={`Papel de ${user.name}`}>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {ROLES.map((role) => (
                              <SelectItem key={role} value={role}>
                                {ROLE_NAMES[role]}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      ) : (
                        ROLE_NAMES[user.role]
                      )}
                    </TableCell>
                    <TableCell className="hidden text-muted-foreground sm:table-cell">
                      {user.last_login_at ? formatRelative(user.last_login_at) : "Nunca entrou"}
                    </TableCell>
                    <TableCell>
                      {editable ? (
                        <Button
                          variant="outline"
                          size="sm"
                          disabled={update.isPending}
                          onClick={() =>
                            update.mutate({ id: user.id, status: user.status === "ACTIVE" ? "DISABLED" : "ACTIVE" })
                          }
                        >
                          {user.status === "ACTIVE" ? "Desativar" : "Reativar"}
                        </Button>
                      ) : (
                        <span className="text-muted-foreground">{user.status === "ACTIVE" ? "Ativo" : "Desativado"}</span>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}

function CreateUser() {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [role, setRole] = useState<Role>("MEMBER");
  const create = useMutation({
    mutationFn: (body: { name: string; email: string; password: string; role: Role }) =>
      unwrap(api.POST("/api/v1/users", { body })),
    onSuccess: () => {
      toast.success("Usuário criado.");
      setOpen(false);
      queryClient.invalidateQueries({ queryKey: ["users"] });
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <UserPlus aria-hidden />
          Novo usuário
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            create.mutate({
              name: String(data.get("name")),
              email: String(data.get("email")),
              password: String(data.get("password")),
              role,
            });
          }}
        >
          <DialogHeader>
            <DialogTitle>Novo usuário</DialogTitle>
            <DialogDescription>A pessoa entra com este e-mail e a senha inicial que você definir.</DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5">
            <Label htmlFor="user-name">Nome</Label>
            <Input id="user-name" name="name" required minLength={2} autoComplete="off" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="user-email">E-mail</Label>
            <Input id="user-email" name="email" type="email" required autoComplete="off" />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="user-password">Senha inicial (mínimo 10 caracteres)</Label>
            <Input
              id="user-password"
              name="password"
              type="password"
              required
              minLength={10}
              autoComplete="new-password"
            />
          </div>
          <div className="space-y-1.5">
            <Label>Papel</Label>
            <Select value={role} onValueChange={(value) => setRole(value as Role)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {ROLES.map((value) => (
                  <SelectItem key={value} value={value}>
                    {ROLE_NAMES[value]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <DialogFooter>
            <Button type="submit" disabled={create.isPending}>
              {create.isPending ? "Criando…" : "Criar usuário"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
