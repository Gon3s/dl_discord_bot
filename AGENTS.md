# AGENTS.md - DLux v2

Ce fichier est le point d'entrée des agents Codex pour tout le dépôt.

## Instructions du projet

Lire entièrement [`CLAUDE.md`](./CLAUDE.md) avant toute modification. Ce fichier
reste la source de vérité partagée pour la présentation, l'architecture, les
commandes et les conventions de code. Son nom historique ne limite pas son usage
à Claude Code.

Ne pas dupliquer ces instructions dans `AGENTS.md`. Toute nouvelle convention
commune doit être ajoutée dans `CLAUDE.md`.

## Suivi du travail

Consulter [`TODO.md`](./TODO.md) avant une évolution importante. Mettre à jour la
case et les notes associées lorsqu'une tâche de cette liste est terminée.

## Outils Codex

Lire [`RTK.md`](./RTK.md) et utiliser RTK pour compacter les sorties des commandes
prises en charge. Si RTK ne prend pas correctement en charge une commande, lancer
la commande normalement plutôt que de bloquer le travail.

Les skills locales, dont Caveman, vivent dans `.agents/skills/`. Ne pas activer
le mode Caveman automatiquement : l'utiliser uniquement lorsque l'utilisateur le
demande explicitement avec `/caveman` ou une formulation équivalente.

@RTK.md
