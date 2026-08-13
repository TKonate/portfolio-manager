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

| Type | Dossier | Exemple |
|---|---|---|
| `project` | `projects/` | Projet technique |
| `lab` | `labs/` | Laboratoire |
| `publication` | `publications/` | Article |
| `reading` | `reading/` | Note de lecture |

## Structure

```
portfolio-manager/
├── .github/workflows/ci.yml
├── config.json
├── portfolio_manager.py
├── pyproject.toml
├── requirements.txt
├── templates.py
├── tests/
├── LICENSE
├── README.md
└── ROADMAP.md
```

## Fonctionnalités

- Slug auto depuis le titre
- Front matter YAML complet
- Templates par type
- Validation domaines/sous-domaines
- Dossiers auto, protection écrasement
- Config via config.json
- Tests (pytest) + CI (3.10-3.13)
- Packaging pyproject.toml

## Roadmap

| Version | Fonctionnalités | Statut |
|---|---|---|
| V1 | Génération Markdown | ✅ |
| V2 | Config config.json | ✅ |
| V3 | Prompts guidés | ⏳ |
| V4 | Métadonnées avancées | ⏳ |
| V5 | Modification fichiers | ⏳ |
| V6 | Vérification qualité | ⏳ |
| V7 | Stats portfolio | ⏳ |
| V8 | Index Markdown | ⏳ |
| V9 | Hugo/GitHub Pages | ⏳ |
| V10 | Interface graphique | 🔮 |

## Développement

```bash
pytest -v
ruff check .
pip install -e .
```

## Licence

MIT