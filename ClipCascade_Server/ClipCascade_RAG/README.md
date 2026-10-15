# ClipCascade RAG Sidecar

Ingests links copied to the clipboard (x.com / fxtwitter, instagram / kkinstagram,
tiktok, youtube / youtu.be, or any https page), extracts their content
(post text, article text, video subtitles/transcripts, image OCR), and indexes
it into Qdrant so past clips are semantically searchable.

## Flow

```
ClipCascade server ──POST /ingest──▶ in-memory queue ──▶ IngestionPipeline
                                                          ├─ ExtractorRegistry
                                                          │    ├─ SocialPostExtractor (x.com, instagram)
                                                          │    ├─ YtDlpExtractor     (youtube, tiktok)
                                                          │    └─ WebPageExtractor   (any https, catch-all)
                                                          ├─ MediaEnrichers (WhisperTranscriber, ImageDescriber)
                                                          └─ Chunker → FastEmbedEmbedder → QdrantIndexer
```

Jobs are held in memory only — a lost job just means re-copying the link.
Duplicate URLs (same user) are skipped at enqueue and at index time.

## Endpoints

- `POST /ingest` — `{url, link_type, username, timestamp}`; returns 202 immediately.
- `GET /search?username=&q=&limit=` — vector search filtered to that user's clips.
- `GET /health` — queue depth and job counters.

Auth: requests must carry `X-CCRAG-Token` matching `CCRAG_AUTH_TOKEN` (empty = auth off).
Search from the ClipCascade server goes through its authenticated `/rag/search` proxy.

## Run

```
docker compose -f ../docker-compose/docker-compose-rag.yml up --build
```

Key env vars (see `app/config.py` for all): `CCRAG_QDRANT_URL`, `CCRAG_AUTH_TOKEN`,
`CCRAG_EMBEDDING_MODEL`, `CCRAG_WORKER_CONCURRENCY`, `CCRAG_TRANSCRIPTION_ENABLED`,
`CCRAG_WHISPER_MODEL`, `CCRAG_MAX_DOWNLOAD_MB`.

Transcription uses `faster-whisper` (a required dependency) for videos without
subtitles. Image understanding/OCR uses the Gemini API (`gemini-3-flash-preview`
by default, override with `CCRAG_GEMINI_MODEL`) — set `GEMINI_API_KEY` in the
environment; the sidecar will not start without it.

x.com/Twitter post text is fetched via an OpenAI-compatible chat-completions
endpoint (`HERMES_API_BASE_URL`, default `http://192.168.1.174:8642`; model
name via `HERMES_MODEL`, default `hermes`) instead of the fxtwitter API.

## Note on encryption

The ClipCascade server can only detect links in **unencrypted** text payloads.
Clients using end-to-end clipboard encryption will not have their links ingested.
