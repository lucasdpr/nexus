# NEXUS — Plano de implementação

Plataforma de inteligência documental: documentos corporativos viram uma base de
conhecimento pesquisável, com respostas de IA fundamentadas em fontes verificáveis.

## Decisões tomadas

| Tema | Decisão | Motivo |
|---|---|---|
| Escopo | MVP vertical primeiro | Upload → processamento → pergunta → resposta com fonte → PDF destacado, publicado cedo. O resto entra em fases. |
| Custo | Zero | Todos os serviços em plano gratuito. |
| Geração de respostas | Gemini Flash (API Google, cota gratuita), modelo configurável por variável de ambiente | Gratuito. Groq descartado: 8K tokens/min no plano gratuito não comporta o contexto do RAG. |
| Embeddings | Voyage AI (`voyage-4`, 200M tokens grátis por conta) | Gratuito na escala da demo. Se os limites de taxa sem cartão forem baixos demais, troca para `gemini-embedding-2` pela mesma interface. |
| Citações | Trechos numerados `[S1]…[Sn]`; o backend aceita só fontes que estão entre os trechos recuperados | Sem citações nativas no provedor gratuito; a garantia de "nunca inventar fonte" fica no backend. |
| Banco | PostgreSQL + pgvector no Neon (dev e produção) | Nada instalado localmente. |
| Docker | `Dockerfile` e `docker-compose.yml` no repositório; executados pelo GitHub Actions | O PC de desenvolvimento não precisa de Docker. |
| Fila de jobs | Tabela `jobs` no Postgres (`FOR UPDATE SKIP LOCKED`) + processo worker | Sem Redis/Celery: uma peça de infraestrutura a menos. |
| Orquestração de IA | Camada própria e fina (`EmbeddingProvider`, `AnswerProvider`), sem LangChain/LlamaIndex | Mais clara, testável e troca de provedor por configuração. |
| Autenticação | Sessão opaca em cookie `httpOnly`, revogável, guardada no banco; Next.js repassa `/api/*` ao FastAPI | Evita token em localStorage (XSS) e mantém o cookie no mesmo domínio. |
| Multi-tenancy | `org_id` em todas as tabelas, escopo no repositório + Row-Level Security no Postgres | Isolamento no backend e no banco. |
| Permissão no RAG | Filtro de organização e coleção dentro da query de busca, nunca depois | Impede a IA de vazar conteúdo que o usuário não pode ver. |
| Unidade de permissão | Coleções (ex.: Engenharia, Jurídico) | Substitui o "setor" que aparecia só nos filtros. |
| Formatos no MVP | PDF, DOCX, TXT, MD | OCR e XLSX ficam para depois. Sem importação por URL (elimina SSRF). |
| Demo pública | "Entrar como visitante": organização de demonstração, somente leitura, com limite de uso | Quem avalia o portfólio não cria conta. |
| Dados de demo | Documentos fictícios de uma empresa + normas públicas reais (NRs) | Volume e credibilidade. Nada confidencial passa pela cota gratuita. |
| Ambiente | PC da empresa: nenhuma instalação no sistema; dependências só dentro da pasta do projeto (`node_modules`, `.venv`) | Restrição do ambiente. |
| Ferramentas | npm (web) e pip + venv (API), em vez de pnpm e uv | Já existem nos dois PCs; nenhum ganho justifica mais uma ferramenta. |
| Versões | Node 24, Next.js 16, Python 3.14 (mínimo 3.13) | Versões disponíveis no ambiente de desenvolvimento. |

### Decisões da implementação (Fase 1)

- **Role da aplicação:** cada transação faz `set_config('role', 'nexus_app', true)` junto com
  o contexto de organização, numa única ida ao banco. Funciona com pooler (escopo de
  transação) e a mesma string de conexão serve para migrações e aplicação.
- **Leituras sem organização:** só três funções `SECURITY DEFINER` (login, resolução de
  sessão, entrada na demo), com `search_path` fixo e colunas mínimas.
- **IDs:** UUIDv7 gerados no Python (ordenados no tempo, bons para índices).
- **Conexão resiliente:** até 3 tentativas com timeout de 15 s, para quedas de rede e para o
  Neon acordando da hibernação.
- **E-mail único no sistema todo:** o login não pergunta a organização.
- **Neon:** projeto `NEXUS` (us-east-1) com branches `production`, `dev` e `test`.

### Pontos de atenção do plano gratuito

- No plano gratuito do Gemini, a Google usa os dados para melhorar os produtos. A demo só
  processa documentos fictícios e públicos, e o visitante não envia arquivos. Isso fica
  documentado no `/about-project`.
- A cota diária do Gemini pode esgotar. Mitigação: cache de respostas, perguntas sugeridas,
  limite por visitante e mensagem clara quando a cota acabar.
- Os limites dos planos gratuitos de Neon, Vercel e Render serão conferidos na fase de deploy.

