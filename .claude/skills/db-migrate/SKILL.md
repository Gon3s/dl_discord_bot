---
name: db-migrate
description: Crée et applique une migration Alembic pour le backend DLux après un changement des modèles ORM. Argument = description de la migration. À utiliser quand l'utilisateur modifie backend/app/models/orm.py ou demande "crée une migration".
---

# db-migrate

Génère une migration Alembic à partir des modèles ORM modifiés
(`backend/app/models/orm.py`) puis l'applique.

## Prérequis

- Changement déjà fait dans `backend/app/models/orm.py`.
- `$ARGUMENTS` = description courte (ex: `add discord_notify to notifications`).

## Étapes

```bash
cd backend

# 1. Autogénérer la migration
uv run alembic revision --autogenerate -m "$ARGUMENTS"

# 2. RELIRE le fichier généré dans alembic/versions/
#    Alembic ne détecte pas tout (renommages, contraintes) → vérifier
#    upgrade()/downgrade() à la main.

# 3. Appliquer
uv run alembic upgrade head
```

Rollback si besoin : `uv run alembic downgrade -1`.

## Critère de succès

Nouveau fichier dans `alembic/versions/`, relu et cohérent avec le diff ORM, et
`upgrade head` sans erreur. Signaler le nom du fichier généré.
