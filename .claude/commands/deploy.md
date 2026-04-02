Lance ou redémarre la stack complète via systemd. Argument optionnel : `$ARGUMENTS` (ex: `backend`, `bot` pour cibler un seul service).

## Prérequis

- Fichier `.env` présent à la racine (copié depuis `.env.example`)
- Services systemd installés : `bash deploy/install.sh` (première fois uniquement)
- `uv` installé sur le serveur (`~/.local/bin/uv`)

## Étapes à suivre

1. **Lancer les tests avant de déployer** :
   ```bash
   cd backend && uv run pytest --tb=short -q
   ```
   Arrêter si des tests échouent — ne pas déployer du code cassé.

2. **Synchroniser les dépendances** :
   ```bash
   cd backend && uv sync
   cd ../bot && uv sync
   ```

3. **Redémarrer les services** :
   ```bash
   # Stack complète
   sudo systemctl restart dl_backend.service discord_bot.service

   # Ou un seul service (si $ARGUMENTS est renseigné)
   sudo systemctl restart dl_$ARGUMENTS.service   # ex: dl_backend.service
   # ou
   sudo systemctl restart discord_bot.service     # pour le bot
   ```

4. **Vérifier que les services sont UP** :
   ```bash
   systemctl status dl_backend.service discord_bot.service --no-pager
   ```
   Les deux doivent afficher `active (running)`.

5. **Vérifier les logs au démarrage** :
   ```bash
   journalctl -u dl_backend -u discord_bot -n 30 --no-pager
   ```
   Signaux OK à chercher :
   - Backend : `Application startup complete`
   - Bot : `Bot connecté en tant que`

6. **Test de santé** :
   ```bash
   curl -s http://127.0.0.1:8000/api/v1/status | python3 -m json.tool
   ```

## Commandes utiles

```bash
# Voir les logs en temps réel
journalctl -u dl_backend -u discord_bot -f

# Statut rapide
systemctl status dl_backend discord_bot

# Arrêter les services
sudo systemctl stop dl_backend.service discord_bot.service

# Première installation des services
bash deploy/install.sh
```

## En cas d'erreur

- **Port 8000 déjà utilisé** : `ss -tlnp | grep 8000` pour identifier le process
- **Service qui redémarre en boucle** : `journalctl -u dl_backend -n 50` pour voir l'erreur
- **Bot ne joint pas le backend** : vérifier `BACKEND_URL=http://localhost:8000` dans `.env`
- **Alembic error** : `cd backend && uv run alembic upgrade head`
