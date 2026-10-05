# NEXUS

Plataforma de inteligência documental: documentos corporativos viram uma base de
conhecimento pesquisável, com respostas de IA fundamentadas em fontes verificáveis
(documento e página).

> **Em construção.** Fases 0 (fundação) e 1 (núcleo: organizações, autenticação, papéis,
> coleções e auditoria) concluídas. O plano completo, com arquitetura, modelo de dados,
> fluxo RAG e decisões técnicas, está em [docs/PLANO.md](docs/PLANO.md).

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
  api/   FastAPI: app/core (config, banco, segurança) e app/modules/<domínio>
  web/   Next.js
docs/    plano e decisões
```

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

Sobe banco, API e web; aplica as migrações e cria a organização de demonstração. Web em
http://localhost:3000, documentação da API em http://localhost:8000/api/docs.

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
imutabilidade da auditoria. O CI roda tudo isso a cada push e pull request, além do build
das imagens Docker e de um teste de fumaça (web → proxy → API → banco).
