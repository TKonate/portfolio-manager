"""Basic tests for Portfolio Manager."""

from pathlib import Path

import portfolio_manager as pm


def test_slugify():
    assert pm.slugify("Hello World") == "hello-world"
    assert pm.slugify("Populations civiles et souverainetés fragmentées") == "populations-civiles-et-souverainetes-fragmentees"
    assert pm.slugify("  Test  ") == "test"
    assert pm.slugify("a@b#c") == "a-b-c"


def test_parse_tags():
    assert pm.parse_tags("python, cli, markdown") == ["python", "cli", "markdown"]
    assert pm.parse_tags("  a , b , c  ") == ["a", "b", "c"]
    assert pm.parse_tags("") == []
    assert pm.parse_tags("single") == ["single"]


def test_validate_metadata():
    valid = {
        "title": "Test",
        "domain": "technology",
        "subdomain": "computer-science",
        "tags": "python, cli",
        "date": "2026",
    }
    assert pm.validate_metadata(valid) is True

    invalid_title = valid.copy()
    invalid_title["title"] = ""
    assert pm.validate_metadata(invalid_title) is False

    invalid_domain = valid.copy()
    invalid_domain["domain"] = "unknown"
    assert pm.validate_metadata(invalid_domain) is False

    invalid_subdomain = valid.copy()
    invalid_subdomain["subdomain"] = "unknown"
    assert pm.validate_metadata(invalid_subdomain) is False


def test_generate_front_matter():
    metadata = {
        "title": "Test Project",
        "domain": "technology",
        "subdomain": "computer-science",
        "tags": "python, cli",
        "date": "2026-01-15",
    }
    front_matter = pm.generate_front_matter(metadata, "project")
    assert 'title: "Test Project"' in front_matter
    assert 'type: "project"' in front_matter
    assert "date: 2026-01-15" in front_matter
    assert "tags:" in front_matter
    assert "- python" in front_matter
    assert "- cli" in front_matter
    assert 'status: "draft"' in front_matter
    assert front_matter.startswith("---\n")
    assert front_matter.endswith("---\n")


def test_build_file_path():
    metadata = {
        "domain": "technology",
        "subdomain": "computer-science",
    }
    portfolio_root = Path("/tmp/portfolio")
    file_path = pm.build_file_path(
        portfolio_root, metadata, "project", "test-project.md"
    )
    expected = Path(
        "/tmp/portfolio/content/technology/computer-science/projects/test-project.md"
    )
    assert file_path == expected
