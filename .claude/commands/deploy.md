Lance ou redémarre la stack complète via docker-compose. Argument optionnel : `$ARGUMENTS` (ex: `backend`, `frontend`, `bot` pour cibler un seul service).

## Prérequis

- Docker et docker-compose installés
- Fichier `.env` présent à la racine (copié depuis `.env.example`)
- `DOWNLOAD_PATH` défini et le répertoire existant sur l'hôte

## Étapes à suivre

1. **Vérifier le fichier `.env`** :
   - Confirmer que `DISCORD_TOKEN`, `ALLDEBRID_API_KEY`, `DOWNLOAD_PATH` sont renseignés
   - Confirmer que `DOWNLOAD_PATH` existe sur le système hôte :
     ```bash
     ls "$DOWNLOAD_PATH"
     ```

2. **Builder et démarrer** :
   ```bash
   # Stack complète
   docker-compose up --build -d

   # Ou un seul service (si $ARGUMENTS est renseigné)
   docker-compose up --build -d $ARGUMENTS
   ```

3. **Vérifier que les services sont UP** :
   ```bash
   docker-compose ps
   ```
   Les 3 services doivent être `running` : `backend`, `bot`, `frontend`

4. **Vérifier les logs au démarrage** :
   ```bash
   # Backend
   docker-compose logs --tail=50 backend

   # Bot
   docker-compose logs --tail=20 bot
   ```
   Signaux OK à chercher :
   - Backend : `Application startup complete`
   - Bot : `Logged in as`

5. **Test de santé** :
   ```bash
   curl -s http://localhost:8000/api/v1/status | python3 -m json.tool
   curl -s http://localhost:80
   ```

## Commandes utiles

```bash
# Voir les logs en temps réel
docker-compose logs -f

# Redémarrer un service sans rebuild
docker-compose restart backend

# Stopper la stack
docker-compose down

# Stopper et supprimer les volumes (reset BDD)
docker-compose down -v
```

## En cas d'erreur

- **Port déjà utilisé** : vérifier avec `ss -tlnp | grep 8000` ou `ss -tlnp | grep 80`
- **SQLite verrouillé** : un process local tourne encore — `docker-compose down` puis relancer
- **Selenium crash** : vérifier que le container backend a accès à Chrome (`--shm-size` dans docker-compose)
- **Bot ne se connecte pas au backend** : vérifier `BACKEND_URL=http://backend:8000` dans `.env` (nom du service docker, pas localhost)
