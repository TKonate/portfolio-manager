# Roadmap — Portfolio Manager

Portfolio Manager est un outil en ligne de commande développé en Python pour créer, organiser, modifier et maintenir les fichiers Markdown d’un portfolio personnel.

Cette roadmap décrit l’évolution prévue du projet.

## V1 — Génération Markdown simple

**Statut : terminée**

Objectif : créer automatiquement des fichiers Markdown structurés dans l’arborescence du portfolio.

Fonctionnalités réalisées :

* commande `new`
* prise en charge des types `project`, `lab`, `publication` et `reading`
* génération automatique d’un nom de fichier propre
* génération d’un front matter YAML
* utilisation de templates Markdown
* validation simple des domaines et sous-domaines
* création automatique des dossiers nécessaires
* protection contre l’écrasement d’un fichier existant
* documentation du projet
* publication du code sur GitHub

## V2 — Configuration du vrai portfolio

Objectif : permettre à l’outil d’écrire directement dans le vrai dossier du portfolio au lieu d’utiliser un dossier de test local.

Fonctionnalités prévues :

* ajouter un fichier `config.json`
* définir un chemin `portfolio_root`
* charger la configuration au lancement du programme
* utiliser le chemin configuré pour créer les fichiers Markdown
* vérifier que le dossier cible existe
* éviter les écritures accidentelles au mauvais endroit

Exemple de configuration :

```json
{
  "portfolio_root": "../portfolio"
}
```

## V3 — Prompts guidés et tags standards

Objectif : améliorer l’expérience utilisateur lors de la création d’un nouveau contenu.

Fonctionnalités prévues :

* afficher les domaines disponibles avant la saisie
* proposer les sous-domaines selon le domaine choisi
* proposer des tags par défaut selon le type de contenu
* permettre d’ajouter de nouveaux tags standards
* demander le statut du contenu : `draft`, `in-progress`, `published`
* proposer des valeurs par défaut pour certains champs

## V4 — Métadonnées avancées par type de contenu

Objectif : enrichir les fichiers Markdown avec des métadonnées adaptées à leur type.

Fonctionnalités prévues :

Pour les projets :

* `repository`
* `demo`

Pour les labs :

* `repository`
* `dataset`
* `diagram`

Pour les publications :

* `pdf`
* `source_url`

Pour les notes de lecture :

* `pdf`
* `author`
* `source_url`

Le champ `skills` reste une piste possible, mais il ne sera ajouté que s’il apporte une vraie valeur par rapport aux tags.

## V5 — Modification de fichiers existants

Objectif : permettre la modification de certaines métadonnées sans recréer entièrement un fichier Markdown.

Fonctionnalités prévues :

* changer le statut d’un contenu
* passer un contenu de `draft` à `published`
* modifier les tags
* modifier un champ comme `repository`, `demo` ou `pdf`
* préserver le contenu Markdown existant

Exemple de commande possible :

```bash
python portfolio_manager.py update-status path/to/file.md published
```

## V6 — Vérification de qualité

Objectif : maintenir le portfolio propre, cohérent et standardisé.

Commande envisagée :

```bash
python portfolio_manager.py check
```

Contrôles possibles :

* front matter présent
* titre présent
* type valide
* date présente
* statut valide
* tags présents
* cohérence entre `status` et `draft`
* fichier PDF indiqué mais absent
* dépôt GitHub manquant pour un projet publié
* fichier placé dans le bon dossier
* nom de fichier conforme

Cette fonctionnalité doit aider à éviter les erreurs de structure dans le portfolio.

## V7 — Analyse de portfolio et tableau de bord

Objectif : produire des statistiques utiles sur l’état du portfolio.

Commande envisagée :

```bash
python portfolio_manager.py stats
```

Statistiques possibles :

* nombre total de contenus
* contenus par type
* contenus par domaine
* contenus par statut
* tags les plus utilisés
* projets publiés
* projets en cours
* publications avec ou sans PDF
* contenus incomplets

À terme, cette commande pourra générer un fichier de données utilisable par la page d’accueil du portfolio.

Exemple :

```text
data/portfolio_stats.json
```

Ce fichier pourra servir à afficher automatiquement des indicateurs comme :

* nombre de projets publiés
* nombre de projets en cours
* nombre de labs techniques
* répartition par domaine

## V8 — Génération d’index Markdown

Objectif : générer automatiquement des pages d’index pour faciliter la navigation dans le portfolio.

Commande envisagée :

```bash
python portfolio_manager.py index
```

Fonctionnalités prévues :

* générer des index par domaine
* générer des index par sous-domaine
* générer des index par type de contenu
* créer des fichiers `_index.md`
* lister les contenus publiés
* ignorer les brouillons si nécessaire

Cette fonctionnalité sera particulièrement utile dans le cadre d’un site statique.

## V9 — Compatibilité Hugo / GitHub Pages

Objectif : préparer le portfolio pour une publication sous forme de site statique.

Fonctionnalités prévues :

* front matter compatible Hugo
* ajout du champ `draft: true` ou `draft: false`
* meilleure organisation des métadonnées
* support des fichiers `_index.md`
* support optionnel des page bundles
* vérification avant publication
* génération de données pour la page d’accueil

Pour les publications ou readings avec PDF, une structure de type page bundle pourra être utilisée :

```text
content/society/political-science/publications/example-publication/
├── index.md
└── example-publication.pdf
```

## V10 — Interface graphique

Objectif : rendre l’outil plus accessible et plus confortable à utiliser.

Fonctionnalités possibles :

* formulaire de création de contenu
* choix guidé du domaine et du sous-domaine
* sélection des tags standards
* ajout d’un PDF
* modification du statut
* modification de certaines métadonnées
* ouverture d’un fichier Markdown existant
* prévisualisation simple

Cette version viendra plus tard, lorsque la logique principale de la CLI sera stable.

## Principes de développement

Le projet doit rester progressif et maintenable.

Principes à respecter :

* avancer par petites versions
* garder un code lisible
* limiter les dépendances inutiles
* documenter chaque fonctionnalité
* tester chaque commande manuellement
* faire des commits clairs
* privilégier l’utilité réelle plutôt que la complexité
* garder une compatibilité avec un futur portfolio Hugo ou GitHub Pages

## Priorité actuelle

La prochaine étape de développement est la V2 :

```text
Configuration du vrai chemin du portfolio
```

Cette version permettra à Portfolio Manager de devenir réellement utilisable au quotidien, en créant directement les fichiers Markdown dans le vrai dépôt du portfolio.
