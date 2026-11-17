"""Tests for :mod:`pfm.naming`."""

from __future__ import annotations

import unittest
from pathlib import Path

from pfm.naming import (
    MAX_SLUG_LENGTH,
    filename_for,
    is_slug_filename,
    parse_tags,
    slugify,
    target_path,
)


class SlugifyTests(unittest.TestCase):
    def test_plain_title(self) -> None:
        self.assertEqual(slugify("Hello World"), "hello-world")

    def test_accents_are_folded(self) -> None:
        self.assertEqual(
            slugify("Populations civiles et souverainetés fragmentées"),
            "populations-civiles-et-souverainetes-fragmentees",
        )

    def test_edges_and_specials(self) -> None:
        self.assertEqual(slugify("  Test  "), "test")
        self.assertEqual(slugify("a@b#c"), "a-b-c")
        self.assertEqual(slugify("---already-slug---"), "already-slug")

    def test_empty_when_no_usable_character(self) -> None:
        self.assertEqual(slugify("###"), "")

    def test_truncates_on_a_word_boundary(self) -> None:
        slug = slugify("word " * 40)
        self.assertLessEqual(len(slug), MAX_SLUG_LENGTH)
        self.assertFalse(slug.endswith("-"))
        self.assertNotIn("--", slug)

    def test_long_single_word_is_truncated(self) -> None:
        slug = slugify("a" * 200)
        self.assertEqual(len(slug), MAX_SLUG_LENGTH)


class ParseTagsTests(unittest.TestCase):
    def test_comma_separated(self) -> None:
        self.assertEqual(parse_tags("python, cli, markdown"), ["python", "cli", "markdown"])

    def test_trims_and_deduplicates(self) -> None:
        self.assertEqual(parse_tags(" python , Python ,cli "), ["python", "cli"])

    def test_spaces_become_dashes(self) -> None:
        self.assertEqual(parse_tags("open source"), ["open-source"])

    def test_accepts_sequences(self) -> None:
        self.assertEqual(parse_tags(["A", "b c"]), ["a", "b-c"])

    def test_empty_values(self) -> None:
        self.assertEqual(parse_tags(""), [])
        self.assertEqual(parse_tags([",", " "]), [])


class FilenameTests(unittest.TestCase):
    def test_filename(self) -> None:
        self.assertEqual(filename_for("My Project"), "my-project.md")

    def test_filename_requires_usable_title(self) -> None:
        with self.assertRaises(ValueError):
            filename_for("!!!")

    def test_slug_convention(self) -> None:
        self.assertTrue(is_slug_filename("my-project.md"))
        self.assertTrue(is_slug_filename("index.md"))
        self.assertFalse(is_slug_filename("My Project.md"))
        self.assertFalse(is_slug_filename("my-project.txt"))
        self.assertFalse(is_slug_filename("_index.md"))


class TargetPathTests(unittest.TestCase):
    def test_flat_entry(self) -> None:
        path = target_path(Path("/p"), "project", "technology", "computer-science", "slug.md")
        self.assertEqual(path, Path("/p/content/technology/computer-science/projects/slug.md"))

    def test_bundle_entry(self) -> None:
        path = target_path(
            Path("/p"),
            "publication",
            "society",
            "political-science",
            "slug.md",
            bundle=True,
        )
        self.assertEqual(
            path, Path("/p/content/society/political-science/publications/slug/index.md")
        )


if __name__ == "__main__":
    unittest.main()
