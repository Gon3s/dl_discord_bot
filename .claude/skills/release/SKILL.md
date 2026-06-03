---
name: release
description: Pilote le workflow d'une issue DLux de bout en bout — création de branche, implémentation, PR, attente de review, puis déploiement après merge. À utiliser quand l'utilisateur dit "commence l'issue N", "ouvre la PR", ou "déploie". Argument = numéro d'issue (+ nom court optionnel).
---

# release

Workflow Git/PR/déploiement de DLux. Remplace les anciennes commandes
start-issue / finish-issue / deploy. Suivre la phase correspondant à l'état actuel.

## Phase 1 — Démarrer (branche)

```bash
git checkout main && git pull
git checkout -b feat/<numero>-<nom-court>
```
`<nom-court>` = slug kebab dérivé du titre de l'issue.

## Phase 2 — Implémenter

Coder la fonctionnalité (utiliser `new-feature` / `add-scraper` / `db-migrate`
selon le cas). Avant de finaliser :

- `run-tests` → suite backend verte.
- `quality-gate` → lint + build OK.

## Phase 3 — PR

```bash
git add -A
git commit -m "<type>: <résumé>

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
git push -u origin HEAD
gh pr create --fill
```
- Mettre à jour `CLAUDE.md` (endpoints / fichiers) si l'API ou la structure a changé.
- Lier l'issue dans le corps de la PR (`Closes #<numero>`).
- Terminer le corps de PR par :
  `🤖 Generated with [Claude Code](https://claude.com/claude-code)`

## Phase 4 — Attendre

**Ne pas merger.** Attendre la revue et la validation explicite de l'utilisateur.

## Phase 5 — Déployer (après merge)

Production systemd :
```bash
git checkout main && git pull
# si le frontend a changé :
cd frontend && npx ng build --configuration production && cd ..
# si l'ORM a changé : migration (cf. db-migrate)
sudo systemctl restart dl_backend.service discord_bot.service
```
Production Docker/Portainer : Stack → **"Pull and redeploy"** après le rebuild des
images par GitHub Actions (~10 min).

## Critère de succès

Branche depuis `main` à jour, CI verte, PR ouverte et liée à l'issue. Déploiement
seulement après merge validé ; vérifier le statut des services
(`systemctl status dl_backend discord_bot`).
