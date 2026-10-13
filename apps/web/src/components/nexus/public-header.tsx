import Link from "next/link";

import { Wordmark } from "@/components/nexus/wordmark";
import { Button } from "@/components/ui/button";

/** Cabeçalho das páginas públicas (landing e sobre o projeto). */
export function PublicHeader() {
  return (
    <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-6 py-5">
      <Link href="/" aria-label="NEXUS, página inicial">
        <Wordmark className="text-base" />
      </Link>
      <nav aria-label="Principal" className="flex items-center gap-1 sm:gap-3">
        <Link
          href="/about-project"
          className="rounded-md px-2 py-1.5 text-[14px] text-muted-foreground hover:text-foreground"
        >
          Sobre o projeto
        </Link>
        <Button asChild size="sm">
          <Link href="/entrar">Entrar</Link>
        </Button>
      </nav>
    </header>
  );
}

export function PublicFooter() {
  return (
    <footer className="mx-auto w-full max-w-6xl border-t border-border px-6 py-8 text-[13px] text-muted-foreground">
      <p>
        Projeto de portfólio. A organização de demonstração usa documentos fictícios, e nada enviado
        a ela deve ser confidencial.
      </p>
      <p className="mt-2">
        <a
          href="https://github.com/lucasdpr/nexus"
          className="underline underline-offset-4 hover:text-foreground"
        >
          Código no GitHub
        </a>
      </p>
    </footer>
  );
}
