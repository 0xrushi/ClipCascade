from app.config import settings


class Chunker:
    """Splits text into overlapping character-window chunks, preferring
    paragraph and sentence boundaries near the window edge."""

    def __init__(self, size: int | None = None, overlap: int | None = None) -> None:
        self.size = size or settings.chunk_size_chars
        self.overlap = overlap or settings.chunk_overlap_chars

    def split(self, text: str) -> list[str]:
        text = text.strip()
        if not text:
            return []
        if len(text) <= self.size:
            return [text]

        chunks = []
        start = 0
        while start < len(text):
            end = min(start + self.size, len(text))
            if end < len(text):
                # back off to the last paragraph/sentence break in the window
                for sep in ("\n\n", ". ", "\n", " "):
                    cut = text.rfind(sep, start + self.size // 2, end)
                    if cut != -1:
                        end = cut + len(sep)
                        break
            chunks.append(text[start:end].strip())
            if end >= len(text):
                break
            start = max(end - self.overlap, start + 1)
        return [c for c in chunks if c]
