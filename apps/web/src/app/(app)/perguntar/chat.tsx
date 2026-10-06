"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUp, FileSearch, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import { AnswerText } from "@/components/nexus/answer-text";
import { SourceCard } from "@/components/nexus/source-card";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Skeleton } from "@/components/ui/skeleton";
import {
  api,
  errorMessage,
  unwrap,
  type ConversationDetail,
  type Message,
  type Source,
} from "@/lib/api/client";
import { askQuestion } from "@/lib/chat-stream";
import { pluralize } from "@/lib/format";
import { useMe } from "@/lib/me-context";
import { cn } from "@/lib/utils";

const MAX_QUESTION = 1000;

type Turn = {
  key: string;
  question: string;
  status: "streaming" | "done" | "failed";
  /** Trechos recuperados durante o streaming, antes da resposta final. */
  sources: Source[];
  text: string;
  message?: Message;
  error?: string;
};

type PanelSource = {
  marker: number;
  documentId: string;
  chunkId: string | null;
  title: string | null;
  page: number | null;
  quote: string | null;
};

const DEMO_SUGGESTIONS = [
  "Qual é o prazo de garantia do compressor CX-200?",
  "O que fazer antes de uma manutenção elétrica?",
  "Quais EPIs são obrigatórios na área de fundição?",
];

function fromHistory(detail: ConversationDetail): Turn[] {
  const turns: Turn[] = [];
  for (const message of detail.messages) {
    if (message.role === "USER") {
      turns.push({ key: message.id, question: message.content, status: "done", sources: [], text: "" });
    } else if (turns.length > 0) {
      const turn = turns[turns.length - 1];
      turn.message = message;
      turn.text = message.content;
      turn.status = message.status === "FAILED" ? "failed" : "done";
      if (message.status === "FAILED") turn.error = message.content;
    }
  }
  return turns;
}

/** Fontes a mostrar: as citadas na resposta final, ou as recuperadas enquanto ela é escrita. */
function panelSources(turn: Turn): PanelSource[] {
  if (turn.message) {
    return turn.message.citations.map((citation) => ({
      marker: citation.marker,
      documentId: citation.document_id,
      chunkId: citation.chunk_id ?? null,
      title: citation.document_title,
      page: citation.page,
      quote: citation.quote,
    }));
  }
  return turn.sources.map((source) => ({
    marker: source.marker,
    documentId: source.document_id,
    chunkId: source.chunk_id,
    title: source.document_title,
    page: source.page,
    quote: source.snippet,
  }));
}

