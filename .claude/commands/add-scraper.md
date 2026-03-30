Scaffolde un nouveau scraper pour la source de données `$ARGUMENTS`.

## Étapes à suivre

1. **Lire les fichiers de référence** avant de créer quoi que ce soit :
   - `backend/app/scrapers/base.py` — interface `BaseScraper`, dataclasses `SearchResult` et `ProviderLinks`, décorateur `@register`
   - `backend/app/scrapers/wawacity.py` — implémentation de référence complète
   - `backend/app/scrapers/darkiworld.py` — exemple de stub

2. **Créer** `backend/app/scrapers/<source_name>.py` avec :
   - Classe héritant de `BaseScraper` avec `@register`
   - `source_name = "<source_name>"` (slug minuscule, utilisé comme valeur du param `?source=`)
   - Méthode `search(query, category, year, limit) -> list[SearchResult]`
   - Méthode `get_provider_links(url, providers) -> list[ProviderLinks]`
   - Si la source n'est pas encore implémentée : `raise NotImplementedError("source_name: not implemented yet")`

3. **Vérifier** que le scraper est auto-enregistré :
   - Chercher dans `backend/app/scrapers/__init__.py` si le module est bien importé
   - Ajouter l'import si nécessaire pour que `@register` s'exécute au démarrage

4. **Ajouter les tests** dans `backend/tests/test_scrapers.py` (créer si absent) :
   - Si stub : tester que `search()` lève bien `NotImplementedError`
   - Si implémenté : tester la structure des `SearchResult` retournés (mocker les appels réseau)

5. **Lancer les tests** pour valider :
   ```bash
   cd backend && uv run pytest tests/test_scrapers.py -v
   ```

6. **Tester** manuellement l'endpoint (si le backend tourne) :
   - `GET /api/v1/search?q=test&source=<source_name>&category=films`
   - Si stub : doit retourner `501 Not Implemented` avec message clair
   - Si implémenté : doit retourner une liste de `SearchResult`

7. **Mettre à jour** `CLAUDE.md` section "Sources actuelles" avec le nouvel entry.

## Conventions importantes

- Tous les appels HTTP dans le scraper utilisent `aiohttp` (pas `requests`)
- Les appels Selenium (bloquants) sont wrappés dans `run_in_executor`
- Pas de logique de debrid dans le scraper — uniquement extraction des liens protégés
- Logger les erreurs avec `logging.getLogger(__name__)`, pas de `print()`
