Démarre le travail sur une issue GitHub. Arguments : `$ARGUMENTS` (ex: `42 add-darkiworld-scraper`).

## Étapes à suivre

1. **Parser les arguments** — `$ARGUMENTS` doit être de la forme `{numero} {nom}` :
   - Numéro : entier (ex: `42`)
   - Nom : slug kebab-case décrivant l'issue (ex: `add-darkiworld-scraper`)
   - Branche cible : `feat/{numero}-{nom}`

2. **S'assurer d'être sur la branche principale à jour** :
   ```bash
   git checkout v2
   git pull origin v2
   ```

3. **Créer et basculer sur la branche de feature** :
   ```bash
   git checkout -b feat/{numero}-{nom}
   ```

4. **Confirmer** à l'utilisateur :
   - Nom de la branche créée
   - Issue associée (lien GitHub si possible)
   - Rappel du workflow : travail → commits → `/deploy` ou skill adapté → PR

## Conventions

- Le nom de branche doit être en kebab-case, en anglais, court et descriptif
- Toujours partir de `v2` (branche de développement principale)
- Une branche = une issue
- Ne pas commencer à implémenter quoi que ce soit dans cette commande — se contenter de créer la branche
