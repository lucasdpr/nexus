import type { Metadata } from "next";
import Link from "next/link";

import { PublicFooter, PublicHeader } from "@/components/nexus/public-header";
import { Button } from "@/components/ui/button";
import { EVALUATION, percent } from "@/lib/evaluation";

export const metadata: Metadata = {
  title: "Sobre o projeto",
  description: "Como o NEXUS foi construído, o que foi medido e o que ainda não funciona.",
};

const DECISIONS: { title: string; body: string }[] = [
  {
    title: "Citações verificadas depois do modelo",
    body: "O modelo recebe as fontes numeradas e responde com marcadores como [S1]. Um validador separado remove marcadores de fontes que não existem, e uma resposta sem nenhuma fonte válida é trocada por “não encontrei”. Quando nenhum trecho passa do limiar de relevância, o modelo nem é chamado.",
  },
  {
    title: "Busca híbrida com fusão por posição",
    body: "Cada pergunta roda uma busca vetorial (pgvector) e uma textual em português (ts_rank com unaccent). Os dois rankings são fundidos por Reciprocal Rank Fusion, que não exige comparar notas de escalas diferentes.",
  },
  {
    title: "Isolamento entre organizações em duas camadas",
    body: "Todo repositório filtra por organização, e o Postgres reforça com Row-Level Security: cada transação assume uma role sem privilégios e declara a organização, de modo que uma consulta esquecida não vaza dados. O acesso por coleção é aplicado dentro da própria consulta de busca.",
  },
  {
    title: "Fila de processamento no próprio Postgres",
    body: "Envios viram jobs em uma tabela, consumidos com SKIP LOCKED, repetição com espera crescente e recuperação de jobs travados. Cada etapa (extração, trechos, embeddings, indexação) grava seu estado, que a tela acompanha.",
  },
  {
    title: "Auditoria que só aceita inserção",
    body: "Eventos de login, envio, download, exclusão e pergunta vão para uma tabela sem permissão de alteração ou remoção. O limite de perguntas por hora é contado a partir dela, com trava para impedir que pedidos simultâneos o ultrapassem.",
  },
  {
    title: "Respostas que não dependem de um único provedor",
    body: "Gemini e Voyage ficam atrás de interfaces próprias. Se o Gemini estiver sobrecarregado, o sistema tenta de novo e, se continuar fora, responde de forma extrativa com a frase que cobre a pergunta, ou recusa quando nenhuma cobre.",
  },
];

const LIMITS = [
  "Os embeddings atuais são locais, por hash de palavras, e entendem pouco de sinônimos. O Voyage AI está previsto, e a avaliação deve melhorar com ele.",
  "Os arquivos enviados ficam no disco da API, que no plano gratuito é apagado a cada reinício. Falta ligar um armazenamento compatível com S3.",
  "PDFs digitalizados (só imagem) são recusados com uma mensagem clara. OCR não foi implementado.",
  "A API gratuita dorme depois de alguns minutos parada, então o primeiro acesso pode levar cerca de um minuto.",
  "A avaliação cobre poucos documentos e perguntas, escritos pelo próprio projeto. Ela mostra a direção, não é um benchmark.",
];

const STACK: [string, string][] = [
  ["Interface", "Next.js 16, React 19, TypeScript, Tailwind CSS 4, TanStack Query, react-pdf"],
  ["API", "Python 3.14, FastAPI, Pydantic, SQLAlchemy 2 assíncrono, Alembic"],
  ["Banco", "PostgreSQL 17 com pgvector e Row-Level Security (Neon)"],
  ["IA", "Gemini para respostas e Voyage AI para embeddings, atrás de interfaces próprias"],
  ["Entrega", "Docker Compose, GitHub Actions, Vercel (interface) e Render (API)"],
];

