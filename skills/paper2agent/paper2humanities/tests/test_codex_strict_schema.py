import json

from paper2humanities.runtime.attribution import enrich_attribution_axes
from paper2humanities.runtime.model_adapter import (
    CODEX_SCHEMA_PATH,
    SCHEMA_PATH,
    validate_typed_turn,
)


def _assert_strict_objects(schema):
    if isinstance(schema, dict):
        if "properties" in schema:
            assert schema.get("additionalProperties") is False
            assert isinstance(schema.get("required"), list)
            assert set(schema["required"]) == set(schema["properties"])
        for value in schema.values():
            _assert_strict_objects(value)
    elif isinstance(schema, list):
        for value in schema:
            _assert_strict_objects(value)


def _validate_wire_instance(value, schema):
    if "enum" in schema:
        assert value in schema["enum"]
    expected = schema.get("type")
    if isinstance(expected, list):
        if value is None:
            assert "null" in expected
            return
        expected = next(item for item in expected if item != "null")
    if expected == "object":
        assert isinstance(value, dict)
        assert set(value) == set(schema["required"])
        if schema.get("additionalProperties") is False:
            assert set(value) <= set(schema["properties"])
        for key, child in schema["properties"].items():
            _validate_wire_instance(value[key], child)
    elif expected == "array":
        assert isinstance(value, list)
        for item in value:
            _validate_wire_instance(item, schema["items"])
    elif expected == "string":
        assert isinstance(value, str)
    elif expected == "integer":
        assert type(value) is int


def _grounded_turn():
    return {
        "text": "The source attributes this proposition to the author.",
        "statement_type": "AUTHOR_CLAIM",
        "evidence_voice": "AUTHOR",
        "support_ids": ["s1"],
        "pages": [1],
        "relation_type": "QUALIFIES",
        "actor_paper": "paper",
        "actor_edition_id": None,
        "action": "AUTHOR_ATTRIBUTION",
        "semantic_support": "SEMANTICALLY_SUPPORTED",
        "evidence_sufficiency": "SUFFICIENT",
        "qualification": None,
        "evidence_span": "source span",
        "thesis": None,
        "target_claim": None,
        "stance_update": None,
        "unresolved_point": None,
        "claims": [{
            "text": "The source states the claim.",
            "statement_type": "AUTHOR_CLAIM",
            "support_ids": ["s1"],
        }],
    }


def _unresolved_turn():
    return {
        "text": "The supplied evidence is insufficient.",
        "statement_type": "UNRESOLVED",
        "evidence_voice": "UNKNOWN",
        "support_ids": [],
        "pages": [],
        "relation_type": "UNRESOLVED",
        "actor_paper": "paper",
        "actor_edition_id": None,
        "action": "SOURCE_RETRIEVAL",
        "semantic_support": "UNSUPPORTED",
        "evidence_sufficiency": "INSUFFICIENT",
        "qualification": None,
        "evidence_span": None,
        "thesis": None,
        "target_claim": None,
        "stance_update": None,
        "unresolved_point": None,
        "claims": [],
    }


def test_codex_wire_schema_is_recursively_strict_and_excludes_derived_axes():
    wire = json.loads(CODEX_SCHEMA_PATH.read_text(encoding="utf-8"))
    internal = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    _assert_strict_objects(wire)
    assert "statement_form" not in wire["properties"]
    assert "attribution_owner" not in wire["properties"]
    assert "statement_form" in internal["properties"]
    assert "attribution_owner" in internal["properties"]
def test_wire_output_without_derived_axes_validates_and_enriches_grounded_turn():
    wire = json.loads(CODEX_SCHEMA_PATH.read_text(encoding="utf-8"))
    turn = _grounded_turn()
    _validate_wire_instance(turn, wire)
    validated = validate_typed_turn(turn)
    enriched = enrich_attribution_axes(validated)
    assert enriched["statement_form"] == "PARAPHRASE"
    assert enriched["attribution_owner"] == "AUTHOR"


def test_wire_output_without_derived_axes_keeps_unresolved_unattributed():
    wire = json.loads(CODEX_SCHEMA_PATH.read_text(encoding="utf-8"))
    turn = _unresolved_turn()
    _validate_wire_instance(turn, wire)
    validated = validate_typed_turn(turn)
    enriched = enrich_attribution_axes(validated)
    assert "statement_form" not in enriched
    assert "attribution_owner" not in enriched


def test_attribution_derivation_matrix_remains_identical():
    cases = [
        ({"statement_type": "AUTHOR_CLAIM", "evidence_voice": "AUTHOR"}, "PARAPHRASE", "AUTHOR"),
        ({"statement_type": "SOURCE_QUOTE", "evidence_voice": "EXTERNAL"}, "QUOTE", "EXTERNAL"),
        ({"statement_type": "INTERPRETATION", "evidence_voice": "EXTERNAL"}, "INTERPRETIVE_STATEMENT", "EXTERNAL"),
        ({"statement_type": "AI_SYNTHESIS", "evidence_voice": "UNKNOWN"}, "SYNTHESIS", "AI"),
    ]
    for turn, expected_form, expected_owner in cases:
        enriched = enrich_attribution_axes(turn)
        assert enriched["statement_form"] == expected_form
        assert enriched["attribution_owner"] == expected_owner
