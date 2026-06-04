"""Tests for pure utility functions — no filesystem or LLM needed."""

from __future__ import annotations

from pathlib import Path

import pytest

from llm_memory.utils import (
    build_index_entry,
    extract_wikilinks,
    file_hash,
    get_article_word_count,
    slugify,
)


class TestSlugify:
    def test_lowercase_and_spaces(self):
        assert slugify("Hello World") == "hello-world"

    def test_collapses_multiple_spaces(self):
        assert slugify("  lots   of   spaces  ") == "lots-of-spaces"

    def test_strips_special_chars(self):
        assert slugify("React.js Patterns!") == "reactjs-patterns"

    def test_handles_underscores(self):
        assert slugify("snake_case_name") == "snake-case-name"

    def test_empty_string(self):
        assert slugify("") == ""

    def test_preserves_hyphens(self):
        assert slugify("already-slugged") == "already-slugged"


class TestExtractWikilinks:
    def test_single_link(self):
        assert extract_wikilinks("See [[python-patterns]]") == ["python-patterns"]

    def test_multiple_links(self):
        result = extract_wikilinks("[[alpha]] and [[beta]] and [[gamma]]")
        assert result == ["alpha", "beta", "gamma"]

    def test_no_links(self):
        assert extract_wikilinks("plain text no links") == []

    def test_links_with_paths(self):
        result = extract_wikilinks("See [[concepts/async-design]]")
        assert result == ["concepts/async-design"]

    def test_incomplete_brackets_ignored(self):
        assert extract_wikilinks("[single bracket]") == []


class TestBuildIndexEntry:
    def test_produces_markdown_row(self):
        entry = build_index_entry("concepts/python.md", "Python tips", "2026-06-04", "2026-06-04")
        assert "[[concepts/python]]" in entry
        assert "Python tips" in entry
        assert "2026-06-04" in entry

    def test_strips_md_extension(self):
        entry = build_index_entry("qa/my-question.md", "summary", "src", "date")
        assert "[[qa/my-question]]" in entry
        assert ".md" not in entry.split("|")[1]  # link cell should have no .md


class TestFileHash:
    def test_returns_16_char_hex(self, tmp_path):
        f = tmp_path / "test.txt"
        f.write_text("hello world")
        h = file_hash(f)
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)

    def test_same_content_same_hash(self, tmp_path):
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_text("same content")
        b.write_text("same content")
        assert file_hash(a) == file_hash(b)

    def test_different_content_different_hash(self, tmp_path):
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_text("content A")
        b.write_text("content B")
        assert file_hash(a) != file_hash(b)


class TestGetArticleWordCount:
    def test_counts_words_in_body(self, tmp_path):
        f = tmp_path / "article.md"
        f.write_text("one two three four five")
        assert get_article_word_count(f) == 5

    def test_skips_frontmatter(self, tmp_path):
        f = tmp_path / "article.md"
        f.write_text("---\ntitle: My Article\ndate: 2026-01-01\n---\none two three")
        assert get_article_word_count(f) == 3