export function Chat({ conversationId: initialId }: { conversationId?: string }) {
  const me = useMe();
  const queryClient = useQueryClient();
  const [conversationId, setConversationId] = useState(initialId);
  // Perguntas feitas nesta tela; o histórico vem da consulta, sem ser copiado para o estado.
  const [newTurns, setTurns] = useState<Turn[]>([]);
  const [selected, setSelected] = useState<{ turn: string; marker: number | null } | null>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const abort = useRef<AbortController | null>(null);
  const bottom = useRef<HTMLDivElement>(null);

  const history = useQuery({
    queryKey: ["conversation", initialId],
    queryFn: () =>
      unwrap(api.GET("/api/v1/chat/conversations/{conversation_id}", { params: { path: { conversation_id: initialId! } } })),
    enabled: Boolean(initialId),
    staleTime: Infinity,
  });
  const turns = [...(history.data ? fromHistory(history.data) : []), ...newTurns];

  useEffect(() => () => abort.current?.abort(), []);

  const streaming = turns.some((turn) => turn.status === "streaming");
  const activeTurn = turns.find((turn) => turn.key === selected?.turn) ?? turns.at(-1);
  const sources = activeTurn ? panelSources(activeTurn) : [];

  const createConversation = useMutation({
    mutationFn: () => unwrap(api.POST("/api/v1/chat/conversations")),
  });

  async function send(question: string) {
    const key = crypto.randomUUID();
    const update = (patch: Partial<Turn> | ((turn: Turn) => Partial<Turn>)) =>
      setTurns((current) =>
        current.map((turn) => (turn.key === key ? { ...turn, ...(typeof patch === "function" ? patch(turn) : patch) } : turn)),
      );
    setTurns((current) => [...current, { key, question, status: "streaming", sources: [], text: "" }]);
    setSelected({ turn: key, marker: null });
    requestAnimationFrame(() => bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" }));

    try {
      let id = conversationId;
      if (!id) {
        id = (await createConversation.mutateAsync()).id;
        setConversationId(id);
        // Atualiza a URL sem remontar a tela (a resposta continua chegando).
        window.history.replaceState(null, "", `/perguntar/${id}`);
      }
      abort.current = new AbortController();
      await askQuestion(
        id,
        question,
        {
          onSources: (found) => update({ sources: found }),
          onToken: (text) => update((turn) => ({ text: turn.text + text })),
          onDone: (message) => update({ status: "done", message, text: message.content }),
          onError: (detail) => update({ status: "failed", error: detail }),
        },
        abort.current.signal,
      );
      update((turn) => (turn.status === "streaming" ? { status: "done" } : {}));
      await queryClient.invalidateQueries({ queryKey: ["conversations"] });
    } catch (error) {
      if ((error as Error).name === "AbortError") {
        update({ status: "failed", error: "Resposta interrompida." });
      } else {
        update({ status: "failed", error: errorMessage(error) });
      }
    }
  }

  function cite(turnKey: string, marker: number) {
    setSelected({ turn: turnKey, marker });
    if (window.matchMedia("(max-width: 1023px)").matches) setSheetOpen(true);
    requestAnimationFrame(() =>
      document.getElementById(`fonte-${marker}`)?.scrollIntoView({ behavior: "smooth", block: "nearest" }),
    );
  }

  const panel = (
    <SourcesPanel sources={sources} activeMarker={selected?.marker ?? null} streaming={activeTurn?.status === "streaming"} />
  );

  if (initialId && history.isLoading) {
    return (
      <div className="mx-auto w-full max-w-3xl space-y-6 px-4 py-10 sm:px-8">
        <Skeleton className="ml-auto h-10 w-2/3" />
        <Skeleton className="h-24 w-full" />
      </div>
    );
  }
  if (initialId && history.isError) {
    return (
      <div className="mx-auto max-w-md px-6 py-20 text-center">
        <p className="font-medium">Não foi possível abrir esta conversa.</p>
        <p className="mt-1 text-muted-foreground">{errorMessage(history.error)}</p>
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100dvh-7rem)] min-h-0 md:h-dvh">
      <div className="flex min-w-0 flex-1 flex-col">
        <div className="min-h-0 flex-1 overflow-y-auto">
          {turns.length === 0 ? (
            <div className="mx-auto flex h-full w-full max-w-2xl flex-col justify-center px-4 py-10 sm:px-8">
              <h1 className="text-[26px] leading-tight font-semibold tracking-tight text-balance">
                O que você precisa encontrar?
              </h1>
              <p className="mt-2 max-w-[60ch] text-[15px] leading-relaxed text-muted-foreground">
                As respostas vêm só dos documentos das coleções que você acessa, com o documento e
                a página de onde saíram.
              </p>
              <Composer onSend={send} disabled={streaming} autoFocus className="mt-6" />
              {me.organization.is_demo && (
                <div className="mt-6">
                  <p className="text-[13px] text-muted-foreground">Perguntas para experimentar</p>
                  <ul className="mt-2 flex flex-col items-start gap-1">
                    {DEMO_SUGGESTIONS.map((suggestion) => (
                      <li key={suggestion}>
                        <button
                          type="button"
                          onClick={() => send(suggestion)}
                          className="rounded-md px-2 py-1.5 text-left text-[14px] text-primary hover:bg-accent"
                        >
                          {suggestion}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <div className="mx-auto w-full max-w-3xl space-y-10 px-4 py-8 sm:px-8">
              {turns.map((turn) => (
                <TurnView
                  key={turn.key}
                  turn={turn}
                  activeMarker={selected?.turn === turn.key ? selected.marker : null}
                  onCite={(marker) => cite(turn.key, marker)}
                  onShowSources={() => {
                    setSelected({ turn: turn.key, marker: null });
                    setSheetOpen(true);
                  }}
                  onStop={() => abort.current?.abort()}
                />
              ))}
              <div ref={bottom} />
            </div>
          )}
        </div>
        {turns.length > 0 && (
          <div className="border-t border-border bg-background/95 px-4 py-3 backdrop-blur sm:px-8">
            <Composer onSend={send} disabled={streaming} className="mx-auto max-w-3xl" />
          </div>
        )}
      </div>

      {turns.length > 0 && (
        <aside aria-label="Fontes da resposta" className="hidden w-[380px] shrink-0 overflow-y-auto border-l border-border bg-secondary/40 lg:block">
          {panel}
        </aside>
      )}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent side="bottom" className="max-h-[85dvh] overflow-y-auto lg:hidden">
          <SheetHeader>
            <SheetTitle>Fontes da resposta</SheetTitle>
          </SheetHeader>
          {panel}
        </SheetContent>
      </Sheet>
    </div>
  );
}

function TurnView({
  turn,
  activeMarker,
  onCite,
  onShowSources,
  onStop,
}: {
  turn: Turn;
  activeMarker: number | null;
  onCite: (marker: number) => void;
  onShowSources: () => void;
  onStop: () => void;
}) {
  const sources = panelSources(turn);
  const markers = new Set(sources.map((source) => source.marker));
  const notAnswered = turn.message?.answered === false;

  return (
    <article className="space-y-4">
      <p className="ml-auto w-fit max-w-[85%] rounded-xl rounded-br-sm bg-card px-4 py-2.5 text-[15px] ring-1 ring-border">
        {turn.question}
      </p>

      <div aria-live={turn.status === "streaming" ? "polite" : undefined} aria-busy={turn.status === "streaming"}>
        {turn.status === "streaming" && !turn.text && (
          <p className="flex items-center gap-2 text-muted-foreground">
            <FileSearch className="size-4 animate-pulse" aria-hidden />
            {turn.sources.length > 0
              ? `${pluralize(turn.sources.length, "trecho encontrado", "trechos encontrados")}. Escrevendo a resposta…`
              : "Procurando nos documentos…"}
          </p>
        )}

        {turn.status === "failed" ? (
          <p role="alert" className="rounded-md border border-destructive/40 px-3 py-2 text-[14px] text-destructive">
            {turn.error}
          </p>
        ) : notAnswered ? (
          <div className="rounded-md border border-dashed border-border px-4 py-3">
            <p className="text-[15px]">{turn.text}</p>
            <p className="mt-1 text-[13px] text-muted-foreground">
              Tente outras palavras, ou confira se o documento está numa coleção que você acessa.
            </p>
          </div>
        ) : (
          turn.text && <AnswerText text={turn.text} markers={markers} activeMarker={activeMarker} onCite={onCite} />
        )}
      </div>

      <div className="flex items-center gap-2">
        {turn.status === "streaming" && (
          <Button variant="ghost" size="sm" onClick={onStop}>
            <Square aria-hidden />
            Parar
          </Button>
        )}
        {sources.length > 0 && turn.status !== "failed" && !notAnswered && (
          <Button variant="ghost" size="sm" className="lg:hidden" onClick={onShowSources}>
            {pluralize(sources.length, "fonte", "fontes")}
          </Button>
        )}
      </div>
    </article>
  );
}

function documentHref(source: PanelSource): string {
  const query = new URLSearchParams();
  if (source.page) query.set("pagina", String(source.page));
  if (source.chunkId) query.set("trecho", source.chunkId);
  const search = query.toString();
  return `/documentos/${source.documentId}${search ? `?${search}` : ""}`;
}

function SourcesPanel({
  sources,
  activeMarker,
  streaming,
}: {
  sources: PanelSource[];
  activeMarker: number | null;
  streaming: boolean;
}) {
  if (sources.length === 0) {
    return (
      <p className="p-5 text-[13px] text-muted-foreground">
        {streaming ? "Procurando trechos relevantes…" : "Esta resposta não tem fontes citadas."}
      </p>
    );
  }
  return (
    <div className="space-y-3 p-4">
      <p className="px-1 text-[13px] text-muted-foreground">
        {streaming ? "Trechos consultados" : pluralize(sources.length, "fonte citada", "fontes citadas")}
      </p>
      {sources.map((source) =>
        source.title && source.quote ? (
          <div key={source.marker} id={`fonte-${source.marker}`} className="scroll-mt-4">
            <SourceCard
              marker={source.marker}
              documentTitle={source.title}
              page={source.page}
              quote={source.quote}
              href={documentHref(source)}
              className={cn(activeMarker === source.marker && "border-primary ring-2 ring-primary/30")}
            />
          </div>
        ) : (
          <p key={source.marker} id={`fonte-${source.marker}`} className="rounded-md border border-dashed border-border px-3 py-2 text-[13px] text-muted-foreground">
            Fonte {source.marker} indisponível: o documento foi excluído ou saiu das coleções que você acessa.
          </p>
        ),
      )}
    </div>
  );
}

function Composer({
  onSend,
  disabled,
  autoFocus,
  className,
}: {
  onSend: (question: string) => void;
  disabled: boolean;
  autoFocus?: boolean;
  className?: string;
}) {
  const [value, setValue] = useState("");
  const question = value.trim();
  const tooLong = value.length > MAX_QUESTION;

  function submit() {
    if (!question || disabled || tooLong) return;
    onSend(question);
    setValue("");
  }

  return (
    <form
      className={cn("relative", className)}
      onSubmit={(event) => {
        event.preventDefault();
        submit();
      }}
    >
      <label htmlFor="pergunta" className="sr-only">
        Pergunta
      </label>
      <textarea
        id="pergunta"
        value={value}
        autoFocus={autoFocus}
        rows={1}
        placeholder="Pergunte aos seus documentos"
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
            event.preventDefault();
            submit();
          }
        }}
        className="field-sizing-content max-h-48 min-h-[52px] w-full resize-none rounded-xl border border-input bg-card py-3.5 pr-14 pl-4 text-base shadow-xs outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/30 sm:text-[15px]"
      />
      <Button
        type="submit"
        size="icon"
        disabled={!question || disabled || tooLong}
        className="absolute right-2 bottom-2 size-9 rounded-lg"
        aria-label="Enviar pergunta"
      >
        <ArrowUp aria-hidden />
      </Button>
      {value.length > MAX_QUESTION * 0.8 && (
        <p className={cn("mt-1 text-right text-[12px] text-muted-foreground", tooLong && "text-destructive")}>
          {value.length}/{MAX_QUESTION}
        </p>
      )}
    </form>
  );
}
