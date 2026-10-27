from dataclasses import dataclass
from pathlib import PurePath


@dataclass(frozen=True)
class SourceFile:
    filename: str
    content: bytes

    @property
    def extension(self) -> str:
        return PurePath(self.filename).suffix.lower()

    @property
    def stem(self) -> str:
        return PurePath(self.filename).stem
