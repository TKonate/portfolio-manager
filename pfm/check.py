"""Portfolio quality checks (roadmap V6).

The checker walks every entry and reports *errors* (something is broken and
will produce a bad page) and *warnings* (something is incomplete but valid).
Each finding carries a stable code so it can be filtered or tested.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .config import Config
from .models import (
    CONTENT_FOLDERS,
    FOLDER_CONTENT_TYPES,
    STATUSES,
    TYPE_METADATA_FIELDS,
    Entry,
    is_valid_type,
)
from .naming import is_slug_filename
from .store import iter_entries_strict
from .validate import validate_date

ERROR = "error"
WARNING = "warning"

#: Statuses accepted before V3, kept valid for existing files.
_LEGACY_OK = True

_URLISH = re.compile(r"^https?://", re.IGNORECASE)


@dataclass(frozen=True)
class Issue:
    """One finding of the checker.

    Attributes:
        code: Stable identifier such as ``E003`` (error) or ``W007`` (warning).
        severity: ``error`` or ``warning``.
        path: Entry id (portfolio relative path) or file path.
        message: Human readable description.
    """

    code: str
    severity: str
    path: str
    message: str

    @property
    def is_error(self) -> bool:
        """True for blocking findings."""
        return self.severity == ERROR

    def to_dict(self) -> dict[str, str]:
        """Serialise for the JSON report and the web UI."""
        return {
            "code": self.code,
            "severity": self.severity,
            "path": self.path,
            "message": self.message,
        }


@dataclass
class CheckReport:
    """Aggregated result of :func:`run_checks`."""

    issues: list[Issue] = field(default_factory=list)
    checked: int = 0
    entries: list[Entry] = field(default_factory=list)

    @property
    def errors(self) -> list[Issue]:
        """Blocking findings."""
        return [issue for issue in self.issues if issue.is_error]

    @property
    def warnings(self) -> list[Issue]:
        """Non blocking findings."""
        return [issue for issue in self.issues if not issue.is_error]

    def ok(self, *, strict: bool = False) -> bool:
        """True when there is nothing to report (warnings count in strict mode)."""
        if strict:
            return not self.issues
        return not self.errors

    def to_dict(self) -> dict[str, object]:
        """Serialise the report (CLI ``--json`` and web UI)."""
        return {
            "checked": self.checked,
            "errors": [issue.to_dict() for issue in self.errors],
            "warnings": [issue.to_dict() for issue in self.warnings],
            "ok": self.ok(),
        }


def _entry_location(entry: Entry) -> tuple[str, str, str]:
    """Return ``(domain, subdomain, folder)`` from the entry path.

    Missing parts are returned as empty strings.
    """
    parts = entry.relative_path.parts
    domain = parts[1] if len(parts) > 2 else ""
    subdomain = parts[2] if len(parts) > 3 else ""
    folder = parts[3] if len(parts) > 4 else ""
    return domain, subdomain, folder


def check_entry(config: Config, entry: Entry) -> list[Issue]:
    """Run every per-entry check and return the findings."""
    issues: list[Issue] = []
    entry_id = entry.entry_id

    def add(code: str, severity: str, message: str) -> None:
        issues.append(Issue(code=code, severity=severity, path=entry_id, message=message))

    # -- identity -----------------------------------------------------------
    if not entry.title:
        add("E002", ERROR, "missing title in front matter")

    if not entry.type:
        add("E003", ERROR, "missing 'type' in front matter")
    elif not is_valid_type(entry.type):
        add(
            "E003",
            ERROR,
            f"invalid type {entry.type!r} (expected one of {', '.join(CONTENT_FOLDERS)})",
        )

    # -- date ---------------------------------------------------------------
    if not entry.date:
        add("E004", ERROR, "missing date in front matter")
    else:
        try:
            validate_date(entry.date)
        except Exception as exc:  # ValidationError carries a readable message
            add("E005", ERROR, str(exc))

    # -- status / draft -----------------------------------------------------
    if not entry.status:
        add("E006", ERROR, "missing status in front matter")
    elif entry.status not in STATUSES:
        add("E006", ERROR, f"invalid status {entry.status!r} (expected {', '.join(STATUSES)})")
    else:
        draft_flag = entry.metadata.get("draft")
        expected_draft = entry.status != "published"
        if draft_flag is not None and not isinstance(draft_flag, bool):
            add("E008", ERROR, "'draft' must be a boolean")
        elif draft_flag is not None and draft_flag != expected_draft:
            add(
                "E008",
                ERROR,
                f"'draft' is {draft_flag!r} while status is {entry.status!r}",
            )

    # -- tags ---------------------------------------------------------------
    if not entry.tags:
        add("W007", WARNING, "no tags")

    # -- domain / subdomain -------------------------------------------------
    domain, subdomain, folder = _entry_location(entry)
    if not domain or not subdomain or not folder:
        add("E011", ERROR, "file is not inside content/<domain>/<subdomain>/<type>/")
    else:
        if entry.type and is_valid_type(entry.type):
            expected_folder = CONTENT_FOLDERS[entry.type]
            if folder != expected_folder:
                add(
                    "E011",
                    ERROR,
                    f"file lives in {folder}/ but its type is {entry.type!r} "
                    f"(expected {expected_folder}/)",
                )
        if folder not in FOLDER_CONTENT_TYPES:
            add("E011", ERROR, f"unknown content folder {folder!r}")
        if entry.metadata.get("domain") and entry.metadata.get("domain") != domain:
            add(
                "E011",
                ERROR,
                f"front matter domain {entry.metadata.get('domain')!r} "
                f"does not match directory {domain!r}",
            )
        if entry.metadata.get("subdomain") and entry.metadata.get("subdomain") != subdomain:
            add(
                "E011",
                ERROR,
                f"front matter subdomain {entry.metadata.get('subdomain')!r} "
                f"does not match directory {subdomain!r}",
            )
        if domain not in config.domains:
            add("W016", WARNING, f"domain {domain!r} is not declared in config.json")
        elif subdomain not in config.domains[domain]:
            add(
                "W016",
                WARNING,
                f"subdomain {subdomain!r} is not declared for domain {domain!r}",
            )

    # -- naming -------------------------------------------------------------
    if entry.path.parent.name != entry.path.parent.name.lower():
        add("E012", WARNING, "directory names should be lowercase")

    if not is_slug_filename(entry.path.name):
        add(
            "E012",
            ERROR,
            f"file name {entry.path.name!r} does not follow the slug convention",
        )

    # -- type-specific metadata --------------------------------------------
    allowed_fields = TYPE_METADATA_FIELDS.get(entry.type, ())
    for key in allowed_fields:
        value = entry.metadata.get(key)
        if value is not None and not isinstance(value, str):
            add("E013", ERROR, f"{key} must be a string")
        elif value == "":
            add("W013", WARNING, f"{key} is empty")

    pdf_value = entry.metadata.get("pdf")
    if isinstance(pdf_value, str) and pdf_value and not _URLISH.match(pdf_value):
        candidate = entry.path.parent / pdf_value
        if not candidate.is_file():
            add("E009", ERROR, f"referenced PDF not found: {pdf_value}")

    if (
        entry.type == "project"
        and entry.status == "published"
        and not entry.metadata.get("repository")
    ):
        add("W010", WARNING, "published project without a repository URL")

    return issues


def run_checks(config: Config, *, entries: list[Entry] | None = None) -> CheckReport:
    """Check the whole portfolio (or a provided list of entries)."""
    report = CheckReport()

    if entries is None:
        if not config.content_root.is_dir():
            report.issues.append(
                Issue(
                    code="E001",
                    severity=ERROR,
                    path=str(config.content_root),
                    message="content/ directory does not exist",
                )
            )
            return report
        entries, failures = iter_entries_strict(config.portfolio_root)
        for path, message in failures:
            prefix = f"{path}: "
            if message.startswith(prefix):
                message = message[len(prefix) :]
            report.issues.append(
                Issue(
                    code="E001",
                    severity=ERROR,
                    path=path.relative_to(config.portfolio_root).as_posix(),
                    message=f"unreadable front matter: {message}",
                )
            )

    report.entries = list(entries)
    report.checked = len(entries)
    for entry in entries:
        report.issues.extend(check_entry(config, entry))

    # Cross-entry check: duplicated titles.
    seen: dict[str, str] = {}
    for entry in entries:
        key = entry.title.strip().lower()
        if not key:
            continue
        if key in seen:
            report.issues.append(
                Issue(
                    code="E014",
                    severity=WARNING,
                    path=entry.entry_id,
                    message=f"duplicate title, already used by {seen[key]}",
                )
            )
        else:
            seen[key] = entry.entry_id

    report.issues.sort(key=lambda issue: (issue.path, issue.code))
    return report


def format_report(report: CheckReport, *, root: Path | None = None) -> str:
    """Render a human readable report for the terminal."""
    lines: list[str] = []
    prefix = f"{root}/" if root else ""
    for issue in report.issues:
        marker = "ERROR  " if issue.is_error else "WARNING"
        lines.append(f"{marker} {issue.code} {prefix}{issue.path}: {issue.message}")
    summary = (
        f"{report.checked} entries checked, "
        f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)"
    )
    lines.append(summary)
    return "\n".join(lines)
