import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { SourceCard } from "@/components/nexus/source-card";
import { Wordmark } from "@/components/nexus/wordmark";
import { getSession } from "@/lib/session";

import { LoginForm } from "./login-form";

export const metadata: Metadata = { title: "Entrar" };

export default async function SignInPage() {
  if (await getSession()) redirect("/perguntar");

  return (
    <main className="grid min-h-dvh lg:grid-cols-[minmax(0,1fr)_minmax(0,1.15fr)]">
      <section className="flex flex-col px-6 py-8 sm:px-12 lg:py-12">
        <Wordmark className="text-lg" />
        <div className="my-auto w-full max-w-sm py-12">
          <h1 className="text-[28px] leading-tight font-semibold tracking-tight text-balance">
            Pergunte aos documentos da sua empresa.
          </h1>
          <p className="mt-3 text-[15px] leading-relaxed text-muted-foreground">
            Cada resposta mostra o documento e a página de onde veio.
          </p>
          <LoginForm />
        </div>
        <p className="text-xs text-muted-foreground">
          Projeto de portfólio. A organização de demonstração usa documentos fictícios.
        </p>
      </section>

      <section
        aria-label="Exemplo de resposta"
        className="hidden flex-col justify-center gap-5 border-l border-border bg-secondary/60 px-12 py-12 lg:flex xl:px-20"
      >
        <div className="max-w-xl space-y-5">
          <p className="w-fit rounded-xl rounded-br-sm bg-card px-4 py-2.5 text-[15px] shadow-xs ring-1 ring-border">
            Qual é o prazo de garantia do compressor CX-200?
          </p>
          <p className="max-w-[60ch] text-[15px] leading-relaxed">
            O prazo é de 24 meses a partir da data de instalação, desde que as manutenções
            preventivas estejam em dia.
            <sup className="ml-0.5 rounded-sm bg-evidence px-1 text-[11px] font-semibold text-evidence-foreground">
              1
            </sup>
          </p>
          <SourceCard
            marker={1}
            documentTitle="Manual do Compressor CX-200"
            page={42}
            collection="Engenharia de Manutenção"
            version={3}
            quote="7.1 Garantia. O prazo de garantia é de 24 meses a partir da data de instalação, condicionado à execução das manutenções preventivas previstas no capítulo 5. A garantia não cobre desgaste natural de filtros e correias."
            highlight="O prazo de garantia é de 24 meses a partir da data de instalação"
          />
        </div>
      </section>
    </main>
  );
}
