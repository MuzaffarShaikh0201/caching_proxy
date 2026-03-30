# Caching Proxy Architecture

## System Overview

Caching Proxy is a single FastAPI application that sits in front of a configurable **origin** HTTP(S) server. It forwards most requests upstream with **HTTPX**, caches **GET** responses that return **200** in **Redis**, and serves a small set of **first-party routes** (health, OpenAPI UI) without proxying.

```
┌─────────────┐
│   Clients   │
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────┐
│         FastAPI (ASGI / Uvicorn)         │
│  CORS → ProxyMiddleware → App routes     │
└──────┬───────────────────────┬───────────┘
       │                       │
       │ excluded paths        │ proxied paths
       │ (/docs, /redoc,       │ (everything else)
       │  /openapi.json,       │
       │  /health)             │
       ▼                       ▼
┌──────────────┐      ┌──────────────────────┐
│  App router  │      │   proxy_service      │
│  (misc)      │      │   + httpx → Origin   │
└──────────────┘      └───────────┬──────────┘
                                │
                    ┌───────────┴───────────┐
                    │                       │
                    ▼                       ▼
            ┌──────────────┐        ┌───────────────┐
            │    Redis     │        │ Origin server │
            │ (GET cache)  │        │ (PROXY_ORIGIN)│
            └──────────────┘        └───────────────┘
```

## Components

### 1. FastAPI application (`src/main.py`)

- ASGI app with **lifespan** hooks: initializes and closes the async Redis client on startup/shutdown.
- **CORSMiddleware**: permissive defaults (`allow_origins=["*"]`, all methods/headers); adjust for production if needed.
- **ProxyMiddleware**: registered after CORS so it runs **first** on incoming requests; either forwards to the proxy pipeline or passes through to normal routing for excluded paths.
- **Custom OpenAPI** (`src/custom_openapi.py`): enriched API docs (code samples, branding); documents first-party routes such as `/health`.
- **Routers**: `misc_router` for non-proxied endpoints.

### 2. Proxy middleware (`src/middleware/proxy_middleware.py`)

- Intercepts every request whose path is **not** in the excluded set.
- **Excluded paths**: `/docs`, `/redoc`, `/openapi.json`, `/health`, plus any path under `/docs` or `/redoc` prefixes (e.g. static assets for Swagger UI).
- For non-excluded paths, delegates to `proxy_request` and **does not** call `call_next` (the FastAPI route table is bypassed for proxied traffic).

### 3. Proxy service (`src/services/proxy_service.py`)

- Builds the upstream URL: `PROXY_ORIGIN` + request path + query string.
- If `PROXY_ORIGIN` is unset, returns **503** JSON for proxied requests.
- **GET**: checks Redis via `proxy_cache` before calling the origin; sets response header `X-Cache: HIT` or `X-Cache: MISS`.
- **Non-GET** (and GET bodies are rare): forwards method, filtered headers, and body where applicable using **HTTPX** `AsyncClient` with redirects enabled and a bounded timeout.
- Strips **hop-by-hop** headers from requests and responses (RFC 7230); omits forwarding `Host` and does not persist hop-by-hop headers in cached entries.
- On upstream connection errors, returns **502** JSON.

### 4. Redis cache (`src/db/redis_client.py`, `src/services/proxy_cache.py`)

- **redis.asyncio** client from URL built in settings (`redis://user:pass@host:port`).
- Cache keys: prefix `caching_proxy:v1:` + method + full target URL.
- Values: JSON with `status_code`, response `headers`, and **base64-encoded** body.
- **Only** successful **GET** responses with status **200** are stored.
- `clear_proxy_cache()` scans and deletes keys matching the prefix (used by `caching-proxy --clear-cache`).

### 5. Miscellaneous routes (`src/routes/misc.py`)

- **`GET /health`**: returns JSON including Redis reachability (`dependencies.redis`); responds **503** when Redis is unhealthy.

### 6. CLI entrypoints (`scripts/cli.py`)

- **`api`**: runs Uvicorn against `src.main:app` (port **5000**); `--local` enables reload on localhost.
- **`caching-proxy`**: sets `PROXY_ORIGIN` from `--origin` and binds `--port`; optional `--clear-cache` for administrative cache flush.

## Data flow

### Proxied request (typical GET)

1. Client → Uvicorn → **ProxyMiddleware** (path not excluded).
2. `proxy_request` computes target URL → **`proxy_cache.get_cached`** for GET.
3. **Cache hit**: return stored body/headers + `X-Cache: HIT`.
4. **Cache miss**: **HTTPX** request to origin → return response + `X-Cache: MISS` → if GET and status **200**, **`proxy_cache.set_cached`**.

### First-party routes

1. Client → Uvicorn → **ProxyMiddleware** sees excluded path → **`call_next`** → FastAPI routing → e.g. **`GET /health`** or static OpenAPI assets.

### Cache invalidation

- No TTL is applied in code; eviction is operational (flush DB, `--clear-cache`, or manual key deletion). Adding TTL is a possible future enhancement.

## Scaling strategy

### Horizontal scaling

- Run **multiple Uvicorn workers or replicas** behind a load balancer. No in-memory session state is required for proxying; **shared Redis** gives a **shared cache** across instances.
- Ensure all instances use the same **`PROXY_ORIGIN`** and Redis credentials so cache keys stay consistent.

### Vertical scaling

- Increase Uvicorn workers, file descriptor limits, and Redis memory if the working set of cached URLs grows.

### Origin and Redis

- The **origin** is the main bottleneck for cache misses; Redis size and latency bound cache hits.

## Performance characteristics

1. **Async I/O**: Redis and HTTPX operations are async within the request path.
2. **GET caching**: Reduces origin load and latency for repeated identical URLs.
3. **HTTPX client**: Each proxied request currently uses a **new** `AsyncClient` context (simple and safe; pooling could be added later for high QPS).
4. **Hop-by-hop filtering**: Avoids leaking proxy-specific headers and keeps stored headers closer to what clients should see.

## Monitoring

- **Health**: `GET /health` — application name, version, and Redis dependency status.
- **Cache visibility**: `X-Cache` response header on proxied GET responses.
- **Logging**: coloredlogs-based setup in `src/utils/logging.py` (extend with structured logging or external sinks in production as needed).

## Configuration

- Centralized in **`src/config.py`** via **Pydantic Settings**; loads from environment variables and optional `.env`.
- Required: Redis connection parameters, `SUPPORT_EMAIL`; **`PROXY_ORIGIN`** must be set for proxied traffic unless supplied by the **`caching-proxy`** CLI (which sets the environment variable for that process).

## Production considerations

1. **TLS**: Terminate TLS at a reverse proxy (e.g. nginx, cloud LB) in front of Uvicorn; ensure `PROXY_ORIGIN` uses `https://` when the upstream expects HTTPS.
2. **CORS**: The default allows all origins; restrict `allow_origins` when exposing the service publicly.
3. **Secrets**: Keep Redis credentials and any future API keys out of source control; inject via environment or a secrets manager.
4. **Redis**: Use persistence and monitoring appropriate to your SLA; size for peak cache footprint and set eviction policy if relying on Redis memory limits.
5. **Observability**: Add metrics (latency, cache hit ratio, 502/503 rates) and centralized logging for production operations.
6. **Authentication**: The proxy does **not** implement API-key or JWT validation by default; enforce auth at the edge or on the origin if required.
