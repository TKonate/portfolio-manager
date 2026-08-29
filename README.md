# Portfolio Manager

A lightweight Python CLI for generating and organizing structured Markdown files for a personal portfolio.

## Installation

```bash
git clone https://github.com/TKonate/portfolio-manager.git
cd portfolio-manager
```

The project uses only the Python standard library at runtime. An editable installation is available for development:

```bash
pip install -e .
```

Configure the path to your portfolio in `config.json`:

```json
{
  "portfolio_root": "../portfolio"
}
```

Relative paths are resolved from the directory containing `config.json`.

## Usage

```bash
python portfolio_manager.py new publication
```

The program prompts for the content metadata:

```text
Title: Civilian populations and fragmented sovereignties
Domain: society
Subdomain: political-science
Tags, separated by commas: political-science, osint, sahel
Date: 2026
```

The Markdown file is generated in the configured portfolio directory:

```text
portfolio/content/society/political-science/publications/civilian-populations-and-fragmented-sovereignties.md
```

## Supported content types

| Type | Destination folder | Example |
|---|---|---|
| `project` | `projects/` | Technical project |
| `lab` | `labs/` | Experiment or lab |
| `publication` | `publications/` | Article or analysis |
| `reading` | `reading/` | Reading note |

## Features

- Automatic filename slug generation from the title
- YAML front matter with title, type, date, tags and status
- Markdown templates for each content type
- Domain and subdomain validation
- Automatic creation of missing directories
- Protection against overwriting existing files
- Configurable portfolio root through `config.json`
- Validation of malformed configuration values
- Automated tests with the Python standard library
- Continuous integration across supported Python versions

## Project structure

```text
portfolio-manager/
├── .github/workflows/ci.yml  # Continuous integration
├── config.json               # Portfolio path configuration
├── portfolio_manager.py      # CLI entry point and generation logic
├── pyproject.toml            # Packaging metadata
├── requirements.txt          # Runtime dependency declaration
├── templates.py              # Markdown templates
├── tests/                    # Automated tests
├── .gitignore
├── LICENSE
├── README.md
└── ROADMAP.md
```

## Development

Run the test suite with the Python standard library:

```bash
python3 -m unittest discover -v
```

Compile-check the Python files:

```bash
python3 -m py_compile portfolio_manager.py templates.py
```

If the development environment provides pytest and ruff, they can also be used:

```bash
pytest -v
ruff check .
```

## Roadmap

See [`ROADMAP.md`](ROADMAP.md) for the planned evolution of the project.

## License

MIT
