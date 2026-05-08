# Smart Retail Assistant

Flask retail application with analytics, admin tools, and a **RAG document assistant** backed by **Azure OpenAI** (embeddings + chat) and **Azure AI Search** for vector retrieval.

## Features

- Retail catalog, orders, and admin UI
- Document upload (PDF, TXT, CSV) → text chunking → Azure OpenAI embeddings → Azure AI Search indexing
- `/rag/chat` answers questions using retrieval + Azure OpenAI chat (with extractive fallback when LLM keys are missing)

## Prerequisites

- Python 3.10+
- Azure OpenAI resource with:
  - An **embedding deployment** (e.g. `text-embedding-3-small` or `text-embedding-ada-002`)
  - A **chat deployment** (e.g. `gpt-4o-mini`) for answers
- Azure AI Search **index** with vector search enabled and field names that match this app (defaults below)

## Environment variables

Copy values into a `.env` file (not committed) or set them in your shell.

| Variable | Purpose |
|----------|---------|
| `SECRET_KEY` | Flask session secret |
| `DATABASE_URL` | SQLAlchemy URI (default SQLite `sqlite:///retail.db`) |
| `AZURE_OPENAI_API_KEY` | Azure OpenAI API key |
| `AZURE_OPENAI_ENDPOINT` | `https://YOUR_RESOURCE.openai.azure.com` |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Name of your embedding model deployment |
| `AZURE_OPENAI_DEPLOYMENT` | Name of your chat model deployment |
| `AZURE_SEARCH_ENDPOINT` | `https://YOUR_SEARCH.search.windows.net` |
| `AZURE_SEARCH_KEY` | Admin or query key with index read/write |
| `AZURE_SEARCH_INDEX` | Target index name |

Optional overrides if your index schema uses different field names:

| Variable | Default |
|----------|---------|
| `AZURE_SEARCH_VECTOR_FIELD` | `contentVector` |
| `AZURE_SEARCH_CONTENT_FIELD` | `content` |

Optional fallbacks:

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | Public OpenAI API for chat only (if Azure chat is not configured) |

## Azure AI Search index schema

Create an index whose **retrievable** fields align with the app. Typical setup:

- **`id`** (`Edm.String`, key) — unique per chunk
- **`filename`** (`Edm.String`, filterable)
- **`chunk_id`** (`Edm.Int32`, filterable optional)
- **`content`** (`Edm.String`, searchable) — chunk text
- **`contentVector`** — `Collection(Edm.Single)`, **vector** profile with dimensions matching your embedding model (e.g. 1536 for many OpenAI models)

Vector search must be enabled on the index and the vector field wired to your chosen embedding model dimensions. If you rename `content` / `contentVector`, set `AZURE_SEARCH_CONTENT_FIELD` and `AZURE_SEARCH_VECTOR_FIELD` accordingly.

Refer to [Azure AI Search vector store](https://learn.microsoft.com/azure/search/vector-search-overview) for the latest index JSON and “vector search profile” configuration.

## Install and run

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux / macOS

pip install -r requirements.txt
python init_db.py               # if you use the bundled DB bootstrap
flask --app run.py run --debug
```

Or:

```bash
python run.py
```

RAG routes (see `app/routes/app.py`):

- `POST /rag/upload` — multipart upload (login required)
- `POST /rag/chat` — JSON `{ "message": "..." }`

## Project layout (RAG-related)

- `app/services/rag/embedder.py` — Azure OpenAI embeddings
- `app/services/rag/azure_search_store.py` — upload, vector search, delete by `filename`
- `app/services/rag/pdf_processor.py` — PDF/TXT/CSV text extraction helpers and chunking
- `app/services/agents/document_agent.py` — orchestration for upload + Q&A

## Scripts

- `test_rag.py` — minimal script; requires valid Azure env vars and an existing index

## Troubleshooting

- **PyMuPDF / `DLL load failed`** on Windows: upgrade or reinstall with `pip install --upgrade PyMuPDF`, or use a TXT/CSV upload until the wheel matches your Python version. PDF extraction loads PyMuPDF only when needed, so the rest of the Flask app can still start.

- **`Client.__init__() got an unexpected keyword argument 'proxies'`** (OpenAI): upgrade with `pip install -U "openai>=1.76.0"` so it matches your installed `httpx` version.

## License / training use

Use and extend as needed for Capgemini training or your own deployment; ensure compliance with your organization’s Azure subscription and data policies.
