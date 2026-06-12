# Portfolio Manager

Portfolio Manager est un outil en ligne de commande écrit en Python.

Il permet de créer automatiquement des fichiers Markdown structurés pour organiser un portfolio personnel.

## Objectif du projet

Ce projet a été développé pour apprendre à concevoir proprement un petit outil Python utile, maintenable et documenté.

L'objectif principal est d'automatiser la création de fiches Markdown dans une arborescence de portfolio organisée par domaines, sous-domaines et types de contenus.

## Fonctionnalités de la V1

* Création d'un fichier Markdown depuis le terminal
* Génération automatique d'un nom de fichier propre
* Génération d'un front matter YAML
* Utilisation de templates selon le type de contenu
* Création automatique des dossiers nécessaires
* Protection contre l'écrasement d'un fichier existant
* Validation simple des domaines et sous-domaines

## Types de contenus supportés

* `project`
* `lab`
* `publication`
* `reading`

## Exemple d'utilisation

```bash
python portfolio_manager.py new publication
```

Le programme demande ensuite :

```text
Title:
Domain:
Subdomain:
Tags, separated by commas:
Date:
```

Exemple :

```text
Title: Populations civiles et souverainetés fragmentées
Domain: society
Subdomain: political-science
Tags, separated by commas: sciences-politiques, osint, sahel
Date: 2026
```

Le programme génère alors un fichier comme :

```text
portfolio/content/society/political-science/publications/populations-civiles-et-souverainetes-fragmentees.md
```

## Domaines supportés

```text
technology/
├── computer-science
└── electronics

security/
├── cybersecurity
└── osint

society/
├── political-science
└── sociology

interdisciplinary/
└── general
```

## Exemple de fichier généré

```markdown
---
title: "Populations civiles et souverainetés fragmentées"
type: "publication"
date: 2026
tags:
  - sciences-politiques
  - osint
  - sahel
status: "draft"
---

# Populations civiles et souverainetés fragmentées

## Résumé

## Objectif

## Méthodologie

## Compétences mobilisées

## Sources et références
```

## Technologies utilisées

* Python
* Bibliothèque standard Python
* `argparse`
* `pathlib`
* `re`
* `unicodedata`
* Git et GitHub

## Structure du projet

```text
portfolio-manager/
├── README.md
├── portfolio_manager.py
├── templates.py
└── .gitignore
```

## Compétences travaillées

* Création d'un outil CLI
* Manipulation de fichiers avec Python
* Génération de contenu Markdown
* Organisation d'un petit projet logiciel
* Validation d'entrées utilisateur
* Utilisation de Git et GitHub
* Documentation technique

## Améliorations possibles

* Ajouter une commande `stats`
* Générer automatiquement des index Markdown
* Ajouter un fichier de configuration
* Permettre de choisir le chemin du portfolio
* Ajouter des tests unitaires
* Améliorer la gestion des erreurs
* Publier le projet comme package Python installable
