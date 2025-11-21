from typing import Any, Dict, List, Optional


class SchemaBuilder:
    """
    Utility for building JSON Schemas from simple field lists or custom specifications.
    Provides backward compatibility for legacy field-based extraction.
    """

    @staticmethod
    def from_fields(
        fields: List[str],
        *,
        item_type: str = "object",
        allow_null: bool = True,
        require_all: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate a JSON Schema from a simple list of field names.

        Args:
            fields: List of field names to extract
            item_type: "object" for single extraction, "array" for multiple
            allow_null: Whether fields can be null
            require_all: Whether all fields are required

        Returns:
            JSON Schema dict
        """
        properties: Dict[str, Any] = {}

        for field in fields:
            field_schema: Dict[str, Any] = {"type": "string"}
            if allow_null:
                field_schema = {"anyOf": [{"type": "string"}, {"type": "null"}]}
            properties[field] = field_schema

        item_schema = {
            "type": "object",
            "properties": properties,
        }

        if require_all:
            item_schema["required"] = fields

        if item_type == "array":
            return {
                "type": "array",
                "items": item_schema,
            }

        return item_schema

    @staticmethod
    def wrap_with_provenance(
        extraction_schema: Dict[str, Any],
        require_provenance: bool = True,
    ) -> Dict[str, Any]:
        """
        Wrap an extraction schema with the standard provenance structure.

        Returns schema for: {extractions: <schema>, provenance: [...]}
        """
        wrapped = {
            "type": "object",
            "properties": {
                "extractions": extraction_schema,
                "provenance": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "document_id": {"type": "string"},
                            "chunk_id": {"type": "string"},
                            "reason": {"type": "string"},
                        },
                        "required": ["document_id"],
                    },
                },
            },
            "required": ["extractions"],
        }

        if require_provenance:
            wrapped["required"].append("provenance")

        return wrapped

    @staticmethod
    def merge_instructions(
        queries: Optional[List[str]] = None,
        custom_instructions: Optional[str] = None,
    ) -> str:
        """
        Merge legacy queries and custom instructions into a single instruction string.
        """
        parts: List[str] = []

        if custom_instructions:
            parts.append(custom_instructions)

        if queries:
            parts.append("Extract the following information:")
            for query in queries:
                parts.append(f"- {query}")

        if not parts:
            return (
                "Extract structured data from the documents. "
                "For each field in the schema, find the corresponding value in the documents. "
                "Return ONLY the JSON object with extracted values."
            )

        return "\n".join(parts)

    @staticmethod
    def validate_schema(schema: Dict[str, Any]) -> bool:
        """
        Basic validation that a schema is well-formed.
        """
        if not isinstance(schema, dict):
            return False

        if "type" not in schema:
            return False

        valid_types = {
            "object",
            "array",
            "string",
            "number",
            "integer",
            "boolean",
            "null",
        }
        schema_type = schema.get("type")

        if isinstance(schema_type, str):
            return schema_type in valid_types

        if isinstance(schema_type, list):
            return all(t in valid_types for t in schema_type)

        return False

    @staticmethod
    def get_schema_description(schema: Dict[str, Any]) -> str:
        """
        Generate a human-readable description of a schema for LLM prompts.
        """
        schema_type = schema.get("type", "unknown")

        if schema_type == "object":
            props = schema.get("properties", {})
            if props:
                fields = ", ".join(props.keys())
                return f"Object with fields: {fields}"
            return "Object"

        if schema_type == "array":
            items = schema.get("items", {})
            item_desc = SchemaBuilder.get_schema_description(items)
            return f"Array of {item_desc}"

        return schema_type.capitalize()
