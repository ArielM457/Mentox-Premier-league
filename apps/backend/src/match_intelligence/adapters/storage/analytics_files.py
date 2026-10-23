from pathlib import Path


class InMemoryAnalyticsWriter:
    """Guarda los archivos del análisis en memoria, para pruebas."""

    def __init__(self) -> None:
        self.files: dict[str, tuple[bytes, str]] = {}

    async def write(
        self, *, match_id: str, run_id: str, name: str, content: bytes, content_type: str
    ) -> str:
        location = f"memory://analytics/{match_id}/{run_id}/{name}"
        self.files[location] = (content, content_type)
        return location


class LocalDirectoryAnalyticsWriter:
    """Guarda los archivos en ``<root>/<match_id>/<run_id>/``."""

    def __init__(self, root: Path) -> None:
        self._root = root

    async def write(
        self, *, match_id: str, run_id: str, name: str, content: bytes, content_type: str
    ) -> str:
        directory = self._root / match_id / run_id
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / name
        path.write_bytes(content)
        return str(path)
