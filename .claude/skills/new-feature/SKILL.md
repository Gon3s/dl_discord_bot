---
name: new-feature
description: Scaffolde une tranche verticale complète sur DLux (endpoint FastAPI + schéma Pydantic + migration éventuelle + feature Angular standalone). À utiliser quand l'utilisateur veut ajouter une nouvelle fonctionnalité de bout en bout, calquée sur les features existantes (favorites, notifications, history…).
---

# new-feature

Crée une fonctionnalité de bout en bout en suivant le moule des features
existantes. NE PAS inventer de pattern : copier celui de la feature la plus
proche (`favorites` = CRUD simple, `notifications` = CRUD + scheduler,
`history` = lecture/suppression).

## 1. Cadrage (avant de coder)

- Nommer la ressource + les opérations (GET/POST/PATCH/DELETE).
- Choisir la feature modèle à imiter.
- Lister les critères de succès vérifiables.

## 2. Backend

1. **ORM** — ajouter le modèle dans `backend/app/models/orm.py` (si persistance).
2. **Migration** — utiliser le skill `db-migrate` (si l'ORM a changé).
3. **Schémas** — `…Create` / `…Read` / `…Patch` dans `backend/app/models/schemas.py`.
4. **Router** — `backend/app/api/v1/<feature>.py` (calqué sur `favorites.py`),
   puis l'inclure dans `backend/app/api/v1/router.py`.
5. **Service** — `backend/app/services/` si logique non triviale.
6. **Tests** — ajouter `backend/tests/test_<feature>.py`.

## 3. Frontend

1. **Modèle** — `frontend/src/app/core/models/<feature>.type.ts` (+ export `index.ts`).
2. **Service** — méthodes dans `api.service.ts` (jamais de `HttpClient` direct
   en composant) ; service dédié si état partagé (cf. `favorite.service.ts`).
3. **Feature** — `frontend/src/app/features/<feature>/` : composant standalone
   + routes. `signal()`/`computed()` pour l'état, `inject()`, `takeUntilDestroyed()`.
4. **Sidebar** — ajouter l'entrée de nav si pertinent (`shared/components/sidebar`).

## 4. Vérification

- `run-tests` (backend) puis `quality-gate` (lint + build).
- Mettre à jour `CLAUDE.md` : section endpoints API + table "Fichiers importants".

## Critère de succès

Endpoint répond (cf. `api-smoke`), feature affichée dans le frontend buildé,
tests verts, docs à jour.
