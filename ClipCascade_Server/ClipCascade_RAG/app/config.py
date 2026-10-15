import os


class Settings:
    """All configuration comes from environment variables (CCRAG_* prefix)."""

    def __init__(self) -> None:
        self.qdrant_url: str = os.environ.get("CCRAG_QDRANT_URL", "http://localhost:6333")
        self.qdrant_api_key: str | None = os.environ.get("CCRAG_QDRANT_API_KEY")
        self.collection: str = os.environ.get("CCRAG_COLLECTION", "clips")

        # Shared secret; must match CC_RAG_SIDECAR_TOKEN on the Java server.
        # Empty string disables auth (only safe on a private docker network).
        self.auth_token: str = os.environ.get("CCRAG_AUTH_TOKEN", "")

        self.embedding_model: str = os.environ.get(
            "CCRAG_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5"
        )
        self.chunk_size_chars: int = int(os.environ.get("CCRAG_CHUNK_SIZE_CHARS", "2000"))
        self.chunk_overlap_chars: int = int(os.environ.get("CCRAG_CHUNK_OVERLAP_CHARS", "200"))

        self.worker_concurrency: int = int(os.environ.get("CCRAG_WORKER_CONCURRENCY", "2"))
        self.max_queue_size: int = int(os.environ.get("CCRAG_MAX_QUEUE_SIZE", "500"))
        self.job_max_retries: int = int(os.environ.get("CCRAG_JOB_MAX_RETRIES", "2"))

        # Hard ceiling on downloaded media, protects disk on long videos.
        self.max_download_mb: int = int(os.environ.get("CCRAG_MAX_DOWNLOAD_MB", "512"))
        self.download_dir: str = os.environ.get("CCRAG_DOWNLOAD_DIR", "/tmp/ccrag")

        self.transcription_enabled: bool = (
            os.environ.get("CCRAG_TRANSCRIPTION_ENABLED", "true").lower() == "true"
        )
        self.whisper_model: str = os.environ.get("CCRAG_WHISPER_MODEL", "base")

        # Transcripts that are mostly non-speech (music/noise) or too short
        # are discarded so the pipeline falls back to describing the
        # thumbnail image instead.
        self.whisper_no_speech_threshold: float = float(
            os.environ.get("CCRAG_WHISPER_NO_SPEECH_THRESHOLD", "0.6")
        )
        self.whisper_min_words: int = int(os.environ.get("CCRAG_WHISPER_MIN_WORDS", "3"))

        # Gemini is used for image understanding/OCR.
        self.gemini_api_key: str = os.environ.get("GEMINI_API_KEY", "")
        self.gemini_model: str = os.environ.get("CCRAG_GEMINI_MODEL", "gemini-3-flash-preview")

        # Hermes is an OpenAI-compatible chat-completions endpoint (with URL
        # fetching/browsing) used to pull the text content of x.com/Twitter
        # posts, replacing the old fxtwitter API extraction.
        self.hermes_api_base_url: str = os.environ.get(
            "HERMES_API_BASE_URL", "http://192.168.1.174:8642"
        )
        self.hermes_model: str = os.environ.get("HERMES_MODEL", "hermes")


settings = Settings()
