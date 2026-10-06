"use client";

import { useMutation } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useId } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, errorMessage, unwrap } from "@/lib/api/client";

export function LoginForm() {
  const router = useRouter();
  const errorId = useId();

  const login = useMutation({
    mutationFn: (credentials: { email: string; password: string }) =>
      unwrap(api.POST("/api/v1/auth/login", { body: credentials })),
    onSuccess: () => router.replace("/perguntar"),
  });
  const visit = useMutation({
    mutationFn: () => unwrap(api.POST("/api/v1/auth/demo")),
    onSuccess: () => router.replace("/perguntar"),
  });

  const error = login.error ?? visit.error;
  const busy = login.isPending || visit.isPending;

  return (
    <div className="mt-8 space-y-6">
      <form
        className="space-y-4"
        aria-describedby={error ? errorId : undefined}
        onSubmit={(event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          visit.reset();
          login.mutate({ email: String(form.get("email")), password: String(form.get("password")) });
        }}
      >
        <div className="space-y-1.5">
          <Label htmlFor="email">E-mail</Label>
          <Input id="email" name="email" type="email" autoComplete="username" required />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="password">Senha</Label>
          <Input id="password" name="password" type="password" autoComplete="current-password" required />
        </div>
        {error && (
          <p id={errorId} role="alert" className="text-[13px] text-destructive">
            {errorMessage(error)}
          </p>
        )}
        <Button type="submit" className="h-10 w-full" disabled={busy}>
          {login.isPending ? "Entrando…" : "Entrar"}
        </Button>
      </form>

      <div className="space-y-2 border-t border-border pt-6">
        <Button
          type="button"
          variant="outline"
          className="h-10 w-full"
          disabled={busy}
          onClick={() => {
            login.reset();
            visit.mutate();
          }}
        >
          {visit.isPending ? "Abrindo a demonstração…" : "Entrar como visitante"}
        </Button>
        <p className="text-[13px] leading-relaxed text-muted-foreground">
          Abre a NovaForja Industrial, uma metalúrgica fictícia com manuais, normas e contratos.
          Você pode perguntar e consultar, sem alterar nada.
        </p>
      </div>
    </div>
  );
}
