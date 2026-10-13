import Link from "next/link";
import { redirect } from "next/navigation";

import { PublicFooter, PublicHeader } from "@/components/nexus/public-header";
import { SourceCard } from "@/components/nexus/source-card";
import { Button } from "@/components/ui/button";
import { EVALUATION, percent } from "@/lib/evaluation";
import { getSession } from "@/lib/session";

export default async function Home() {
  if (await getSession()) redirect("/painel");

  return (
    <div className="flex min-h-dvh flex-col">
      <PublicHeader />

      <main id="conteudo" className="flex-1">
        <section className="mx-auto grid w-full max-w-6xl gap-12 px-6 pt-10 pb-20 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] lg:items-center lg:pt-16">
          <div>
            <h1 className="max-w-[16ch] text-[40px] leading-[1.05] font-semibold tracking-tight text-balance sm:text-[52px]">
              Cada resposta aponta a página de onde veio.
            </h1>
            <p className="mt-5 max-w-[48ch] text-[17px] leading-relaxed text-muted-foreground">
              O NEXUS lê os documentos da sua empresa e responde perguntas citando o documento e a
              página. Quando a informação não está lá, ele diz que não encontrou, em vez de inventar.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Button asChild size="lg">
                <Link href="/entrar">Testar com documentos fictícios</Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link href="/about-project">Como foi feito</Link>
              </Button>
            </div>
          </div>

          <figure aria-label="Exemplo de pergunta e resposta" className="space-y-4">
            <p className="w-fit rounded-xl rounded-br-sm bg-card px-4 py-2.5 text-[15px] shadow-xs ring-1 ring-border">
              Qual é o prazo de garantia do compressor CX-200?
            </p>
            <p className="max-w-[60ch] text-[16px] leading-relaxed">
              O prazo é de 24 meses a partir da data de instalação, desde que as manutenções
              preventivas estejam em dia.
              <sup className="ml-0.5 rounded-sm bg-evidence px-1 text-[11px] font-semibold text-evidence-foreground">
                1
              </sup>
            </p>
            <SourceCard
              marker={1}
              documentTitle="Manual do Compressor CX-200"
              page={4}
              collection="Engenharia de Manutenção"
              version={1}
              quote="5. Garantia. O prazo de garantia é de 24 meses a partir da data de instalação, limitado a 12.000 horas de operação. A garantia depende do cumprimento das manutenções preventivas do capítulo 4, registradas na ficha de manutenção."
              highlight="O prazo de garantia é de 24 meses a partir da data de instalação"
            />
          </figure>
        </section>

        <section className="border-y border-border bg-secondary/50">
          <div className="mx-auto grid w-full max-w-6xl gap-10 px-6 py-16 md:grid-cols-3">
            <div>
              <h2 className="text-[18px] font-semibold">A fonte é verificada, não confiada</h2>
              <p className="mt-2 text-[15px] leading-relaxed text-muted-foreground">
                O modelo propõe a resposta e as citações. Depois, o sistema confere se cada fonte
                citada existe. Fonte inventada é removida, e resposta sem fonte vira “não encontrei”.
              </p>
            </div>
            <div>
              <h2 className="text-[18px] font-semibold">Cada pessoa vê o que pode ler</h2>
              <p className="mt-2 text-[15px] leading-relaxed text-muted-foreground">
                O acesso por coleção vale dentro da própria busca, antes de o texto chegar ao modelo.
                Uma organização não enxerga a outra, e o banco reforça isso com isolamento por linha.
              </p>
            </div>
            <div>
              <h2 className="text-[18px] font-semibold">Quem fez o quê fica registrado</h2>
              <p className="mt-2 text-[15px] leading-relaxed text-muted-foreground">
                Envios, downloads, exclusões e perguntas entram em um registro que ninguém altera nem
                apaga, consultável pela administração.
              </p>
            </div>
          </div>
        </section>

        <section className="mx-auto w-full max-w-6xl px-6 py-16">
          <h2 className="max-w-[28ch] text-[28px] leading-tight font-semibold tracking-tight text-balance">
            Medido contra perguntas com resposta conhecida
          </h2>
          <p className="mt-3 max-w-[62ch] text-[15px] leading-relaxed text-muted-foreground">
            {EVALUATION.questions} perguntas sobre {EVALUATION.documents} documentos fictícios:{" "}
            {EVALUATION.answerable} com resposta nos documentos e {EVALUATION.unanswerable} sem. A
            busca usa embeddings {EVALUATION.embeddings}.
          </p>
          <dl className="mt-8 grid max-w-3xl gap-px overflow-hidden rounded-md border border-border bg-border sm:grid-cols-3">
            {[
              ["Trecho certo em 1º lugar", percent(EVALUATION.search.top1)],
              ["Trecho certo entre os 5 primeiros", percent(EVALUATION.search.top5)],
              ["Posição média inversa (MRR)", EVALUATION.search.mrr.toFixed(2).replace(".", ",")],
            ].map(([label, value]) => (
              <div key={label} className="bg-card px-4 py-4">
                <dt className="text-[13px] text-muted-foreground">{label}</dt>
                <dd className="mt-1 text-[28px] font-semibold tabular-nums">{value}</dd>
              </div>
            ))}
          </dl>
          <p className="mt-4 max-w-[62ch] text-[14px] text-muted-foreground">
            Os limites do projeto, como o que ainda não funciona, estão em{" "}
            <Link href="/about-project" className="underline underline-offset-4 hover:text-foreground">
              Sobre o projeto
            </Link>
            .
          </p>
        </section>
      </main>

      <PublicFooter />
    </div>
  );
}
