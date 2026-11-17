# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [1.0.0] — 2026-11-17

Complete implementation of roadmap V3 to V10. The tool is now a package (`pfm`) with 278 tests,
enforced linting and type checking; `python portfolio_manager.py ...` keeps working.

### Added

- **Guided creation**: numbered prompts for the content type, domain and subdomain, suggested tags,
  status selection, and an interactive menu when the CLI is started without arguments (`V3`).
- **Type-specific metadata**: `repository`, `demo`, `dataset`, `diagram`, `pdf`, `author` and
  `source_url`, with URL and path validation (`V4`).
- **`update` command**: status, title, date, tags and metadata, body preserved, unknown keys kept,
  `--dry-run`, and an `update-status` shortcut (`V5`).
- **`check` command**: thirteen front matter, path and consistency checks with stable codes,
  `--json`, `--strict` and a meaningful exit code (`V6`).
- **`stats` command**: counts by type, status, domain and subdomain, top tags, published projects,
  publications with and without PDF, drafts, incomplete entries, `--json` and
  `data/portfolio_stats.json` (`V7`).
- **`index` command**: `_index.md` generation at portfolio, domain, subdomain and type level, with
  relative or Hugo links, draft filtering and `--dry-run` (`V8`).
- **Hugo support**: boolean `draft`, unquoted ISO dates, page bundles with attached PDF/diagram,
  `pfm hugo` validation and in-place normalisation, generated homepage data (`V9`).
- **Local web UI** (`pfm serve`): entry browser with search and filters, metadata editor, status
  switching, deletion, creation form, rendered preview, statistics, checks and index regeneration.
  Standard library only, loopback-only, cross-origin and DNS-rebinding protection, path traversal
  refused, end-to-end HTTP tests (`V10`).
- **`init` command** to bootstrap a portfolio skeleton and a `config.json`.
- **`list` and `show` commands** with filters, JSON output and safe entry-id resolution.
- **Demo portfolio** in `examples/` with six entries, a page bundle and a generator script.
- **Makefile**, `CHANGELOG.md`, `docs/architecture.md` and a screenshot of the web UI.

### Changed

- The single script became a package: `pfm/models.py`, `config.py`, `frontmatter.py`, `naming.py`,
  `validate.py`, `store.py`, `create.py`, `update.py`, `check.py`, `stats.py`, `index.py`,
  `hugo.py`, `markdown.py`, `prompts.py`, `server.py`, `templates.py`, `cli.py`.
- Front matter now records `domain`, `subdomain` and a boolean `draft`; the body is separated from
  the front matter by one blank line.
- `config.json` accepts optional `domains` and `default_tags`; relative paths are resolved from the
  configuration file, never from the current directory.
- Errors print a readable message with actionable details and return exit code `1` instead of a
  traceback.
- CI enforces `ruff check` and `mypy` (previously `ruff --exit-zero`) and runs the suite with
  coverage on Python 3.10 to 3.13.

### Fixed

- A missing `content/` directory is no longer fatal for write commands and is reported by `check`.
- Titles containing braces no longer crash the template rendering.
- Filenames are truncated on a word boundary, so long titles stay valid slugs.
- Tags are normalised (lowercase, spaces to dashes, deduplicated) instead of being written raw.

### Removed

- `templates.py` at the repository root (moved to `pfm/templates.py`).
- The old `validate_metadata` / `generate_front_matter` helpers, replaced by the package API.

## [0.2.0] — 2026-09-28

### Added

- `config.json` with a `portfolio_root` resolved relative to the configuration file.
- Validation of the configuration file and of the target directory.
- Unit tests for the configuration loader.

## [0.1.0] — 2026-08-10

### Added

- Initial CLI: `new <type>` creating a Markdown entry from a template.
- Slug generation, tag parsing, YAML front matter, domain and subdomain validation.
- Protection against overwriting an existing file.
