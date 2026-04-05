Finalise le travail sur une issue : met à jour la documentation, ferme l'issue et ouvre la PR. Arguments : `$ARGUMENTS` (numéro de l'issue, ex: `65`).

## Étapes à suivre

### 1. Tests

```bash
cd backend && uv run pytest --tb=short -q
```

Arrêter si des tests échouent — corriger avant de continuer.

### 2. Mise à jour de la documentation

Passer en revue les changements (`git diff main`) et mettre à jour ce qui est impacté :

- **`CLAUDE.md`** — nouveaux endpoints API, conventions, fichiers importants
- **`docs/architecture-v2.md`** — diagrammes si le flux de données a changé
- **`README.md`** — si le démarrage ou les commandes ont changé

Ne documenter que ce qui est **non évident depuis le code**. Commit les docs si modifiées.

### 3. Build frontend (si des fichiers `frontend/` ont changé)

```bash
cd frontend && ng build --configuration production
```

Vérifier qu'il n'y a pas d'erreurs de compilation TypeScript.

### 4. Commit final

Si des fichiers sont encore non commités :

```bash
git add <fichiers>
git commit -m "docs: mise à jour documentation issue #$ARGUMENTS"
git push
```

### 5. Ouverture de la PR

```bash
gh pr create \
  --title "<titre court>" \
  --body "$(cat <<'EOF'
## Résumé
- <bullet point>

## Test plan
- [ ] <étape de test>

Closes #$ARGUMENTS

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

La description doit contenir **`Closes #$ARGUMENTS`** pour fermer l'issue automatiquement au merge.

### 6. Confirmer

Afficher l'URL de la PR et rappeler à l'utilisateur d'attendre la revue avant de merger.

## Checklist avant PR

- [ ] Tests passent
- [ ] `CLAUDE.md` à jour (endpoints, conventions)
- [ ] Pas de `console.log`, `print()`, ou code de debug laissé
- [ ] Pas de credentials ou secrets dans le code
- [ ] `Closes #N` présent dans la description de la PR
