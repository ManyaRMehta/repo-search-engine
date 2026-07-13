from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentSyncSummary:
    files_created: int
    files_updated: int
    files_deleted: int
    files_unchanged: int

    @property
    def files_discovered(self) -> int:
        return (
            self.files_created
            + self.files_updated
            + self.files_unchanged
        )