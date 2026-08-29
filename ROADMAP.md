# Roadmap — Portfolio Manager

Portfolio Manager is a Python command-line tool for creating, organizing, updating and maintaining Markdown files for a personal portfolio.

This roadmap describes the planned evolution of the project.

## V1 — Basic Markdown generation

**Status: complete**

Goal: automatically create structured Markdown files in the portfolio hierarchy.

Implemented features:

- `new` command
- Support for `project`, `lab`, `publication` and `reading` content types
- Automatic clean filename generation
- YAML front matter generation
- Markdown templates
- Basic domain and subdomain validation
- Automatic creation of missing directories
- Protection against overwriting existing files
- Project documentation
- GitHub repository publication workflow prepared

## V2 — Configurable portfolio root

**Status: complete**

Goal: allow the tool to write to the actual portfolio directory instead of a local test directory.

Implemented features:

- `config.json` configuration file
- Configurable `portfolio_root` path
- Configuration loading at startup
- Relative path resolution from the configuration file location
- Validation that the target portfolio exists
- Protection against writing to an invalid location

Example:

```json
{
  "portfolio_root": "../portfolio"
}
```

## V3 — Guided prompts and standard tags

Goal: improve the experience when creating new content.

Planned features:

- Display available domains before input
- Suggest subdomains based on the selected domain
- Suggest default tags based on the content type
- Support standard tag additions
- Ask for content status: `draft`, `in-progress` or `published`
- Provide sensible defaults for common fields

## V4 — Type-specific metadata

Goal: enrich files with metadata appropriate to their content type.

For projects:

- `repository`
- `demo`

For labs:

- `repository`
- `dataset`
- `diagram`

For publications:

- `pdf`
- `source_url`

For reading notes:

- `pdf`
- `author`
- `source_url`

The `skills` field remains optional and will only be added if it provides real value beyond tags.

## V5 — Updating existing files

Goal: update selected metadata without recreating the entire file.

Planned features:

- Change the content status
- Move content from `draft` to `published`
- Update tags
- Update fields such as `repository`, `demo` or `pdf`
- Preserve existing Markdown content

Possible command:

```bash
python portfolio_manager.py update-status path/to/file.md published
```

## V6 — Portfolio quality checks

Goal: keep the portfolio clean, consistent and standardized.

Possible command:

```bash
python portfolio_manager.py check
```

Potential checks:

- Front matter is present
- Title is present
- Content type is valid
- Date is present
- Status is valid
- Tags are present
- `status` and `draft` are consistent
- Referenced PDFs exist
- Published projects include a repository link
- Files are placed in the correct directory
- Filenames follow the naming convention

## V7 — Portfolio analysis and dashboard data

Goal: provide useful statistics about the portfolio.

Possible command:

```bash
python portfolio_manager.py stats
```

Potential statistics:

- Total number of content files
- Content by type
- Content by domain
- Content by status
- Most frequently used tags
- Published projects
- Projects in progress
- Publications with or without PDFs
- Incomplete content

The command could eventually generate data for the portfolio homepage:

```text
data/portfolio_stats.json
```

## V8 — Markdown index generation

Goal: generate index pages to improve portfolio navigation.

Possible command:

```bash
python portfolio_manager.py index
```

Planned features:

- Generate indexes by domain
- Generate indexes by subdomain
- Generate indexes by content type
- Create `_index.md` files
- List published content
- Optionally ignore drafts

## V9 — Hugo and GitHub Pages compatibility

Goal: prepare the portfolio for static-site publication.

Planned features:

- Hugo-compatible front matter
- `draft: true` or `draft: false`
- Improved metadata organization
- `_index.md` support
- Optional page bundles
- Pre-publication validation
- Homepage data generation

For publications or reading notes with PDFs, page bundles could use this structure:

```text
content/society/political-science/publications/example-publication/
├── index.md
└── example-publication.pdf
```

## V10 — Graphical interface

Goal: make the tool more accessible and comfortable to use.

Possible features:

- Content creation form
- Guided domain and subdomain selection
- Standard tag selection
- PDF attachment
- Status editing
- Selected metadata editing
- Opening existing Markdown files
- Basic preview

This version should come after the core CLI logic is stable.

## Development principles

- Move forward in small versions
- Keep the code readable
- Limit unnecessary dependencies
- Document every feature
- Test every command manually
- Keep commits clear and honest
- Prefer real-world usefulness over complexity
- Preserve compatibility with a future Hugo or GitHub Pages portfolio
