# ── Stage 1 : Build Angular ──────────────────────────────────────────────────
FROM node:22-slim AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build -- --configuration production


# ── Stage 2 : Backend Python + Chromium ──────────────────────────────────────
FROM python:3.12-slim

# Chromium requis par seleniumbase (scraping Wawacity / dl-protect)
RUN apt-get update && apt-get install -y --no-install-recommends \
        chromium \
        chromium-driver \
    && rm -rf /var/lib/apt/lists/*

# uv — gestionnaire de paquets Python
COPY uv /usr/local/bin/uv

WORKDIR /app

# Dépendances Python (layer caché si pyproject.toml/uv.lock inchangés)
COPY backend/pyproject.toml backend/uv.lock ./backend/
RUN cd backend && uv sync --frozen --no-dev

# Code applicatif
COPY backend/ ./backend/

# Build Angular — FastAPI le cherche à {project_root}/frontend/dist/frontend/browser/
COPY --from=frontend-builder /app/frontend/dist/frontend/browser/ ./frontend/dist/frontend/browser/

WORKDIR /app/backend

# Chromium installé via apt
ENV SELENIUM_BINARY_LOCATION=/usr/bin/chromium

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
