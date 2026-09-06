# TODO - DLux v2

Cette liste est la roadmap technique versionnée du projet. Les issues GitHub
peuvent détailler l'exécution, mais ce fichier conserve les priorités communes aux
humains, à Codex et à Claude Code.

## P0 - Sécurité avant exposition publique

- [x] Valider `source_url` et `alternative_urls` : protocoles autorisés, nombre et
  taille maximum, rejet de `localhost` et des adresses IP locales ou réservées.
- [x] Remplacer les chaînes libres de `media_type`, `status` et `source` par des
  types ou enums partagés.
- [ ] Ajouter des limites de requêtes et de taille de file pour empêcher le spam,
  l'épuisement du quota debrid et le remplissage du disque.
- [ ] Restreindre `PUT /settings` à une liste de clés et valider chaque valeur.
- [ ] Documenter que les clés debrid persistées sont stockées en clair dans SQLite,
  puis décider si elles doivent rester uniquement dans l'environnement.

## P1 - Fiabilité des téléchargements

- [x] Implémenter une vraie annulation : état `cancelled`, retrait logique de la
  file, interruption du worker et nettoyage du fichier partiel.
- [ ] Télécharger vers un fichier `.part`, contrôler la taille lorsqu'elle est
  connue, puis effectuer un renommage atomique.
- [ ] Au démarrage, remettre en file les états transitoires `scraping`, `resolving`,
  `debriding` et `downloading`, pas seulement `queued`.
- [ ] Empêcher l'écrasement silencieux d'un fichier final existant.
- [ ] Définir le comportement en cas d'espace disque insuffisant avant et pendant
  un téléchargement.
- [ ] Faire appliquer immédiatement une modification de
  `max_concurrent_downloads`, ou indiquer clairement qu'un redémarrage est requis.

## P1 - Données et migrations

- [ ] Exécuter `alembic upgrade head` au déploiement et retirer
  `Base.metadata.create_all()` du chemin de production.
- [ ] Remplacer `alternative_urls` encodé en JSON dans une colonne texte par un
  type explicite ou une table associée si les usages augmentent.
- [ ] Ajouter les index utiles sur les statuts et dates consultés fréquemment.
- [ ] Définir une politique de conservation des téléchargements terminés et de
  l'historique.

## P1 - Veille des séries

- [ ] Identifier les épisodes par numéro ou URL au lieu de déduire les nouveautés
  depuis le seul nombre total d'épisodes.
- [ ] Gérer les suppressions, renumérotations et changements d'ordre de la source.
- [ ] Ajouter un verrou pour empêcher deux vérifications simultanées du scheduler.
- [ ] Authentifier le serveur interne de notification du bot ou limiter strictement
  son exposition au réseau Docker.

## P2 - Tests et qualité

- [ ] Ajouter des tests frontend sur les parcours recherche, lancement, annulation,
  reprise WebSocket et modification des paramètres.
- [ ] Ajouter des tests d'intégration pour interruption et reprise d'un fichier
  partiel.
- [ ] Tester les URL malveillantes, les noms de fichiers hostiles et les limites de
  requêtes.
- [ ] Corriger le badge du README pour ne plus coder en dur le nombre de tests.
- [ ] Ajouter le lint et les tests du bot à la CI.
- [ ] Tester les migrations Alembic sur une base vierge et sur une base de la
  version précédente.

## P2 - Exploitation et déploiement

- [ ] Décider si les URL de téléchargement doivent utiliser une liste d'hôtes
  autorisés ou une résolution DNS protégée contre le rebinding.
- [ ] Remplacer le chemin hôte `/home/gones/moovies` par une variable documentée
  ou un volume portable.
- [ ] Utiliser des tags d'image immuables pour les déploiements, avec une procédure
  explicite de rollback.
- [ ] Ajouter des healthchecks Docker pour le backend et le bot.
- [ ] Ajouter des logs structurés et une rotation des journaux.
- [ ] Sauvegarder régulièrement SQLite et tester la restauration.
- [ ] Documenter qu'une seule instance backend est supportée tant que la file et
  le bus d'événements restent en mémoire.

## P3 - Maintenabilité

- [ ] Centraliser les listes de fournisseurs et leurs priorités actuellement
  répétées dans le backend et le frontend.
- [ ] Distinguer les erreurs temporaires de scraping/debrid des erreurs définitives
  afin d'appliquer une politique de retry bornée.
- [ ] Mettre à jour les diagrammes de `docs/architecture-v2.md` lorsqu'un flux ou
  un modèle persistant change.
- [ ] Évaluer l'ajout d'un second scraper uniquement lorsqu'une source concrète
  doit être supportée.

## Décisions prises

- [x] Conserver la roadmap principale dans le dépôt afin qu'elle soit versionnée
  avec le code et disponible hors ligne.
- [x] Garder `CLAUDE.md` comme source de vérité commune et utiliser `AGENTS.md`
  comme point d'entrée Codex.
- [x] Installer les skills Caveman localement dans `.agents/skills/`.
- [x] Activer les instructions RTK locales via `RTK.md`.
