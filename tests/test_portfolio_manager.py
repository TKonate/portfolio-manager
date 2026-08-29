"""Tests basiques pour Portfolio Manager."""

import tempfile
import json
from pathlib import Path

# Import du module à tester
import portfolio_manager as pm


def test_slugify():
    assert pm.slugify("Hello World") == "hello-world"
    assert pm.slugify("Populations civiles et souverainetés fragmentées") == "populations-civiles-et-souverainetes-fragmentees"
    assert pm.slugify("  Test  ") == "test"
    assert pm.slugify("a@b#c") == "a-b-c"
    print("✓ test_slugify passed")


def test_parse_tags():
    assert pm.parse_tags("python, cli, markdown") == ["python", "cli", "markdown"]
    assert pm.parse_tags("  a , b , c  ") == ["a", "b", "c"]
    assert pm.parse_tags("") == []
    assert pm.parse_tags("single") == ["single"]
    print("✓ test_parse_tags passed")


def test_validate_metadata():
    # Métadonnées valides
    valid = {
        "title": "Test",
        "domain": "technology",
        "subdomain": "computer-science",
        "tags": "python, cli",
        "date": "2026"
    }
    assert pm.validate_metadata(valid) is True

    # Titre vide
    invalid_title = valid.copy()
    invalid_title["title"] = ""
    assert pm.validate_metadata(invalid_title) is False

    # Domaine invalide
    invalid_domain = valid.copy()
    invalid_domain["domain"] = "unknown"
    assert pm.validate_metadata(invalid_domain) is False

    # Sous-domaine invalide
    invalid_sub = valid.copy()
    invalid_sub["subdomain"] = "unknown"
    assert pm.validate_metadata(invalid_sub) is False

    print("✓ test_validate_metadata passed")


def test_generate_front_matter():
    metadata = {
        "title": "Test Project",
        "domain": "technology",
        "subdomain": "computer-science",
        "tags": "python, cli",
        "date": "2026-01-15"
    }
    fm = pm.generate_front_matter(metadata, "project")
    assert "title: \"Test Project\"" in fm
    assert "type: \"project\"" in fm
    assert "date: 2026-01-15" in fm
    assert "tags:" in fm
    assert "- python" in fm
    assert "- cli" in fm
    assert "status: \"draft\"" in fm
    assert fm.startswith("---\n")
    assert fm.endswith("---\n")
    print("✓ test_generate_front_matter passed")


def test_build_file_path():
    from pathlib import Path
    metadata = {
        "domain": "technology",
        "subdomain": "computer-science"
    }
    portfolio_root = Path("/tmp/portfolio")
    file_path = pm.build_file_path(portfolio_root, metadata, "project", "test-project.md")
    expected = Path("/tmp/portfolio/content/technology/computer-science/projects/test-project.md")
    assert file_path == expected
    print("✓ test_build_file_path passed")


if __name__ == "__main__":
    test_slugify()
    test_parse_tags()
    test_validate_metadata()
    test_generate_front_matter()
    test_build_file_path()
    print("\n✅ All tests passed!")