## Arquitetura

```
Navegador ─► Next.js (web) ── rewrite /api/* ──► FastAPI (api)
                                                  routers → services → repositories
                                                  ├─► PostgreSQL: dados + pgvector + busca textual + fila de jobs
                                                  ├─► Storage: disco local (dev) | S3-compatível (prod)
                                                  └─► Provedores de IA (interfaces)
                         worker (mesmo código, outro processo) ◄── fila no Postgres
```

## Estrutura de pastas

```
nexus/
├─ apps/web/                  Next.js (App Router), shadcn/ui, TanStack Query
│  └─ src/{app,components/{ui,nexus},features/*,lib}
├─ apps/api/
│  ├─ app/
│  │  ├─ core/                config, db, logging, segurança
│  │  ├─ modules/             auth, users, collections, documents, search, chat, audit, dashboard
│  │  │   └─ <módulo>/{router,service,repository,models,schemas}.py
│  │  ├─ ingestion/           extratores, normalização, chunking, pipeline
│  │  ├─ retrieval/           busca híbrida, fusão, montagem de contexto
│  │  ├─ ai/                  interfaces + gemini, voyage, fake (testes)
│  │  ├─ jobs/                fila + worker
│  │  └─ storage/             local, s3
│  ├─ migrations/ (Alembic)   tests/   evals/
├─ e2e/ (Playwright)   docs/adr/   docker-compose.yml   .github/workflows/
```

## Modelo de dados

```
organizations       id, name, slug
users               id, org_id, name, email, password_hash (argon2id), avatar_url, role, status, created_at
sessions            id, user_id, token_hash, ip, user_agent, expires_at, revoked_at
collections         id, org_id, name
collection_members  collection_id, user_id
documents           id, org_id, collection_id, uploaded_by, title, mime_type, size_bytes, sha256,
                    storage_key, status, error, page_count, version, metadata jsonb,
                    uploaded_at, processed_at, deleted_at
tags / document_tags
processing_steps    document_id, step, status, started_at, finished_at, error
chunks              id, org_id, collection_id, document_id, ordinal, page, content,
                    tsv (coluna gerada), embedding vector(n), embedding_model, token_count
jobs                id, kind, payload, status, attempts, run_after, locked_at, last_error
conversations       id, org_id, user_id, title
messages            id, conversation_id, role, content, answered, latency_ms, model, tokens_in, tokens_out
citations           message_id, chunk_id, document_id, page, cited_text, rank
audit_events        id, org_id, actor_id, action, resource_type, resource_id, ip, metadata, created_at
```

- Índices: HNSW em `chunks.embedding`, GIN em `chunks.tsv`, `(org_id, collection_id)` em `chunks`.
- `documents`: chave única `(org_id, sha256)` para documentos não excluídos.
- `audit_events`: só inserção; a role da aplicação não tem `UPDATE` nem `DELETE`.

## Fluxo RAG

Todos os parâmetros são configuráveis e ajustados pelo conjunto de avaliação.

1. **Chunking:** segue parágrafos e seções, ~500 tokens, sobreposição de ~15%. Um trecho
   nunca atravessa página, para que a citação aponte a página exata.
2. **Busca:** vetorial (top 40) + textual em português (`tsvector` + `unaccent`, top 40),
   ambas já filtradas por organização, coleções permitidas, status `READY` e filtros da tela.
3. **Ranking:** Reciprocal Rank Fusion (k = 60), ficando com os 8 melhores. Reranker só
   entra se a avaliação mostrar ganho.
4. **Limiar:** se nada passar do limiar, responde "Não encontrei informação suficiente nos
   documentos disponíveis para responder com segurança." sem chamar a IA, e registra a
   pergunta como sem resposta.
5. **Geração:** trechos numerados `[S1]…[Sn]` com documento e página; instrução para
   responder só com base neles e citar cada afirmação.
6. **Validação:** citações fora do conjunto recuperado são descartadas; resposta sem
   nenhuma citação válida é marcada como sem resposta.
7. **Interface:** resposta em streaming (SSE); clicar na fonte abre o PDF na página com o
   trecho destacado.

**Avaliação:** conjunto de perguntas com respostas e páginas conhecidas, medindo acerto de
recuperação, acerto de citação e taxa de "não sei" correto. Resultados publicados no
`/about-project`.

## Segurança

