"""Tests for the safe Markdown renderer used by the web preview."""

from __future__ import annotations

import unittest

from pfm.markdown import render_markdown


class RenderMarkdownTests(unittest.TestCase):
    def test_headings(self) -> None:
        self.assertEqual(render_markdown("# Title"), "<h1>Title</h1>")
        self.assertEqual(render_markdown("### Deep"), "<h3>Deep</h3>")

    def test_paragraphs(self) -> None:
        self.assertEqual(
            render_markdown("First line\nsecond line\n\nNew paragraph"),
            "<p>First line second line</p>\n<p>New paragraph</p>",
        )

    def test_inline_formatting(self) -> None:
        html = render_markdown("**bold** and *italic* and `code`")
        self.assertIn("<strong>bold</strong>", html)
        self.assertIn("<em>italic</em>", html)
        self.assertIn("<code>code</code>", html)

    def test_links(self) -> None:
        html = render_markdown("[site](https://example.org)")
        self.assertIn('<a href="https://example.org">site</a>', html)

    def test_unsafe_links_are_stripped(self) -> None:
        html = render_markdown("[click](javascript:alert(1))")
        self.assertNotIn("javascript", html)
        self.assertIn("click", html)

    def test_raw_html_is_escaped(self) -> None:
        html = render_markdown("<script>alert(1)</script>")
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_lists(self) -> None:
        html = render_markdown("- one\n- two\n\n1. first\n2. second")
        self.assertIn("<ul>", html)
        self.assertIn("<li>one</li>", html)
        self.assertIn("<ol>", html)
        self.assertIn("<li>second</li>", html)

    def test_code_fence_is_not_interpreted(self) -> None:
        html = render_markdown("```\n<script>x</script>\n```")
        self.assertIn("<pre><code>", html)
        self.assertIn("&lt;script&gt;", html)

    def test_blockquote_and_rule(self) -> None:
        self.assertIn("<blockquote>quoted</blockquote>", render_markdown("> quoted"))
        self.assertEqual(render_markdown("---"), "<hr>")

    def test_empty_document(self) -> None:
        self.assertEqual(render_markdown(""), "")

    def test_code_span_protects_markup(self) -> None:
        html = render_markdown("`**not bold**`")
        self.assertIn("<code>**not bold**</code>", html)
        self.assertNotIn("<strong>", html)


if __name__ == "__main__":
    unittest.main()
