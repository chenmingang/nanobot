"""Vector memory search: semantic search over MEMORY.md and memory/*.md.

Uses ChromaDB for vector store and sentence-transformers for local embedding.
"""

from pathlib import Path
from typing import Any

from loguru import logger

CHUNK_TOKENS = 400
CHUNK_OVERLAP = 80
CHARS_PER_TOKEN = 4  # rough estimate


def _chunk_text(text: str, path: str) -> list[tuple[str, str, int]]:
    """
    Split text into chunks. Returns list of (chunk_text, path, start_line).
    """
    target_chars = CHUNK_TOKENS * CHARS_PER_TOKEN
    overlap_chars = CHUNK_OVERLAP * CHARS_PER_TOKEN
    chunks: list[tuple[str, str, int]] = []
    lines = text.split("\n")
    pos = 0

    while pos < len(lines):
        current: list[str] = []
        current_len = 0
        start_line = pos + 1
        while pos < len(lines) and (current_len < target_chars or not current):
            line = lines[pos]
            current.append(line)
            current_len += len(line) + 1
            pos += 1
        if current:
            chunk_text = "\n".join(current)
            chunks.append((chunk_text, path, start_line))
        if pos < len(lines):
            overlap_count = 0
            overlap_len = 0
            for j in range(len(current) - 1, -1, -1):
                overlap_len += len(current[j]) + 1
                overlap_count += 1
                if overlap_len >= overlap_chars:
                    break
            pos -= overlap_count
    return chunks


_local_model_cache: dict[str, Any] = {}
_torch_warned = False


def _get_embedding_local(text: str, model_name: str) -> list[float] | None:
    """Use sentence-transformers for local embedding. Returns None on failure."""
    global _torch_warned
    try:
        import torch  # noqa: F401
    except ImportError:
        if not _torch_warned:
            _torch_warned = True
            logger.warning(
                "PyTorch not installed; memory semantic search disabled. "
                "Install with: pip install torch  (or pip install nanobot-ai[memory])"
            )
        return None
    try:
        from sentence_transformers import SentenceTransformer
        if model_name not in _local_model_cache:
            _local_model_cache[model_name] = SentenceTransformer(model_name)
        model = _local_model_cache[model_name]
        emb = model.encode(text[:8000], convert_to_numpy=True)
        return emb.tolist()
    except ImportError:
        logger.warning("sentence-transformers not installed; pip install nanobot-ai[memory]")
        return None
    except Exception as e:
        err_str = str(e).lower()
        if "nn" in err_str or "torch" in err_str or isinstance(e, NameError):
            logger.warning(
                "Local embedding failed (PyTorch required): {}. Install with: pip install nanobot-ai[memory]",
                e,
            )
        else:
            logger.warning("Local embedding failed: {}", e)
        return None


class MemorySearchIndex:
    """
    Vector index for memory files (MEMORY.md, memory/*.md).
    Uses ChromaDB + local sentence-transformers embedding.
    """

    def __init__(
        self,
        workspace: Path,
        store_path: Path | None = None,
        local_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    ):
        self.workspace = Path(workspace).expanduser().resolve()
        self.memory_dir = self.workspace / "memory"
        self.store_path = store_path or Path.home() / ".nanobot" / "memory" / "search"
        self.local_model = local_model
        self._client: Any = None
        self._collection: Any = None

    def _get_embedding(self, text: str) -> list[float] | None:
        """Get embedding via local sentence-transformers."""
        return _get_embedding_local(text, self.local_model)

    def _ensure_client(self) -> bool:
        """Initialize ChromaDB client and collection. Returns True if ready."""
        if self._collection is not None:
            return True
        try:
            import chromadb
            self.store_path.mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(path=str(self.store_path))
            self._collection = self._client.get_or_create_collection(
                name="nanobot_memory",
                metadata={"hnsw:space": "cosine"},
            )
            return True
        except ImportError:
            logger.debug("chromadb not installed; memory search disabled")
            return False
        except Exception as e:
            logger.warning("ChromaDB init failed: {}", e)
            return False

    def _get_paths(self) -> list[Path]:
        """Return MEMORY.md and memory/YYYY-MM-DD.md paths."""
        paths: list[Path] = []
        mem_file = self.memory_dir / "MEMORY.md"
        if mem_file.exists():
            paths.append(mem_file)
        if self.memory_dir.exists():
            for p in sorted(self.memory_dir.glob("????-??-??.md"), reverse=True):
                paths.append(p)
        return paths

    def index_paths(self, paths: list[Path] | None = None) -> int:
        """
        Index memory files. Returns number of chunks indexed.
        If ChromaDB or embedding unavailable, returns 0.
        """
        if not self._ensure_client():
            return 0

        paths = paths or self._get_paths()
        all_chunks: list[tuple[str, str, int]] = []
        for p in paths:
            if not p.is_file():
                continue
            try:
                text = p.read_text(encoding="utf-8")
                rel = str(p.relative_to(self.workspace)) if p.is_relative_to(self.workspace) else p.name
                chunks = _chunk_text(text, rel)
                all_chunks.extend(chunks)
            except Exception as e:
                logger.warning("Failed to read {}: {}", p, e)

        if not all_chunks:
            return 0

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for i, (chunk_text, path, line) in enumerate(all_chunks):
            ids.append(f"{path}:{i}")
            documents.append(chunk_text)
            metadatas.append({"path": path, "start_line": line})

        embeddings: list[list[float]] = []
        for doc in documents:
            emb = self._get_embedding(doc)
            if emb is None:
                return 0
            embeddings.append(emb)

        try:
            self._client.delete_collection("nanobot_memory")
            self._collection = self._client.get_or_create_collection(
                name="nanobot_memory",
                metadata={"hnsw:space": "cosine"},
            )
        except Exception:
            pass
        self._collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
        logger.info("Indexed {} chunks from {} files", len(all_chunks), len(paths))
        return len(all_chunks)

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """
        Semantic search. Returns list of {content, path, start_line, score}.
        Auto-indexes on first search if collection is empty.
        """
        if not self._ensure_client():
            return []

        try:
            count = self._collection.count()
            if count == 0:
                self.index_paths()
        except Exception:
            pass

        emb = self._get_embedding(query)
        if emb is None:
            return []

        try:
            results = self._collection.query(
                query_embeddings=[emb],
                n_results=min(top_k, 20),
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.warning("ChromaDB query failed: {}", e)
            return []

        out: list[dict[str, Any]] = []
        docs = results.get("documents", [[]])[0] or []
        metas = results.get("metadatas", [[]])[0] or []
        dists = results.get("distances", [[]])[0] or []

        for i, (doc, meta, dist) in enumerate(zip(docs, metas, dists)):
            if not doc:
                continue
            score = 1.0 - (dist / 2.0) if isinstance(dist, (int, float)) else 1.0
            content = doc[:700] + ("..." if len(doc) > 700 else "")
            out.append({
                "content": content,
                "path": meta.get("path", ""),
                "start_line": meta.get("start_line", 1),
                "score": round(score, 3),
            })
        return out
