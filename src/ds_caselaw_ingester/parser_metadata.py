"""Validate document processing metadata from parser tarballs against ds-caselaw-utils JSON Schema."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from typing import cast

from ds_caselaw_utils.types.metadata_schema_autogen import DocumentProcessingMetadata
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from .exceptions import InvalidMetadataException

_SCHEMA_PACKAGE = "ds_caselaw_utils.schemas.parser-metadata"
_SCHEMA_BASE = "https://nationalarchives.github.io/ds-caselaw-utils/schemas/parser-metadata/"
_SCHEMA_NAMES = (
    "metadata.schema.json",
    "parser.schema.json",
    "ingester_options.schema.json",
)


def _load_schema(name: str) -> dict:
    schema_text = resources.files(_SCHEMA_PACKAGE).joinpath(name).read_text(encoding="utf-8")
    schema = json.loads(schema_text)
    schema["$id"] = _SCHEMA_BASE + name
    return schema


@lru_cache(maxsize=1)
def _document_processing_metadata_validator() -> Draft202012Validator:
    schemas = {name: _load_schema(name) for name in _SCHEMA_NAMES}
    registry = Registry().with_resources(
        [(schemas[name]["$id"], Resource.from_contents(schemas[name])) for name in _SCHEMA_NAMES],
    )
    return Draft202012Validator(schemas["metadata.schema.json"], registry=registry)


def validate_document_processing_metadata(
    data: object,
    *,
    consignment_reference: str,
) -> DocumentProcessingMetadata:
    """Return ``data`` if it satisfies the document processing metadata schema, else raise."""
    if not isinstance(data, dict):
        raise InvalidMetadataException(
            f"Metadata must be a JSON object. Consignment Ref: {consignment_reference}",
        )

    validator = _document_processing_metadata_validator()
    errors = sorted(validator.iter_errors(data), key=lambda error: list(error.path))
    if not errors:
        return cast(DocumentProcessingMetadata, data)

    first_error = errors[0]
    path = ".".join(str(part) for part in first_error.path) or "(root)"
    message = (
        f"Metadata failed schema validation at {path}: {first_error.message}. Consignment Ref: {consignment_reference}"
    )
    raise InvalidMetadataException(message) from first_error
