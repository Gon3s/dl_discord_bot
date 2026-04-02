Crée et applique une migration Alembic pour le backend. Description de la migration : `$ARGUMENTS`.

## Étapes à suivre

1. **Vérifier l'état actuel** de la BDD et des modèles :
   - Lire `backend/app/models/orm.py` pour comprendre les tables existantes
   - Lire les migrations existantes dans `backend/alembic/versions/` pour éviter les conflits
   - Vérifier que le backend n'est pas en cours d'exécution (peut verrouiller SQLite)

2. **Générer la migration automatiquement** depuis `backend/` :
   ```bash
   cd backend
   uv run alembic revision --autogenerate -m "$ARGUMENTS"
   ```

3. **Lire et valider** le fichier de migration généré dans `backend/alembic/versions/` :
   - Vérifier que les colonnes `upgrade()` correspondent bien aux changements de `orm.py`
   - Vérifier que `downgrade()` est correct et réversible
   - Corriger manuellement si Alembic a manqué des changements (renommages, contraintes)

4. **Appliquer la migration** :
   ```bash
   cd backend
   uv run alembic upgrade head
   ```

5. **Vérifier** que la migration s'est bien appliquée :
   ```bash
   cd backend
   uv run alembic current
   ```

6. **Ouvrir une Pull Request** vers `v2` si la migration fait partie d'une issue :
   ```bash
   gh pr create --base v2 --title "feat: <description>" \
     --body "$(cat <<'EOF'
   ## Summary
   - Adds Alembic migration: `$ARGUMENTS`

   ## Test plan
   - [ ] `uv run alembic current` affiche la bonne révision
   - [ ] `uv run pytest --tb=short -q` passe

   🤖 Generated with [Claude Code](https://claude.com/claude-code)
   EOF
   )"
   ```
   Retourner l'URL de la PR à l'utilisateur et **attendre sa validation** avant de merger.

## En cas d'erreur

- Si migration en conflit : `uv run alembic merge heads -m "merge"`
- Pour rollback : `uv run alembic downgrade -1`
- Pour voir l'historique : `uv run alembic history --verbose`

## Conventions

- Message de migration en anglais, descriptif : `add_quality_column_to_downloads`, `create_settings_table`
- Ne jamais modifier une migration déjà appliquée en production — toujours créer une nouvelle
- Les colonnes ajoutées doivent avoir une valeur `server_default` si la table n'est pas vide
