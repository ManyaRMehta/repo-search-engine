from pathlib import Path

from app.models.source_file import SourceFile


IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "dist",
    "build",
    "target",
    ".idea",
    ".vscode",
}

SUPPORTED_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".java",
    ".cs",
    ".go",
    ".md",
    ".txt",
    ".json",
    ".yml",
    ".yaml",
}

DEFAULT_MAX_FILE_SIZE_BYTES = 1_000_000


class RepositoryCrawler:
    """
    Finds source files in a local repository that are safe to index.

    This class does not tokenize, rank, or search.
    Its only job is repository ingestion.
    """

    def __init__(self, max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES):
        self.max_file_size_bytes = max_file_size_bytes

    def crawl(self, repo_path: str | Path) -> list[SourceFile]:
        root = Path(repo_path).resolve()

        if not root.exists():
            raise FileNotFoundError(f"Repository path does not exist: {root}")

        if not root.is_dir():
            raise NotADirectoryError(f"Repository path is not a directory: {root}")

        source_files: list[SourceFile] = []

        for file_path in root.rglob("*"):
            if not file_path.is_file():
                continue

            if self._is_ignored_path(file_path):
                continue

            if not self._has_supported_extension(file_path):
                continue

            if not self._is_within_size_limit(file_path):
                continue

            content = self._read_text_file(file_path)

            if content is None:
                continue

            source_files.append(
                SourceFile(
                    path=file_path,
                    relative_path=str(file_path.relative_to(root)),
                    extension=file_path.suffix.lower(),
                    size_bytes=file_path.stat().st_size,
                    content=content,
                )
            )

        return source_files

    def _is_ignored_path(self, file_path: Path) -> bool:
        return any(part in IGNORED_DIRECTORIES for part in file_path.parts)

    def _has_supported_extension(self, file_path: Path) -> bool:
        return file_path.suffix.lower() in SUPPORTED_EXTENSIONS

    def _is_within_size_limit(self, file_path: Path) -> bool:
        return file_path.stat().st_size <= self.max_file_size_bytes

    def _read_text_file(self, file_path: Path) -> str | None:
        try:
            return file_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return None
        except OSError:
            return None