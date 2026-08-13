# Portfolio Manager

CLI Python pour générer des fiches Markdown structurées dans un portfolio.

## Installation

```bash
git clone https://github.com/TKonate/portfolio-manager.git
cd portfolio-manager
```

Configurez le chemin vers votre portfolio dans `config.json` :

```json
{
  "portfolio_root": "../portfolio"
}
```

## Utilisation

```bash
python portfolio_manager.py new publication
```

Le programme demande ensuite les informations de la fiche :

```
Title: Populations civiles et souverainetés fragmentées
Domain: society
Subdomain: political-science
Tags, separated by commas: sciences-politiques, osint, sahel
Date: 2026
```

La fiche est créée automatiquement dans le dossier configuré :

```
portfolio/content/society/political-science/publications/populations-civiles-et-souverainetes-fragmentees.md
```

## Types de contenus

| Type | Dossier de destination | Exemple |
|---|---|---|
| `project` | `projects/` | Projet technique |
| `lab` | `labs/` | Laboratoire / expérimentation |
| `publication` | `publications/` | Article, essai, analyse |
| `reading` | `reading/` | Note de lecture |

## Structure du projet

```
portfolio-manager/
├── config.json              # Configuration (chemin du portfolio)
├── portfolio_manager.py     # Point d'entrée CLI
├── templates.py             # Templates Markdown par type
├── .gitignore
└── README.md
```

## Fonctionnalités

- Génération automatique d'un nom de fichier (slug) à partir du titre
- Front matter YAML complet (title, type, date, tags, status)
- Templates Markdown adaptés à chaque type de contenu
- Validation des domaines et sous-domaines
- Création automatique des dossiers manquants
- Protection contre l'écrasement des fichiers existants
- Configuration via `config.json` (chemin du portfolio personnalisable)

## Roadmap

| Version | Fonctionnalités | Statut |
|---|---|---|
| V1 | Génération Markdown de base | ✅ Terminé |
| V2 | Configuration via `config.json` | ✅ Terminé |
| V3 | Prompts guidés et tags standards | ⏳ |
| V4 | Métadonnées avancées par type de contenu | ⏳ |
| V5 | Modification de fichiers existants | ⏳ |
| V6 | Vérification de qualité | ⏳ |
| V7 | Analyse de portfolio et tableau de bord | ⏳ |
| V8 | Génération d'index Markdown | ⏳ |
| V9 | Compatibilité Hugo / GitHub Pages | ⏳ |
| V10 | Interface graphique | 🔮 |

## Licence

MIT