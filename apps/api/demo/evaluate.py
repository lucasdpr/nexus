"""Avalia a qualidade do RAG contra um ambiente no ar: `python -m demo.evaluate [--chat]`.

Busca (sempre): para cada pergunta com resposta nos documentos, em que posição aparece o
primeiro trecho do documento e da página esperados (acerto@1, @3, @5 e MRR); para perguntas
sem resposta nos documentos, se a busca corretamente não devolve trechos.

Resposta (--chat): faz cada pergunta ao assistente e confere se ele respondeu, se citou o
documento e a página esperados e se a resposta traz o fato esperado. Para perguntas sem
resposta, confere se ele recusou em vez de inventar.
"""

import argparse
import json
import time
import unicodedata
from pathlib import Path
from typing import Any

import httpx2

from demo.client import connect

QUESTIONS = Path(__file__).parent / "questions.json"
RATE_LIMIT_WAIT_S = 300
RATE_LIMIT_RETRIES = 14
NETWORK_RETRIES = 6


def _plain(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.casefold())
    return "".join(ch for ch in folded if not unicodedata.combining(ch))


def _matches(expected: list[dict[str, Any]], title: str | None, page: int | None) -> bool:
    return any(
        item["title"] == title and (item["page"] is None or item["page"] == page)
        for item in expected
    )


def evaluate_search(client: httpx2.Client, questions: list[dict[str, Any]]) -> dict[str, float]:
    ranks: list[int | None] = []
    clean_refusals = 0
    unanswerable = 0
    for item in questions:
        response = client.get("/api/v1/search", params={"q": item["question"], "limit": 10})
        hits = response.json()["items"] if response.status_code == 200 else []
        if not item["expect"]:
            unanswerable += 1
            clean_refusals += not hits
            print(f"  [sem resposta] {len(hits)} trecho(s)  {item['question']}")
            continue
        rank = next(
            (
                position
                for position, hit in enumerate(hits, start=1)
                if _matches(item["expect"], hit["document_title"], hit["page"])
            ),
            None,
        )
        ranks.append(rank)
        print(f"  [posição {rank or '-'}] {item['question']}")
    total = len(ranks)
    return {
        "perguntas_com_resposta": total,
        "acerto@1": sum(1 for r in ranks if r == 1) / total,
        "acerto@3": sum(1 for r in ranks if r and r <= 3) / total,
        "acerto@5": sum(1 for r in ranks if r and r <= 5) / total,
        "mrr": sum(1 / r for r in ranks if r) / total,
        "sem_resposta_sem_trechos": clean_refusals / unanswerable if unanswerable else 0.0,
    }


def _retrying(client: httpx2.Client) -> httpx2.Client:
    """Repete pedidos que falham por rede (a API pode reiniciar no meio da rodada)."""
    original = client.send

    def send(request: httpx2.Request, **kwargs: Any) -> httpx2.Response:
        for attempt in range(NETWORK_RETRIES):
            try:
                return original(request, **kwargs)
            except httpx2.TransportError:
                if attempt == NETWORK_RETRIES - 1:
                    raise
                time.sleep(20)
        raise AssertionError("inalcançável")

    client.send = send  # type: ignore[method-assign]
    return client


def ask(client: httpx2.Client, question: str) -> dict[str, Any]:
    conversation = client.post("/api/v1/chat/conversations").json()["id"]
    url = f"/api/v1/chat/conversations/{conversation}/messages"
    response = client.post(url, json={"question": question})
    # O limite por hora é por pessoa (15 na demonstração): espera a janela reabrir.
    for _ in range(RATE_LIMIT_RETRIES):
        if response.status_code != 429:
            break
        print(f"  (limite de perguntas por hora; esperando {RATE_LIMIT_WAIT_S // 60} min)")
        time.sleep(RATE_LIMIT_WAIT_S)
        response = client.post(url, json={"question": question})
    if response.status_code != 200:
        return {"error": response.text}
    event = None
    for line in response.text.splitlines():
        if line.startswith("event:"):
            event = line.removeprefix("event:").strip()
        elif line.startswith("data:") and event in {"done", "error"}:
            return {event: json.loads(line.removeprefix("data:"))}
    return {"error": "sem evento final"}


def evaluate_chat(client: httpx2.Client, questions: list[dict[str, Any]]) -> dict[str, float]:
    answerable = [q for q in questions if q["expect"]]
    unanswerable = [q for q in questions if not q["expect"]]
    cited = contained = answered = 0
    for item in answerable:
        result = ask(client, item["question"])
        message = result.get("done")
        if not message:
            print(f"  [erro] {item['question']}  {result}")
            continue
        answered += bool(message["answered"])
        citations = message["citations"]
        has_citation = any(
            _matches(item["expect"], c["document_title"], c["page"]) for c in citations
        )
        has_fact = all(
            _plain(fact) in _plain(message["content"]) for fact in item["answer_contains"]
        )
        cited += has_citation
        contained += has_fact
        print(f"  [{'ok' if has_citation and has_fact else 'FALHOU'}] {item['question']}")
    refused = 0
    for item in unanswerable:
        message = ask(client, item["question"]).get("done")
        if not message:
            print(f"  [erro] {item['question']}")
            continue
        refused += message["answered"] is False
        print(f"  [{'recusou' if message['answered'] is False else 'INVENTOU'}] {item['question']}")
    return {
        "respondeu": answered / len(answerable),
        "citou_fonte_esperada": cited / len(answerable),
        "resposta_traz_o_fato": contained / len(answerable),
        "recusou_sem_resposta": refused / len(unanswerable),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat", action="store_true", help="avalia também as respostas")
    parser.add_argument("--output", type=Path, help="grava o resultado em JSON")
    args = parser.parse_args()

    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))
    client = _retrying(connect())
    print("Busca:")
    report = {"busca": evaluate_search(client, questions)}
    if args.chat:
        print("Respostas:")
        report["resposta"] = evaluate_chat(client, questions)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.output:
        args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
