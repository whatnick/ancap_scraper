# Frontend

The user-facing layer consists of a **Streamlit chat application** that communicates with the **FastAPI query API** over HTTP. Both run as separate K8s Deployments.

## Streamlit Chat UI — `services/frontend_app.py`

A single-file Streamlit application providing a conversational interface for asking questions about ANCAP vehicle safety data.

### Features

- Chat-style interface with message history
- Source document references (expandable per answer)
- Sidebar with stack description and conversation reset button
- Persistent session state across Streamlit reruns

### User Flow

```
User types question
  → POST /query to query-api service
  → Display answer in chat bubble
  → Expandable "Sources" section shows PDF names + page numbers
```

### Screenshot Layout

```
┌─────────────────────────────────────────────────┐
│  🚗 ANCAP Vehicle Safety Q&A                     │
│  Ask questions about vehicle safety ratings...   │
│                                                   │
│  ┌─ User ─────────────────────────────────────┐  │
│  │ Which vehicles got 5 stars in 2022?         │  │
│  └─────────────────────────────────────────────┘  │
│                                                   │
│  ┌─ Assistant ─────────────────────────────────┐  │
│  │ Based on the safety reports, the following  │  │
│  │ vehicles received 5-star ratings in 2022:   │  │
│  │ ...                                         │  │
│  │ ▶ Sources                                   │  │
│  └─────────────────────────────────────────────┘  │
│                                                   │
│  ┌─────────────────────────────────────────────┐  │
│  │ e.g. Which vehicles got 5 stars in 2022?    │  │
│  └─────────────────────────────────────────────┘  │
├──────────┐                                        │
│ About    │                                        │
│          │                                        │
│ This app │                                        │
│ uses RAG │                                        │
│ ...      │                                        │
│          │                                        │
│ [Clear]  │                                        │
└──────────┴────────────────────────────────────────┘
```

### Configuration

| Variable | Default | Purpose |
|---|---|---|
| `QUERY_API_URL` | `http://query-api:8000` | URL of the FastAPI backend |

### Error Handling

The frontend gracefully handles:
- **Connection errors** — displays a message if the backend is unreachable
- **Timeouts** — 120-second timeout per query with a user-friendly message
- **Unexpected errors** — catches all exceptions and displays the error

### Running Standalone

```bash
pip install streamlit requests

# Point to a running query API
export QUERY_API_URL=http://localhost:8080
streamlit run services/frontend_app.py --server.port=8501
```

## API Contract

The frontend communicates with the query API using two endpoints:

### `POST /query`

**Request:**
```json
{
  "question": "Which vehicles were tested in 2022?"
}
```

**Response:**
```json
{
  "answer": "Based on the safety reports, the following vehicles were tested...",
  "sources": [
    "safety_data/toyota_corolla_2022_abc123.pdf (page 7)",
    "safety_data/mazda_cx-5_2022_def456.pdf (page 8)"
  ]
}
```

### `POST /reset`

Clears the server-side conversation memory. Called when the user clicks "Clear conversation" in the sidebar.

**Response:**
```json
{
  "status": "memory cleared"
}
```

### `GET /health`

**Response:**
```json
{
  "status": "ok",
  "vector_store": "chroma"
}
```

## Conversation Memory

The system maintains conversation context using LangChain's `ConversationBufferMemory`:

- Memory lives **server-side** in the query-api pod
- The frontend sends each new question; the RAG chain sees all prior Q&A in the chat history
- Memory is per-process (restarting the query-api pod resets it)
- The "Clear conversation" button calls `POST /reset` to wipe the memory

For multi-user deployments, you would need to add session-based memory keying (e.g., by a session cookie or user ID).

## Docker Image

Built from the `frontend` target in the multi-stage Dockerfile:

```dockerfile
FROM python:3.11-slim AS frontend
WORKDIR /app
RUN pip install --no-cache-dir streamlit requests
COPY services/frontend_app.py .
EXPOSE 8501
CMD ["streamlit", "run", "frontend_app.py", ...]
```

This is the lightest image (~180 MB) since it only needs Streamlit and requests — no ML dependencies or Tesseract.

## Kubernetes

The frontend runs as a single-replica Deployment with:
- Port `8501` exposed via a ClusterIP Service
- No volume mounts needed (stateless)
- Readiness probe on Streamlit's `/healthz` endpoint
- The `QUERY_API_URL` env var points to the query-api ClusterIP Service

Public access is provided by the Cloudflare Tunnel, which forwards `ancap.yourdomain.com` to `frontend:8501`. See [deployment.md](deployment.md) for details.

## Tilt Live Update

During development, Tilt syncs `services/frontend_app.py` directly into the running container without rebuilding the image. Streamlit auto-reloads on file changes, so edits appear in the browser within seconds.