| Risco | Mitigação |
|---|---|
| IDOR / vazamento entre organizações | Escopo por `org_id` no repositório + RLS. Recurso de outra organização responde 404. |
| Vazamento pela IA | Permissão aplicada dentro da busca. |
| Prompt injection vinda de documentos | Trechos tratados como dados; o modelo não tem ferramentas com efeito e só vê o que o usuário já pode ver. |
| Upload malicioso ou gigante | Tipo validado pela assinatura do arquivo, limites de tamanho e páginas, checagem de zip bomb no DOCX, nome de arquivo UUID, download com `Content-Disposition: attachment` + `nosniff`. |
| XSS | Markdown da IA renderizado sem HTML bruto; PDF exibido pelo PDF.js. |
| CSRF | Cookie `SameSite=Lax` + verificação de `Origin` em métodos que alteram dados. |
| Senha e sessão | argon2id, sessão revogável, limite de tentativas no login. |
| Custo e abuso de IA | Limite por usuário e por IP, tamanho máximo de pergunta, teto diário na demo. |
| Segredos | `.env` fora do Git, `.env.example` no repositório, `SecretStr`, logs sem conteúdo de documento nem texto de pergunta. |

## Design system

- **Tipografia:** IBM Plex Sans (interface), IBM Plex Mono (IDs, páginas, metadados),
  Source Serif 4 (trechos citados dos documentos).
- **Cores:** neutros frios + um acento (verde-petróleo). Amarelo marca-texto como cor de
  evidência, usado só em citações e destaques. Cores de status só nos badges.
- **Medidas:** espaçamento base 4px; raio 4px (badges), 6px (controles), 10px (diálogos);
  bordas de 1px como separador principal; sombras só em camadas flutuantes.
- **Texto:** 14px na interface, 16px em leitura.
- **Movimento:** 120–200ms, respeitando `prefers-reduced-motion`.
- **Temas:** claro e escuro com tokens semânticos.
- **Componentes:** Button, Input, Select, Dialog, Dropdown, Tooltip, Badge, Card, Table,
  Tabs, Sidebar, Command Palette, Toast, Skeleton, Empty State, Error State, File Upload,
  Document Card, Source Citation, AI Message, AnswerBlock, PipelineStatus, DocumentViewer.

## Telas

- **Públicas:** landing curta, `/about-project`, login com "Entrar como visitante".
- **App:** início (pergunta como elemento central), assistente (conversas + painel de
  fontes), biblioteca (tabela/grade, upload por arrastar, filtros), documento
  (visualizador com destaque, metadados, status do pipeline, histórico), busca global
  (⌘K + página de resultados), dashboard (perguntas sem resposta, documentos mais
  consultados), auditoria, usuários e coleções.
- **Celular:** assistente como tela principal, navegação em barra inferior, tabela vira
  lista, visualizador em tela cheia com fontes num painel deslizante.

## Testes

- **Unitários:** chunking, fusão de ranking, validação de citações, política de permissões.
- **Integração (Postgres real):** autenticação, permissões, isolamento entre organizações
  (um teste por endpoint), upload, pipeline, busca.
- **Front:** componentes críticos e fluxos principais.
- **E2E (Playwright):** criar usuário → login → upload → aguardar processamento → pergunta
  → resposta → fonte → abrir documento, com provedor de IA falso.
- **Avaliação com modelo real:** script separado, executado manualmente.
- **CI:** lint, checagem de tipos, testes e build, sem chamadas a provedores de IA.

## Fases

| Fase | Entrega |
|---|---|
| 0 · Fundação ✅ | Repositório, estrutura, Docker Compose, CI, configuração, health check, proxy web → API. |
| 1 · Núcleo ✅ | Organizações, usuários, sessões, papéis, coleções, RLS, auditoria, dados de demonstração. |
| 2 · Ingestão | Upload, validação, storage, fila e worker, extração PDF/DOCX/TXT, chunking, embeddings, status. |
| 3 · RAG | Busca híbrida, contexto, resposta com citações, abstenção, streaming, histórico. |
| 4 · Design system | Tokens, componentes base, estrutura do app, command palette. |
| 5 · Telas do MVP | Login/visitante, biblioteca, upload, assistente, visualizador com destaque. **Deploy.** |
| 6 · Ampliação | Busca global e filtros, dashboard, tela de auditoria, administração. |
| 7 · Qualidade da IA | Conjunto de avaliação, métricas, ajuste de parâmetros, página de resultados. |
| 8 · Vitrine | `/about-project`, landing, README com screenshots. |
| 9 · Revisões | Segurança, UX, acessibilidade, performance, E2E completo. |

Depois, se fizer sentido: OCR, XLSX, versionamento de documentos, reranker.

## Pendências

- [ ] Chave da API do Gemini (Google AI Studio) e da Voyage AI, colocadas pelo próprio
      usuário no `.env`.
- [ ] Repositório no GitHub (o CI e o Docker só são validados lá).
- [x] Projeto no Neon.
- [ ] Antes do deploy: limitar cadastros por IP. O cadastro responde 409 para e-mail já
      existente, o que permite descobrir contas; sem verificação por e-mail não há como dar
      resposta genérica, então a mitigação é o limite de taxa.
- [ ] No deploy: aplicar `X-Forwarded-For` confiável (proxy da Vercel/Render) para registrar o
      IP real nos logs de auditoria e no limite de tentativas de login.
