import { ApiError, errorMessage, type Message, type Source } from "@/lib/api/client";

export type StreamHandlers = {
  onSources: (sources: Source[]) => void;
  onToken: (text: string) => void;
  onDone: (message: Message) => void;
  onError: (detail: string) => void;
};

/**
 * Envia a pergunta e lê a resposta em Server-Sent Events. Usa `fetch` (e não EventSource)
 * porque a pergunta vai no corpo de um POST.
 */
export async function askQuestion(
  conversationId: string,
  question: string,
  handlers: StreamHandlers,
  signal?: AbortSignal,
): Promise<void> {
  const response = await fetch(`/api/v1/chat/conversations/${conversationId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal,
  });
  if (!response.ok || !response.body) {
    const body = await response.json().catch(() => undefined);
    throw new ApiError(errorMessage(body, "Não foi possível enviar a pergunta."), response.status);
  }

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += value;
    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      dispatch(buffer.slice(0, boundary), handlers);
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf("\n\n");
    }
  }
}

function dispatch(block: string, handlers: StreamHandlers) {
  let event = "message";
  let data = "";
  for (const line of block.split("\n")) {
    if (line.startsWith("event: ")) event = line.slice(7);
    else if (line.startsWith("data: ")) data += line.slice(6);
  }
  if (!data) return;
  const payload = JSON.parse(data);
  switch (event) {
    case "sources":
      handlers.onSources(payload as Source[]);
      break;
    case "token":
      handlers.onToken((payload as { text: string }).text);
      break;
    case "done":
      handlers.onDone(payload as Message);
      break;
    case "error":
      handlers.onError((payload as { detail: string }).detail);
      break;
  }
}
