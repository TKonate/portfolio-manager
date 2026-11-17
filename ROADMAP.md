# Roadmap — Portfolio Manager

Portfolio Manager is a Python command-line tool for creating, organising, updating and maintaining
Markdown files for a personal portfolio.

This roadmap describes the planned evolution of the project. Everything up to V10 is implemented in
version `1.0.0`.

## V1 — Basic Markdown generation

**Status: complete**

- `new` command
- Support for `project`, `lab`, `publication` and `reading` content types
- Automatic clean filename generation
- YAML front matter generation
- Markdown templates
- Domain and subdomain validation
- Automatic creation of missing directories
- Protection against overwriting existing files

## V2 — Configurable portfolio root

**Status: complete**

- `config.json` configuration file
- Configurable `portfolio_root` path
- Resolution relative to the configuration file, not the current directory
- `--config` and `--portfolio-root` overrides
- Validation that the target portfolio exists and is a directory

## V3 — Guided prompts and standard tags

**Status: complete**

- Numbered menu for the content type, domain and subdomain (the value can also be typed)
- Subdomains suggested from the selected domain
- Default tags suggested from the type, domain and subdomain, plus `default_tags` from the config
- Status prompt: `draft`, `in-progress` or `published`
- Interactive menu when `pfm` is run without a command
- `--no-input` mode for scripting

## V4 — Type-specific metadata

**Status: complete**

- Projects: `repository`, `demo`
- Labs: `repository`, `dataset`, `diagram`
- Publications: `pdf`, `source_url`
- Reading notes: `pdf`, `author`, `source_url`
- URLs validated, paths kept inside the portfolio
- Unknown fields refused on update, empty values remove the key

## V5 — Updating existing files

**Status: complete**

- Change the status (and keep `draft` consistent)
- Change the title and the date
- Replace, add or remove tags
- Set or remove type-specific fields
- Preserve the Markdown body and hand-written front matter keys
- `--dry-run` to preview a change
- `update-status` shortcut

## V6 — Portfolio quality checks

**Status: complete**

- Front matter present and parseable
- Title, date, status and type present and valid
- `draft` consistent with `status`
- Tags present (warning)
- Referenced PDF exists
- Published projects include a repository URL (warning)
- File placed in `content/<domain>/<subdomain>/<type>/`
- Domain and subdomain matching the directory (warning when undeclared)
- Filename follows the slug convention
- Duplicate titles detected
- Stable codes, `--json`, `--strict`, exit code `1` on failure

## V7 — Portfolio analysis and dashboard data

**Status: complete**

- `stats` command: totals by type, status, domain and subdomain
- Most used tags
- Published projects and projects in progress
- Publications with and without PDF
- Drafts and incomplete entries
- `--json` output and `data/portfolio_stats.json` for the homepage

## V8 — Markdown index generation

**Status: complete**

- `index` command generating `_index.md` at four levels (portfolio, domain, subdomain, type)
- Relative links (GitHub / Obsidian) or Hugo pretty URLs
- Drafts listed with a marker, or excluded with `--no-drafts`
- Generated files carry a marker and are excluded from the entry listing

## V9 — Hugo and GitHub Pages compatibility

**Status: complete**

- Hugo-compatible front matter with a boolean `draft`
- Unquoted ISO dates so Hugo parses them
- `_index.md` support and optional page bundles (`<slug>/index.md`)
- PDF and diagram attached inside the bundle
- `hugo` command: validation report and in-place normalisation (`--apply`)
- Pre-publication validation (types, titles, dates, draft flag, bundle attachments)
- Homepage data generation through `stats --write`

## V10 — Graphical interface

**Status: complete**

- Local web UI (`pfm serve`) built with the standard library only
- Creation form with guided domain/subdomain selection and type-specific fields
- Entry list with search and filters, metadata table and rendered preview
- Status editing, metadata editing, deletion
- Statistics, homepage JSON, quality checks and index regeneration from the UI
- Loopback-only server, cross-origin and DNS-rebinding protection, path traversal refused
- End-to-end tests over real HTTP in CI

A native desktop interface (Tkinter) is not planned: the web UI already covers the use case and
stays testable on a headless machine.

## Beyond 1.0

Not scheduled, listed for honesty:

- Move or rename an entry from the CLI (`pfm move`)
- Import an existing tree and infer missing front matter
- Optional full CommonMark preview
- Per-section `hugo.toml` generation

## Development principles

- Move forward in small versions
- Keep the code readable and commented
- Limit unnecessary dependencies (currently: none)
- Document every feature
- Test every command, including failure paths
- Keep commits clear and honest
- Prefer real-world usefulness over complexity
- Preserve compatibility with a future Hugo or GitHub Pages portfolio
