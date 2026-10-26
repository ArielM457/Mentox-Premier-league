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
