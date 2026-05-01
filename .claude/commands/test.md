Lance la suite de tests du backend. Argument optionnel : `$ARGUMENTS` (ex: `tests/test_models.py`, `-k test_create`, `-v`).

## Étapes à suivre

1. **Lancer Ruff puis pytest** depuis `backend/` :
   ```bash
   cd backend
   uv run ruff check
   uv run pytest $ARGUMENTS --tb=short -q
   ```

2. **Analyser les résultats** :
   - ✅ Tous les tests passent → indiquer le nombre et la durée
   - ❌ Des tests échouent → lire le traceback, identifier la cause, corriger le code (pas les tests sauf si le test est faux), relancer

3. **Si un test échoue suite à un changement de code** :
   - Vérifier que le comportement attendu dans le test est toujours correct
   - Si oui : corriger le code pour que le test passe
   - Si non (le test est obsolète) : mettre à jour le test ET expliquer pourquoi le comportement a changé

## Conventions

- Le lint doit rester vert : `uv run ruff check`
- Les tests utilisent une BDD SQLite in-memory — pas de dépendance à `.env` ni au serveur
- `conftest.py` fournit les fixtures `db_session` et `client` (AsyncClient FastAPI)
- Ajouter un test pour chaque nouveau comportement ajouté (ORM, schéma, endpoint)
- Un test = une assertion précise, pas de tests fourre-tout
