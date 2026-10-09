from dataclasses import dataclass
from enum import StrEnum
from hashlib import sha256
import re


class ArtifactKind(StrEnum):
    SYNTHETIC_MATCH = "synthetic_match"
    AUTHORIZED_VIDEO = "authorized_video"
    OBSERVATION = "observation"


class ArtifactProvenance(StrEnum):
    SYNTHETIC = "synthetic"
    AUTHORIZED = "authorized"
    EXPERIMENTAL = "experimental"


CONTAINER_BY_KIND: dict[ArtifactKind, str] = {
    ArtifactKind.SYNTHETIC_MATCH: "matches",
    ArtifactKind.AUTHORIZED_VIDEO: "authorized-videos",
    ArtifactKind.OBSERVATION: "observations",
}

_PROVENANCE_BY_KIND: dict[ArtifactKind, ArtifactProvenance] = {
    ArtifactKind.SYNTHETIC_MATCH: ArtifactProvenance.SYNTHETIC,
    ArtifactKind.AUTHORIZED_VIDEO: ArtifactProvenance.AUTHORIZED,
    ArtifactKind.OBSERVATION: ArtifactProvenance.EXPERIMENTAL,
}

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class ArtifactValidationError(ValueError):
    """El artefacto no tiene trazabilidad suficiente para almacenarse."""


@dataclass(frozen=True, slots=True)
class Artifact:
    artifact_id: str
    match_id: str
    kind: ArtifactKind
    provenance: ArtifactProvenance
    origin: str
    content_type: str
    content: bytes

    def __post_init__(self) -> None:
        for field_name, value in (
            ("artifact_id", self.artifact_id),
            ("match_id", self.match_id),
            ("origin", self.origin),
        ):
            if not _SAFE_IDENTIFIER.fullmatch(value):
                raise ArtifactValidationError(
                    f"{field_name} debe ser un identificador seguro de 1 a 128 caracteres"
                )

        expected = _PROVENANCE_BY_KIND[self.kind]
        if self.provenance is not expected:
            raise ArtifactValidationError(
                f"{self.kind.value} requiere procedencia {expected.value}"
            )
        if not self.content_type.strip():
            raise ArtifactValidationError("content_type es obligatorio")
        if not self.content:
            raise ArtifactValidationError("content no puede estar vacío")

    @property
    def container(self) -> str:
        return CONTAINER_BY_KIND[self.kind]

    @property
    def blob_name(self) -> str:
        return f"{self.match_id}/{self.artifact_id}"

    @property
    def content_sha256(self) -> str:
        return sha256(self.content).hexdigest()


@dataclass(frozen=True, slots=True)
class ArtifactLocation:
    container: str
    blob_name: str
    artifact_id: str
    match_id: str
    kind: ArtifactKind
    provenance: ArtifactProvenance
    origin: str
    content_type: str
    content_sha256: str


@dataclass(frozen=True, slots=True)
class RetrievedArtifact:
    location: ArtifactLocation
    content: bytes
