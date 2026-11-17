"""Tests for :mod:`pfm.validate`."""

from __future__ import annotations

import unittest

from pfm.errors import ValidationError
from pfm.validate import (
    validate_content_type,
    validate_date,
    validate_extra_fields,
    validate_file_or_url,
    validate_status,
    validate_title,
    validate_url,
)


class TitleTests(unittest.TestCase):
    def test_strips(self) -> None:
        self.assertEqual(validate_title("  Hello  "), "Hello")

    def test_rejects_empty(self) -> None:
        with self.assertRaises(ValidationError):
            validate_title("   ")

    def test_rejects_multiline(self) -> None:
        with self.assertRaises(ValidationError):
            validate_title("a\nb")

    def test_rejects_too_long(self) -> None:
        with self.assertRaises(ValidationError):
            validate_title("a" * 201)


class DateTests(unittest.TestCase):
    def test_accepted_shapes(self) -> None:
        for value in ("2026", "2026-11", "2026-11-17", "1999-01-01"):
            self.assertEqual(validate_date(value), value)

    def test_rejected_shapes(self) -> None:
        for value in ("", "26-01", "2026-1-1", "2026/01/01", "2026-13", "2026-02-30"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validate_date(value)


class StatusAndTypeTests(unittest.TestCase):
    def test_status(self) -> None:
        self.assertEqual(validate_status("Published"), "published")
        with self.assertRaises(ValidationError):
            validate_status("finished")

    def test_content_type(self) -> None:
        self.assertEqual(validate_content_type("Publication"), "publication")
        with self.assertRaises(ValidationError):
            validate_content_type("article")


class UrlTests(unittest.TestCase):
    def test_valid(self) -> None:
        self.assertEqual(validate_url("repository", "https://example.org"), "https://example.org")
        self.assertEqual(validate_url("demo", "http://example.org/x"), "http://example.org/x")

    def test_invalid(self) -> None:
        for value in ("example.org", "ftp://example.org", "javascript:alert(1)", ""):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validate_url("repository", value)

    def test_file_or_url(self) -> None:
        self.assertEqual(validate_file_or_url("pdf", "paper.pdf"), "paper.pdf")
        self.assertEqual(validate_file_or_url("pdf", "docs/paper.pdf"), "docs/paper.pdf")
        self.assertEqual(
            validate_file_or_url("pdf", "https://example.org/p.pdf"), "https://example.org/p.pdf"
        )
        self.assertEqual(validate_file_or_url("pdf", "/tmp/paper.pdf"), "/tmp/paper.pdf")

    def test_file_or_url_rejects_escapes(self) -> None:
        for value in ("../secret.pdf", "ftp://example.org/p.pdf"):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                validate_file_or_url("pdf", value)


class ExtraFieldsTests(unittest.TestCase):
    def test_filters_unknown_and_empty(self) -> None:
        cleaned = validate_extra_fields(
            "project",
            {
                "repository": "https://example.org/r",
                "demo": "",
                "pdf": "should-be-dropped.pdf",
                "unknown": "x",
            },
        )
        self.assertEqual(cleaned, {"repository": "https://example.org/r"})

    def test_author_is_free_text(self) -> None:
        cleaned = validate_extra_fields("reading", {"author": "Umberto Eco"})
        self.assertEqual(cleaned, {"author": "Umberto Eco"})

    def test_invalid_url_raises(self) -> None:
        with self.assertRaises(ValidationError):
            validate_extra_fields("project", {"repository": "nope"})


if __name__ == "__main__":
    unittest.main()
