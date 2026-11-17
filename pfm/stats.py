"""Portfolio statistics and homepage data (roadmap V7).

Statistics are computed from the entries themselves (front matter, with a
fallback on the directory layout), so they stay correct even for files that were
not created by the tool.
"""

from __future__ import annotations

import datetime as _dt
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import __version__
from .config import Config
from .models import STATUSES, Entry
from .store import iter_entries


@dataclass
class Stats:
    """Computed portfolio statistics."""

    total: int
    by_type: dict[str, int]
    by_status: dict[str, int]
    by_domain: dict[str, int]
    by_subdomain: dict[str, int]
    top_tags: list[tuple[str, int]]
    published_projects: list[dict[str, Any]]
    projects_in_progress: list[dict[str, Any]]
    publications_with_pdf: int
    publications_without_pdf: int
    drafts: int
    incomplete: list[dict[str, str]]
    generated_at: str

    def to_dict(self) -> dict[str, Any]:
        """JSON-ready representation (also used as homepage data)."""
        return {
            "generated_at": self.generated_at,
            "generator": f"portfolio-manager {__version__}",
            "total": self.total,
            "by_type": self.by_type,
            "by_status": self.by_status,
            "by_domain": self.by_domain,
            "by_subdomain": self.by_subdomain,
            "top_tags": [{"tag": tag, "count": count} for tag, count in self.top_tags],
            "published_projects": self.published_projects,
            "projects_in_progress": self.projects_in_progress,
            "publications_with_pdf": self.publications_with_pdf,
            "publications_without_pdf": self.publications_without_pdf,
            "drafts": self.drafts,
            "incomplete": self.incomplete,
        }


def _is_incomplete(entry: Entry) -> list[str]:
    """Return the reasons why ``entry`` is considered incomplete."""
    reasons: list[str] = []
    if not entry.title:
        reasons.append("missing title")
    if not entry.date:
        reasons.append("missing date")
    if not entry.status:
        reasons.append("missing status")
    if not entry.tags:
        reasons.append("no tags")
    if (
        entry.type == "project"
        and entry.status == "published"
        and not entry.metadata.get("repository")
    ):
        reasons.append("published project without repository")
    return reasons


def compute_stats(entries: list[Entry]) -> Stats:
    """Compute statistics from a list of entries."""
    by_type = Counter(entry.type or "unknown" for entry in entries)
    by_status = Counter(entry.status or "unknown" for entry in entries)
    by_domain = Counter(entry.domain or "unknown" for entry in entries)
    by_subdomain = Counter(entry.subdomain or "unknown" for entry in entries)

    tag_counter: Counter[str] = Counter()
    for entry in entries:
        tag_counter.update(entry.tags)

    published_projects = [
        {
            "title": entry.title,
            "id": entry.entry_id,
            "domain": entry.domain,
            "subdomain": entry.subdomain,
            "repository": entry.metadata.get("repository", ""),
            "tags": entry.tags,
        }
        for entry in entries
        if entry.type == "project" and entry.status == "published"
    ]
    projects_in_progress = [
        {"title": entry.title, "id": entry.entry_id, "domain": entry.domain}
        for entry in entries
        if entry.type == "project" and entry.status == "in-progress"
    ]

    publications = [entry for entry in entries if entry.type == "publication"]
    with_pdf = sum(1 for entry in publications if entry.metadata.get("pdf"))

    incomplete: list[dict[str, str]] = []
    for entry in entries:
        reasons = _is_incomplete(entry)
        if reasons:
            incomplete.append({"id": entry.entry_id, "reasons": "; ".join(reasons)})

    return Stats(
        total=len(entries),
        by_type=dict(sorted(by_type.items())),
        by_status={status: by_status.get(status, 0) for status in STATUSES},
        by_domain=dict(sorted(by_domain.items())),
        by_subdomain=dict(sorted(by_subdomain.items())),
        top_tags=tag_counter.most_common(15),
        published_projects=sorted(published_projects, key=lambda item: item["title"].lower()),
        projects_in_progress=sorted(projects_in_progress, key=lambda item: item["title"].lower()),
        publications_with_pdf=with_pdf,
        publications_without_pdf=len(publications) - with_pdf,
        drafts=sum(1 for entry in entries if entry.is_draft),
        incomplete=incomplete,
        generated_at=_dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
    )


def collect_stats(config: Config) -> Stats:
    """Compute statistics for the configured portfolio."""
    return compute_stats(iter_entries(config.portfolio_root))


def format_stats(stats: Stats) -> str:
    """Render statistics as a readable terminal report."""
    lines = [
        f"Portfolio: {stats.total} entries",
        "",
        "By type:",
        *[f"  {name:<14} {count}" for name, count in stats.by_type.items()],
        "",
        "By status:",
        *[f"  {name:<14} {count}" for name, count in stats.by_status.items()],
        "",
        "By domain:",
        *[f"  {name:<20} {count}" for name, count in stats.by_domain.items()],
    ]
    if stats.top_tags:
        lines += ["", "Top tags:"]
        lines += [f"  {tag:<24} {count}" for tag, count in stats.top_tags]
    lines += [
        "",
        f"Published projects: {len(stats.published_projects)}",
        f"Projects in progress: {len(stats.projects_in_progress)}",
        f"Publications with PDF: {stats.publications_with_pdf}",
        f"Publications without PDF: {stats.publications_without_pdf}",
        f"Drafts: {stats.drafts}",
        f"Incomplete entries: {len(stats.incomplete)}",
    ]
    if stats.incomplete:
        lines.append("")
        for item in stats.incomplete:
            lines.append(f"  - {item['id']}: {item['reasons']}")
    return "\n".join(lines)


def write_stats_json(config: Config, stats: Stats, path: Path | None = None) -> Path:
    """Write the statistics as JSON for the portfolio homepage.

    Default destination: ``<portfolio>/data/portfolio_stats.json``.
    """
    destination = path or (config.data_root / "portfolio_stats.json")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(stats.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return destination
