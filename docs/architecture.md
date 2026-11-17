# Architecture

Portfolio Manager is one package, `pfm`, with a single dependency direction:
`cli` and `server` are the entry points, everything else is a library module that knows nothing about
the terminal or HTTP.

```text
            cli.py                     server.py
              │                           │
              ├─────────► create ◄────────┤
              │             update        │
              │             check         │
              │             stats         │
              │             index ◄───────┘
              │             hugo
              ▼
        config ─ models ─ frontmatter ─ naming ─ validate
              │
            store  (disk access, safe ids)
```

## Modules

| Module | Responsibility |
|---|---|
| `models.py` | Vocabulary (content types, folders, statuses, metadata fields, canonical key order) and the `Entry` data class with its derived properties (type, status, tags, domain, draft). |
| `frontmatter.py` | YAML front matter reader/writer for the subset the portfolio uses: scalars, booleans, block and inline lists. `dumps` quotes only what YAML could misread, so files stay readable. |
| `naming.py` | Slug generation (accent folding, word-boundary truncation), tag normalisation, target path computation (flat file or page bundle). |
| `validate.py` | Field validation: title, date, status, type, URL, local path, type-specific fields. Raises `ValidationError` with actionable details. |
| `config.py` | `config.json` loading and validation, path resolution relative to the configuration file, `--config`/`--portfolio-root`/`$PFM_CONFIG` overrides. |
| `store.py` | Directory walking, entry parsing, atomic writes (temporary file + `os.replace`), and `resolve_entry_id`, the single place where an untrusted id becomes a path. |
| `create.py` | Draft validation, front matter assembly, template body, page-bundle creation and attachment copying. |
| `update.py` | Front matter updates that preserve the body and unknown keys; status/tags/fields handling; warnings. |
| `check.py` | Quality checks with stable codes (`E001`…`E014`, `W007`…`W016`) and a serialisable report. |
| `stats.py` | Aggregations and `data/portfolio_stats.json`. |
| `index.py` | `_index.md` generation at four levels, relative or Hugo links. |
| `hugo.py` | Normalisation (`draft` boolean, canonical order) and Hugo-specific validation. |
| `markdown.py` | Small Markdown → HTML renderer for the preview. Escapes HTML first, only allows `http(s)`, `mailto`, `#` and relative links. |
| `prompts.py` | Guided prompts and the interactive menu, written against injected `reader`/`writer` callables so they are testable. |
| `cli.py` | `argparse` definition, subcommand handlers, aliases, error-to-exit-code mapping, menu wiring. |
| `server.py` | `ThreadingHTTPServer` with a small JSON API, static assets, request validation and a write lock. |

## Data model

An entry is a Markdown file under:

```text
<portfolio>/content/<domain>/<subdomain>/<type folder>/<slug>.md
<portfolio>/content/<domain>/<subdomain>/<type folder>/<slug>/index.md   (page bundle)
```

Front matter keys, in canonical order:

`title`, `type`, `date`, `status`, `draft`, `tags`, `domain`, `subdomain`, then the type-specific
fields (`repository`, `demo`, `dataset`, `diagram`, `pdf`, `author`, `source_url`), then any
unknown key found in an existing file.

`status` is the source of truth; `draft` is always recomputed as `status != "published"` so Hugo and
the checks cannot disagree.

## Invariants

1. **Writes are atomic.** `store.write_entry` writes a temporary file in the target directory then
   renames it, so an interrupted run never truncates an entry.
2. **The body is never rewritten.** Updates only rebuild the front matter block.
3. **Paths are resolved, then checked.** `resolve_entry_id` rejects absolute paths, `..` segments,
   null bytes and symlinks escaping the root.
4. **Validation precedes writing.** `create_entry` builds and validates the whole document before
   touching the disk.
5. **Indexes are disposable.** `_index.md` files are regenerated; entries starting with `_` are
   never listed as content.

## Web API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Single-page UI |
| `GET` | `/api/meta` | Types, fields, statuses, domains, version |
| `GET` | `/api/entries?type=&status=&domain=&tag=&q=` | Entry list |
| `GET` | `/api/entries/<id>` | Entry metadata, raw Markdown and rendered HTML |
| `POST` | `/api/entries` | Create an entry |
| `PATCH` | `/api/entries/<id>` | Update metadata |
| `DELETE` | `/api/entries/<id>` | Delete an entry |
| `GET` | `/api/stats` | Statistics |
| `POST` | `/api/stats` | Write `data/portfolio_stats.json` |
| `POST` | `/api/check` | Run the checks |
| `POST` | `/api/index` | Regenerate the indexes |
| `POST` | `/api/hugo` | Normalise for Hugo and report |

Errors are `{"error": {"message": ..., "details": [...]}}` with a matching HTTP status
(400 validation, 403 origin/host, 404 missing, 409 conflict, 415 media type).

Security: loopback bind by default, `Host` restricted to loopback names, `Origin` must match,
writes require `application/json`, bodies limited to 1 MiB, only four static assets are served.

## Testing strategy

- Every module has unit tests; `frontmatter`, `naming`, `validate` and `update` are pure functions.
- CLI tests run `pfm.cli.main` in-process with a temporary portfolio and capture exit code/stdout.
- The server is tested over real HTTP against an ephemeral port: creation, update, deletion,
  traversal attempts, cross-origin and DNS-rebinding refusals.
- The demo portfolio is generated by the tool itself, which acts as an integration test: `check`
  must report zero errors and zero warnings on it.
