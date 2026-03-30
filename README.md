# Caching Proxy

A high-performance HTTP caching proxy built with **FastAPI** and **Redis**. It forwards incoming requests to a configurable upstream origin, caches successful **GET** responses in Redis, and exposes health and OpenAPI documentation on dedicated paths that are not proxied.

## 🚀 Features

- **Configurable origin** — Point the proxy at any HTTP(S) API via CLI (`--origin`) or `PROXY_ORIGIN` in the environment.
- **Redis-backed response cache** — GET responses with status `200` are stored and served with an `X-Cache: HIT` or `X-Cache: MISS` header.
- **Hop-by-hop header handling** — Request/response headers that must not be forwarded across proxies are filtered per common HTTP practice.
- **Async stack** — FastAPI, `httpx` for upstream calls, and `redis.asyncio` for cache I/O.
- **Operational endpoints** — `/health` reports application and Redis status; `/docs`, `/redoc`, and `/openapi.json` stay on the proxy (not forwarded).

## 📋 Tech Stack

- **FastAPI** — Async web framework and OpenAPI docs
- **Redis** — Response cache (async client)
- **HTTPX** — Async HTTP client to the origin
- **Pydantic Settings** — Environment-based configuration
- **Uvicorn** — ASGI server
- **Poetry** — Dependency and packaging

## 🔁 How it works

1. Requests whose paths are **not** reserved (`/docs`, `/redoc`, `/openapi.json`, `/health`, …) are handled by the proxy middleware and sent to `proxy_origin + path + query`.
2. **GET** requests first look up a cache key derived from method and full target URL. On a hit, the stored body and headers are returned.
3. Other methods (and GETs on cache miss) call the origin; **GET** + **200** responses are written to Redis for subsequent requests.
4. Use `caching-proxy --clear-cache` to remove all keys under the proxy’s Redis prefix.

## 🛠️ Setup

### Prerequisites

- Python **3.14+**
- **Poetry**
- A running **Redis** instance reachable with the credentials you configure

### Installation

```bash
git clone <repository-url>
cd caching_proxy

poetry install
```

### Configuration

Configuration is read from the environment (and optionally a `.env` file in the project root). Create a `.env` file or export variables in your shell.

| Variable | Required | Description |
|----------|----------|-------------|
| `SUPPORT_EMAIL` | Yes | Contact email (used in OpenAPI metadata). |
| `REDIS_HOST` | Yes | Redis hostname. |
| `REDIS_PORT` | Yes | Redis port. |
| `REDIS_USERNAME` | Yes | Redis username. |
| `REDIS_PASSWORD` | Yes | Redis password. |
| `PROXY_ORIGIN` | No* | Upstream base URL (e.g. `https://api.example.com`). *Required for proxied traffic unless you pass `--origin` to `caching-proxy`. |
| `APP_NAME` | No | Default: `CachingProxy`. |
| `APP_VERSION` | No | Default: `0.1.0`. |
| `BASE_URL` | No | Public base URL for docs/examples (default: `http://localhost:8000`). |

**Setting the origin**

- **CLI (recommended for `caching-proxy`)**: `PROXY_ORIGIN` is set from `--origin` when you run the `caching-proxy` script (see below).
- **Environment**: set `PROXY_ORIGIN` if you start the app another way (e.g. `uvicorn`) so the proxy can reach the upstream.

If `proxy_origin` is unset when a proxied request arrives, the API responds with **503** and a JSON error body.

### Running the server

#### API entrypoint (`api` script)

Runs Uvicorn on port **5000** (see `scripts/cli.py`).

```bash
# Development: localhost + auto-reload
poetry run api --local

# Production-style: 0.0.0.0, no reload
poetry run api
```

Ensure Redis is up and `PROXY_ORIGIN` is set if you need the proxy path to work.

#### Caching proxy CLI (`caching-proxy`)

Use this when you want to pass **port** and **origin** on the command line:

```bash
poetry run caching-proxy --port 8080 --origin https://dummyjson.com
```

Clear all cached proxy entries in Redis and exit:

```bash
poetry run caching-proxy --clear-cache
```

(`--clear-cache` cannot be combined with `--port` or `--origin`.)

## 📚 API documentation

When the app is running, interactive docs are available at:

- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI JSON**: `/openapi.json`

The **Miscellaneous** section documents `/health`. Remaining traffic to non-excluded paths is proxied and may not appear as separate operations in the schema (behavior is defined by the middleware and origin).

## 🏗️ Project structure

```
caching_proxy/
├── src/
│   ├── main.py              # FastAPI app, lifespan, middleware, routers
│   ├── config.py            # Settings (env / .env)
│   ├── custom_openapi.py    # OpenAPI customization
│   ├── db/
│   │   └── redis_client.py  # Async Redis connection manager
│   ├── middleware/
│   │   └── proxy_middleware.py
│   ├── models/              # Pydantic models (e.g. health)
│   ├── routes/              # Non-proxied routes (e.g. /health)
│   ├── services/
│   │   ├── proxy_service.py # Forward requests, cache integration
│   │   └── proxy_cache.py   # Redis GET cache + clear
│   └── utils/               # Logging helpers
├── scripts/
│   └── cli.py               # `api` and `caching-proxy` entrypoints
├── pyproject.toml
└── README.md
```

## 📝 License

MIT License — see [LICENSE](LICENSE).

## 🖋️ Author

- **Muzaffar Shaikh** — [muzaffarshaikh0201@gmail.com](mailto:muzaffarshaikh0201@gmail.com)
