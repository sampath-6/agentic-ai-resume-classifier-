# Resume Classifier — Multi-Agent Backend (LangGraph + Chroma + FastAPI)

A recruiter-facing service that ingests resumes, classifies them with an LLM, indexes
them in a vector store, and answers natural-language candidate queries — built as a
**supervisor/router multi-agent graph** on [LangGraph](https://langchain-ai.github.io/langgraph/).

Upload resumes → they are parsed, classified, renamed, and indexed automatically → query
by skill/role → get a ranked answer plus a table of matches, each downloadable by clicking
the candidate name.

> This is the **backend**. The React UI lives in `../resume-classifier-ui`.

---

## Features

- **Multi-agent pipeline** — 10 LangGraph nodes across an upload branch and a query branch,
  wired with conditional edges.
- **Folder-drain ingestion** — drop files in an inbox; a loop drains it one file at a time,
  re-scanning after each so mid-run uploads are picked up too.
- **LLM classification** — Claude extracts `first_name`, `last_name`, `years_experience`,
  `skills`, `seniority`, `primary_role`, and a summary via structured output.
- **Local, free embeddings** — Chroma's `DefaultEmbeddingFunction` (ONNX all-MiniLM-L6-v2)
  runs on-device; no embedding API cost.
- **Query guardrail** — a zero-cost keyword screen that only escalates to an LLM judge on a
  hit, blocking prompt-injection and discriminatory (age/gender/disability) queries.
- **Stable download links** — each resume is keyed by an opaque `resume_id` UUID, so renames
  never orphan the index and downloads are path-traversal safe.
- **JWT auth** — single-email allowlist; login issues an HS256 token required by every data route.
- **Resilience** — per-file size rejection (>2 MB), a parse-retry loop (pypdf → pdfplumber),
  and a broaden-search loop that drops the metadata filter when nothing matches.

---

## Architecture

```
                         ┌────────────┐
              intent →   │ supervisor │   (entry, routes by intent)
                         └─────┬──────┘
        upload  ┌──────────────┴───────────────┐  query
                ▼                               ▼
        ┌───────────────┐               ┌────────────────────┐
        │  scan_folder  │◄──┐           │ query_guardrail    │──reject──▶ END
        └──────┬────────┘   │           └─────────┬──────────┘
               ▼            │ (loop)               │ pass
        ┌───────────────┐   │                      ▼
        │ analyzer_agent│   │           ┌────────────────────┐
        └──────┬────────┘   │           │  retrieval_agent   │◄─┐ broaden
               ▼            │           └─────────┬──────────┘  │ (loop)
        ┌───────────────┐   │                     ▼             │
        │ ingestion ◄─┐ │   │           ┌────────────────────┐  │
        │  (retry loop)│ │   │           │ synthesizer_agent  │──┘
        └──────┬───────┘ │   │           └─────────┬──────────┘
               ▼         │   │                     ▼
        ┌───────────────┐│   │                    END
        │ classifier    ││   │
        └──────┬────────┘│   │
               ▼         │   │
        ┌───────────────┐│   │
        │ rename_agent  ││   │
        └──────┬────────┘│   │
               ▼         │   │
        ┌───────────────┐│   │
        │ indexer_agent │┘───┘  (folder-drain: back to scan_folder; empty ⇒ END)
        └───────────────┘
```

**Three loops:** parse-retry (self-loop on ingestion), folder-drain (multi-node cycle),
broaden-search (self-loop on retrieval). Full explanations, diagrams, and code walkthroughs
live in the UI's **Architecture** and **LangGraph** documentation tabs.

| Layer            | Choice                                                        |
| ---------------- | ------------------------------------------------------------- |
| Graph runtime    | LangGraph `StateGraph` + `MemorySaver` checkpointer           |
| LLM              | Anthropic Claude (`claude-sonnet-5`) via `langchain-anthropic`|
| Vector store     | ChromaDB `PersistentClient`, on-disk, cosine distance         |
| Embeddings       | `DefaultEmbeddingFunction` — local ONNX all-MiniLM-L6-v2      |
| API              | FastAPI + Uvicorn                                             |
| Auth             | PyJWT (HS256) + FastAPI `HTTPBearer`                          |
| Parsing          | pypdf → pdfplumber (PDF), python-docx (DOCX), plain (TXT)     |

---

## Prerequisites

- **Python 3.12**
- An **Anthropic API key** on a funded account (pay-as-you-go — the API is billed separately
  from any claude.ai subscription).

---

## Setup

```bash
# 1. create a virtual environment
py -3.12 -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS/Linux

# 2. install dependencies
pip install -r requirements.txt

# 3. create your .env from the template
copy .env.example .env            # Windows
# cp .env.example .env            # macOS/Linux
```

Then edit `.env` and set at least:

```ini
ANTHROPIC_API_KEY=sk-ant-...              # from console.anthropic.com (funded account)
ALLOWED_EMAIL=retrieve-agent-test@gmail.com
JWT_SECRET=<a-long-random-string>         # e.g. python -c "import secrets;print(secrets.token_hex(32))"
```

### Environment variables

| Variable                | Default                              | Purpose                                      |
| ----------------------- | ------------------------------------ | -------------------------------------------- |
| `ANTHROPIC_API_KEY`     | —                                    | Claude API key (required)                    |
| `ANTHROPIC_MODEL`       | `claude-sonnet-5`                    | Model id                                     |
| `ALLOWED_EMAIL`         | `your-email@example.com`             | The only email allowed to log in             |
| `JWT_SECRET`            | `dev-secret-change-me`               | HS256 signing secret                         |
| `JWT_EXPIRY_MINUTES`    | `1440`                               | Token lifetime                               |
| `CORS_ORIGINS`          | `http://localhost:5173`              | Allowed frontend origins (comma-separated)   |
| `UPLOAD_ROOT`           | `./uploads/resume`                   | Inbox root (indexed/rejected/failed nested)  |
| `CHROMA_DIR`            | `./chroma_db`                        | On-disk vector store path                    |
| `CHROMA_COLLECTION`     | `resumes`                            | Chroma collection name                       |
| `MAX_FILE_SIZE_BYTES`   | `2097152` (2 MB)                     | Per-file size cap                            |
| `MAX_PARSE_RETRIES`     | `2`                                  | Parse-retry loop cap                         |
| `MAX_BROADEN_ATTEMPTS`  | `2`                                  | Broaden-search loop cap                      |
| `TOP_K`                 | `20`                                 | Matches fetched per query                    |
| `NARRATION_COUNT`       | `5`                                  | Matches the synthesizer narrates in prose    |
| `GUARDRAIL_KEYWORDS_PATH` | `./config/guardrail_keywords.txt`  | Comma-separated guardrail keyword file       |
| `GRAPH_RECURSION_LIMIT` | `1000`                               | LangGraph step cap (scales with inbox size)  |

---

## Running

```bash
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```

- Health check: <http://localhost:8000/>
- Interactive API docs (Swagger): <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

Uploaded files are sorted on disk into `uploads/resume/{indexed,rejected,failed}/`; the
vector index persists in `chroma_db/`.

---

## API

All routes are under `/api` except the health check. A 🔒 route needs
`Authorization: Bearer <token>`.

| Method | Path                                  | Auth | Purpose                                        |
| ------ | ------------------------------------- | ---- | ---------------------------------------------- |
| POST   | `/api/auth/login`                     | —    | Exchange the allowed email for a JWT           |
| GET    | `/api/resumes`                        | 🔒   | List all indexed candidates                    |
| POST   | `/api/upload`                         | 🔒   | Upload file(s); drains the whole inbox         |
| POST   | `/api/query`                          | 🔒   | Guardrail → vector search → synthesized answer |
| GET    | `/api/resumes/{resume_id}/download`   | 🔒   | Download the original file by UUID             |
| GET    | `/`                                   | —    | Liveness probe                                 |

### Quick smoke test

```bash
# 1. log in (only the ALLOWED_EMAIL succeeds; others get 403 "User is not authorized")
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"retrieve-agent-test@gmail.com"}' | python -c "import sys,json;print(json.load(sys.stdin)['token'])")

# 2. upload a resume (triggers classify → index)
curl -X POST http://localhost:8000/api/upload -H "Authorization: Bearer $TOKEN" \
  -F "files=@/path/to/resume.pdf"

# 3. query
curl -X POST http://localhost:8000/api/query -H "Authorization: Bearer $TOKEN" \
  -F "query=senior java engineer with kafka"
```

---

## Project structure

```
app/
├── main.py                  # FastAPI app + CORS + router mount
├── config.py                # Settings from .env (creates the uploads/ tree)
├── state.py                 # GraphState TypedDict + reducers
├── graph.py                 # build_graph(): nodes, edges, routers, loops, compile
├── agents/                  # one module per node
│   ├── analyzer.py          #   size gate (2 MB)
│   ├── ingestion.py         #   parse text + mint resume_id
│   ├── classifier.py        #   Claude structured extraction  (LLM)
│   ├── rename.py            #   Firstname_Lastname_Years + move to indexed/
│   ├── indexer.py           #   composite doc → Chroma upsert
│   ├── query_guardrail.py   #   keyword screen + gated LLM judge (LLM)
│   ├── retrieval.py         #   top-20 vector search
│   └── synthesizer.py       #   ranked prose over top 5  (LLM)
├── api/
│   ├── auth.py              # POST /auth/login
│   └── routes.py            # upload / query / list / download
└── services/
    ├── llm.py               # get_llm() → ChatAnthropic
    ├── chroma_store.py      # PersistentClient + embedding function
    ├── parsing.py           # pypdf → pdfplumber → python-docx
    └── auth.py              # JWT create/verify + HTTPBearer dependency
config/
└── guardrail_keywords.txt   # comma-separated screen list
```

`design_summary.json` and `design_conversation_journal.json` capture the full technical
spec and the design conversation that produced it.

---

## Notes & troubleshooting

- **`credit balance is too low`** — the API key's Anthropic account has no credits, or the
  key belongs to a *different* account/org than the one you funded. Create a key in the
  funded account and use that.
- **`temperature is deprecated for this model`** — `claude-sonnet-5` rejects the parameter;
  `get_llm()` intentionally omits it. Don't re-add it.
- First run downloads the ~80 MB ONNX embedding model into a local cache (one-time).
