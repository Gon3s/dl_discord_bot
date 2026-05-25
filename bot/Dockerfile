FROM python:3.12-slim

# uv — gestionnaire de paquets Python
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app/bot

# Dépendances Python
COPY bot/pyproject.toml bot/uv.lock ./
RUN uv sync --frozen --no-dev

# Code applicatif
COPY bot/ .

# Les logs Discord vont sur stdout (StreamHandler) — le FileHandler écrit
# bot.log dans /app/bot/bot.log ; monter un volume si persistance souhaitée.
CMD ["uv", "run", "python", "main.py"]
