"""Every setting QueryMesh needs, read from environment variables (the .env file)."""
import os

from dotenv import load_dotenv

load_dotenv()  # copies the lines of .env into os.environ (real env vars win)


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default)


# Search engine (OpenSearch)
OPENSEARCH_URL = env("OPENSEARCH_URL", "http://localhost:9200")
INDEX_NAME = env("INDEX_NAME", "arxiv-chunks")
SEARCH_PIPELINE = env("SEARCH_PIPELINE", "querymesh-rrf")

# Embeddings (Jina AI)
JINA_API_KEY = env("JINA_API_KEY")
EMBED_MODEL = env("EMBED_MODEL", "jina-embeddings-v5-text-small")
EMBED_DIM = int(env("EMBED_DIM", "1024"))

# Language model (vLLM on Hyperstack, OpenAI-compatible)
LLM_BASE_URL = env("LLM_BASE_URL", "http://localhost:8000/v1")
LLM_API_KEY = env("LLM_API_KEY", "EMPTY")
LLM_MODEL = env("LLM_MODEL", "qwen3-4b")

# Cache (Upstash Redis)
REDIS_URL = env("REDIS_URL")
CACHE_TTL_SECONDS = int(env("CACHE_TTL_SECONDS", "86400"))

# Paper storage (S3 on FakeCloud or AWS). Empty = do not upload.
PAPERS_BUCKET = env("PAPERS_BUCKET")

# Agents: base URLs of the five agent servers, comma separated
AGENT_URLS = [u.strip() for u in env("AGENT_URLS").split(",") if u.strip()]
WORKER_MODE = env("WORKER_MODE", "local")  # local = in-process, remote = MCP over SSE

# API security (JWT)
JWT_SECRET = env("JWT_SECRET", "change-me-please-use-a-long-random-string")
JWT_MINUTES = int(env("JWT_MINUTES", "60"))
API_USERNAME = env("API_USERNAME", "admin")
API_PASSWORD = env("API_PASSWORD", "admin")
API_URL = env("API_URL", "http://localhost:8090")

# Telegram
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN")

# Agentic RAG limits
MIN_RELEVANT = int(env("MIN_RELEVANT", "2"))
MAX_RETRIEVALS = int(env("MAX_RETRIEVALS", "2"))
MAX_GENERATIONS = int(env("MAX_GENERATIONS", "2"))
TOP_K = int(env("TOP_K", "8"))
