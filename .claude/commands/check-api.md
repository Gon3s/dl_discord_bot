Vérifie que tous les endpoints du backend FastAPI répondent correctement.

## Prérequis

Le backend doit être lancé sur `:8000`. Si ce n'est pas le cas :
```bash
cd backend && uv run uvicorn app.main:app --reload --port 8000
```

## Étapes à suivre

1. **Health check de base** :
   ```bash
   curl -s http://localhost:8000/api/v1/status | python3 -m json.tool
   ```
   Vérifier : `queue_size`, `active_downloads`, `disk_free_gb`, `alldebrid_ok`

2. **Endpoint Search** :
   ```bash
   curl -s "http://localhost:8000/api/v1/search?q=inception&source=wawacity&category=films&limit=3" | python3 -m json.tool
   ```
   Vérifier : liste de résultats avec `title`, `year`, `quality`, `source_url`

3. **Endpoint Downloads — création** :
   ```bash
   curl -s -X POST http://localhost:8000/api/v1/downloads \
     -H "Content-Type: application/json" \
     -d '{"source_url": "https://test.example", "media_type": "movie", "destination": "server"}' \
     | python3 -m json.tool
   ```
   Vérifier : `download_id` (UUID) et `status: "queued"`

4. **Endpoint Downloads — liste** :
   ```bash
   curl -s "http://localhost:8000/api/v1/downloads" | python3 -m json.tool
   ```

5. **Endpoint History** :
   ```bash
   curl -s "http://localhost:8000/api/v1/history?page=1&limit=10" | python3 -m json.tool
   ```

6. **Endpoint Settings** :
   ```bash
   curl -s "http://localhost:8000/api/v1/settings" | python3 -m json.tool
   ```

7. **Source Darkiworld (doit retourner 501)** :
   ```bash
   curl -s "http://localhost:8000/api/v1/search?q=test&source=darkiworld&category=films" -w "\nHTTP %{http_code}\n"
   ```

8. **Documentation interactive** : ouvrir `http://localhost:8000/docs` et vérifier que tous les schémas sont bien définis.

## Rapport

Pour chaque endpoint, indiquer :
- ✅ Répond avec le bon code HTTP
- ✅ La structure JSON correspond aux schémas Pydantic de `backend/app/models/schemas.py`
- ❌ Tout écart ou erreur avec le détail

Si des erreurs sont trouvées, les corriger avant de valider.
