#!/usr/bin/env bash
# Installation des services systemd pour dl_discord_bot v2
set -euo pipefail

DEPLOY_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$DEPLOY_DIR")"

echo "==> Vérification du .env..."
if [[ ! -f "$PROJECT_DIR/.env" ]]; then
    echo "ERREUR : $PROJECT_DIR/.env introuvable. Copier .env.example → .env et remplir les variables."
    exit 1
fi

echo "==> Build du frontend Angular..."
cd "$PROJECT_DIR/frontend"
npm ci --silent
npx ng build --configuration production

echo "==> Application de la migration Alembic..."
cd "$PROJECT_DIR/backend"
/home/gones/.local/bin/uv run alembic upgrade head

echo "==> Installation des fichiers service..."
sudo cp "$DEPLOY_DIR/dl_backend.service" /etc/systemd/system/dl_backend.service
sudo cp "$DEPLOY_DIR/discord_bot.service" /etc/systemd/system/discord_bot.service

echo "==> Rechargement systemd + activation des services..."
sudo systemctl daemon-reload
sudo systemctl enable dl_backend.service discord_bot.service
sudo systemctl restart dl_backend.service
sudo systemctl restart discord_bot.service

echo ""
echo "==> Statut :"
systemctl status dl_backend.service --no-pager
echo ""
systemctl status discord_bot.service --no-pager
echo ""
echo "Logs : journalctl -u dl_backend -u discord_bot -f"
