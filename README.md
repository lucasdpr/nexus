# NEXUS

Plataforma de inteligência documental: documentos corporativos viram uma base de
conhecimento pesquisável, com respostas de IA fundamentadas em fontes verificáveis
(documento e página).

> **Em construção.** Concluídas as fases 0 (fundação), 1 (organizações, autenticação, papéis,
> coleções e auditoria) e 2 (ingestão de documentos: upload, extração, divisão em trechos,
> embeddings e indexação, com fila de processamento). O plano completo, com arquitetura,
> modelo de dados, fluxo RAG e decisões técnicas, está em [docs/PLANO.md](docs/PLANO.md).

## Stack

| Camada | Tecnologia |
|---|---|
| Web | Next.js 16, React 19, TypeScript, Tailwind CSS 4 |
| API | Python 3.14, FastAPI, Pydantic, SQLAlchemy 2 (async), Alembic |
| Banco | PostgreSQL 17 + pgvector, Row-Level Security |
| IA | Gemini (respostas) e Voyage AI (embeddings), atrás de interfaces próprias |
| Infra | Docker Compose, GitHub Actions, Neon |

## Estrutura

```
apps/
  api/   FastAPI
         app/core        configuração, banco, segurança, limites
         app/modules     domínios: auth, users, collections, documents, audit
         app/ingestion   pipeline: detecção, extração, normalização, chunking
         app/jobs        fila no Postgres e worker
         app/ai          provedores de IA atrás de interfaces
  web/   Next.js
docs/    plano e decisões
scripts/ teste de fumaça do ambiente completo
```

## Pipeline de documentos

```
upload ─► validação (tipo pelo conteúdo, tamanho, duplicata)
       ─► fila (tabela jobs, SKIP LOCKED) ─► worker
       ─► extração (PDF por página, DOCX, TXT/MD) ─► normalização
       ─► trechos (sem atravessar páginas, com sobreposição)
       ─► embeddings ─► indexação (pgvector HNSW + texto em português)
```

Cada etapa grava o próprio estado, que a interface acompanha. Falhas definitivas (PDF
digitalizado, arquivo corrompido) encerram o documento com uma mensagem clara; falhas
temporárias (rede, provedor) são repetidas com backoff.

O navegador fala só com o Next.js; as rotas `/api/*` são repassadas à API, o que mantém
o cookie de sessão no mesmo domínio.

## Segurança multi-tenant

O isolamento entre organizações tem duas camadas:

1. **Aplicação:** toda consulta filtra por `org_id`, e a autorização por papel
   (`ADMIN`, `MANAGER`, `MEMBER`) é verificada no backend.
2. **Banco:** cada transação assume a role `nexus_app`, sem `BYPASSRLS`, e grava a
   organização corrente em `app.org_id`. Políticas de Row-Level Security garantem que nem
   uma consulta sem filtro enxergue dados de outra organização. Só três funções
   `SECURITY DEFINER` leem sem organização definida: localizar a conta no login, resolver
   o cookie de sessão e entrar na demonstração.

Outras medidas: sessão opaca em cookie `httpOnly`/`SameSite=Lax` (só o hash do token vai
ao banco), senhas com argon2id, limite de tentativas de login, verificação de `Origin`
contra CSRF e auditoria só de inserção (a aplicação não tem `UPDATE`/`DELETE` na tabela).

## Rodando localmente

### Com Docker

```bash
docker compose up --build
```

Sobe banco, API, worker e web; aplica as migrações e cria a organização de demonstração
(administrador `admin@novaforja.example.com`, senha `nexus-admin-local`, só para este ambiente
local). Web em http://localhost:3000, documentação da API em http://localhost:8000/api/docs.

### Sem Docker

API (Python 3.14+), com um PostgreSQL acessível (local ou Neon):

```bash
cd apps/api
python -m venv .venv
.venv/Scripts/activate   # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env     # ajuste DATABASE_URL
alembic upgrade head
python -m app.cli seed-demo
uvicorn app.main:app --port 8000
```

O processamento de documentos roda no worker, em outro terminal (`python -m app.worker`),
ou dentro da própria API com `RUN_WORKER_IN_API=true`. Sem `VOYAGE_API_KEY`, os embeddings
usam um provedor local determinístico, sem custo, adequado para desenvolvimento.

Web (Node 24+), em outro terminal:

```bash
cd apps/web
npm install
npm run dev
```

## Qualidade

| | API (`apps/api`) | Web (`apps/web`) |
|---|---|---|
| Lint | `ruff check .` | `npm run lint` |
| Formatação | `ruff format --check .` | — |
| Tipos | `mypy app tests` (estrito) | `npm run typecheck` |
| Testes | `pytest` | — |

Os testes de integração rodam contra um PostgreSQL real (`TEST_DATABASE_URL`) e cobrem
autenticação, papéis, isolamento entre organizações (pela API e direto no banco) e a
imutabilidade da auditoria, além do pipeline de documentos (com PDFs e DOCX reais gerados nos
testes, falhas temporárias, exclusão durante o processamento). O CI roda tudo isso a cada push
e pull request, constrói as imagens Docker e executa [scripts/smoke-test.sh](scripts/smoke-test.sh),
que envia um documento pelo web e espera o worker processá-lo.
