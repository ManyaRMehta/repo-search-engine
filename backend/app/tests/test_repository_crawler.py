from pathlib import Path

import pytest

from app.services.repository_crawler import RepositoryCrawler


def test_crawler_finds_supported_source_files(tmp_path: Path):
    repo = tmp_path / "sample_repo"
    repo.mkdir()

    source_file = repo / "main.py"
    source_file.write_text("print('hello')", encoding="utf-8")

    crawler = RepositoryCrawler()
    files = crawler.crawl(repo)

    assert len(files) == 1
    assert files[0].relative_path == "main.py"
    assert files[0].extension == ".py"
    assert files[0].content == "print('hello')"


def test_crawler_ignores_unsupported_extensions(tmp_path: Path):
    repo = tmp_path / "sample_repo"
    repo.mkdir()

    image_file = repo / "logo.png"
    image_file.write_bytes(b"fake image bytes")

    crawler = RepositoryCrawler()
    files = crawler.crawl(repo)

    assert files == []


def test_crawler_ignores_configured_directories(tmp_path: Path):
    repo = tmp_path / "sample_repo"
    ignored_dir = repo / "node_modules"
    ignored_dir.mkdir(parents=True)

    ignored_file = ignored_dir / "package.js"
    ignored_file.write_text("console.log('ignore me')", encoding="utf-8")

    crawler = RepositoryCrawler()
    files = crawler.crawl(repo)

    assert files == []


def test_crawler_skips_large_files(tmp_path: Path):
    repo = tmp_path / "sample_repo"
    repo.mkdir()

    large_file = repo / "large.py"
    large_file.write_text("a" * 20, encoding="utf-8")

    crawler = RepositoryCrawler(max_file_size_bytes=10)
    files = crawler.crawl(repo)

    assert files == []


def test_crawler_raises_error_for_missing_path():
    crawler = RepositoryCrawler()

    with pytest.raises(FileNotFoundError):
        crawler.crawl("does-not-exist")