---
name: run-tests
description: Lance la suite de tests pytest du backend DLux. Argument optionnel = cible ou flags (ex: "tests/test_models.py", "-k test_create", "-v"). À utiliser quand l'utilisateur demande de lancer/relancer les tests ou de vérifier qu'un changement backend ne casse rien.
---

# run-tests

Suite de tests du backend FastAPI (`backend/tests/`, ~12 fichiers).
Config : `asyncio_mode = "auto"`, `testpaths = ["tests"]`.

## Étapes

```bash
cd backend
uv run pytest $ARGUMENTS
```

- Sans argument : lance toute la suite.
- Avec argument : passe `$ARGUMENTS` tel quel à pytest (cible de fichier, `-k`, `-v`, etc.).

## Critère de succès

Sortie pytest `passed` sans `failed`/`error`. En cas d'échec : rapporter le nom
du test et la trace exacte, sans tenter de corriger sauf demande explicite.