export default function AboutProjectPage() {
  return (
    <div className="flex min-h-dvh flex-col">
      <PublicHeader />

      <main id="conteudo" className="mx-auto w-full max-w-3xl flex-1 px-6 pt-8 pb-20">
        <h1 className="text-[34px] leading-tight font-semibold tracking-tight text-balance">
          Sobre o projeto
        </h1>
        <p className="mt-4 text-[17px] leading-relaxed text-muted-foreground">
          O NEXUS é um projeto de portfólio: uma plataforma de inteligência documental com várias
          organizações, papéis de acesso, auditoria e processamento em segundo plano. O foco é que
          cada resposta de IA possa ser conferida no documento original.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Button asChild>
            <Link href="/entrar">Testar a demonstração</Link>
          </Button>
          <Button asChild variant="outline">
            <a href="https://github.com/lucasdpr/nexus">Ver o código</a>
          </Button>
        </div>

        <h2 className="mt-14 text-[22px] font-semibold">Decisões que importam</h2>
        <dl className="mt-5 space-y-6">
          {DECISIONS.map(({ title, body }) => (
            <div key={title} className="border-l-2 border-primary/40 pl-4">
              <dt className="text-[16px] font-semibold">{title}</dt>
              <dd className="mt-1 text-[15px] leading-relaxed text-muted-foreground">{body}</dd>
            </div>
          ))}
        </dl>

        <h2 className="mt-14 text-[22px] font-semibold">O que foi medido</h2>
        <p className="mt-3 text-[15px] leading-relaxed text-muted-foreground">
          {EVALUATION.questions} perguntas sobre {EVALUATION.documents} documentos fictícios, rodadas
          contra o ambiente no ar: {EVALUATION.answerable} com resposta nos documentos e{" "}
          {EVALUATION.unanswerable} sem, incluindo armadilhas como perguntar pelo modelo CX-300 quando
          só existe o CX-200. A rodada é refeita com{" "}
          <code className="rounded-sm bg-muted px-1 py-0.5 text-[13px]">python -m demo.evaluate --chat</code>.
        </p>
        <table className="mt-5 w-full text-left text-[15px]">
          <caption className="sr-only">Resultado da busca e das respostas na avaliação</caption>
          <tbody className="divide-y divide-border border-y border-border">
            <tr>
              <th scope="row" className="py-2.5 font-normal">Trecho certo em 1º lugar</th>
              <td className="py-2.5 text-right font-semibold tabular-nums">{percent(EVALUATION.search.top1)}</td>
            </tr>
            <tr>
              <th scope="row" className="py-2.5 font-normal">Trecho certo entre os 5 primeiros</th>
              <td className="py-2.5 text-right font-semibold tabular-nums">{percent(EVALUATION.search.top5)}</td>
            </tr>
            <tr>
              <th scope="row" className="py-2.5 font-normal">Posição média inversa (MRR)</th>
              <td className="py-2.5 text-right font-semibold tabular-nums">
                {EVALUATION.search.mrr.toFixed(3).replace(".", ",")}
              </td>
            </tr>
            <tr>
              <th scope="row" className="py-2.5 font-normal">Respostas certas, com documento, página e fato certos</th>
              <td className="py-2.5 text-right font-semibold tabular-nums">{percent(EVALUATION.answers.correct)}</td>
            </tr>
            <tr>
              <th scope="row" className="py-2.5 font-normal">Perguntas sem resposta recusadas, sem inventar</th>
              <td className="py-2.5 text-right font-semibold tabular-nums">{percent(EVALUATION.answers.refused)}</td>
            </tr>
          </tbody>
        </table>
        <p className="mt-3 text-[14px] text-muted-foreground">Embeddings {EVALUATION.embeddings}.</p>

        <h2 className="mt-14 text-[22px] font-semibold">O que ainda não funciona</h2>
        <ul className="mt-4 list-disc space-y-2 pl-5 text-[15px] leading-relaxed text-muted-foreground marker:text-primary">
          {LIMITS.map((limit) => (
            <li key={limit}>{limit}</li>
          ))}
        </ul>

        <h2 className="mt-14 text-[22px] font-semibold">Tecnologias</h2>
        <dl className="mt-4 divide-y divide-border border-y border-border text-[15px]">
          {STACK.map(([layer, tech]) => (
            <div key={layer} className="grid gap-1 py-3 sm:grid-cols-[8rem_1fr]">
              <dt className="font-semibold">{layer}</dt>
              <dd className="text-muted-foreground">{tech}</dd>
            </div>
          ))}
        </dl>
      </main>

      <PublicFooter />
    </div>
  );
}
