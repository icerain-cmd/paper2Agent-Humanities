import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from paper2humanities.runtime.model_adapter import CodexExecAdapter, GenerationFormatFailure

TURN = {"text": "Bounded claim", "statement_type": "AUTHOR_CLAIM", "evidence_voice": "AUTHOR",
        "support_ids": ["s1"], "pages": [2], "relation_type": "QUALIFIES", "actor_paper": "p",
        "actor_edition_id": None, "action": "RESPONSE", "semantic_support": "SEMANTICALLY_SUPPORTED",
        "evidence_span": "source span"}

def test_codex_contract_and_fresh_ephemeral_invocation():
    calls = []
    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        Path(argv[argv.index("-o") + 1]).write_text(json.dumps(TURN))
        return subprocess.CompletedProcess(argv, 0, "", "")
    with patch("paper2humanities.runtime.model_adapter.subprocess.run", side_effect=fake_run):
        result = CodexExecAdapter().generate_typed_turn(system_contract="bounded", payload={"evidence": []})
    argv, kwargs = calls[0]
    assert argv[:8] == ["codex", "exec", "--ephemeral", "--skip-git-repo-check",
                         "--ignore-user-config", "--ignore-rules", "-s", "read-only"]
    assert argv[argv.index("-m") + 1] == "gpt-6-sol"
    assert "--output-schema" in argv and "-o" in argv
    assert kwargs["stdin"] is subprocess.DEVNULL
    assert kwargs["cwd"].startswith("/tmp/")
    assert result.parameters["attempts"] == 1

def test_malformed_retries_once_with_same_packet_then_abstains():
    calls = []
    def fake_run(argv, **kwargs):
        calls.append(argv)
        Path(argv[argv.index("-o") + 1]).write_text("{}")
        return subprocess.CompletedProcess(argv, 0, "", "")
    with patch("paper2humanities.runtime.model_adapter.subprocess.run", side_effect=fake_run):
        with pytest.raises(GenerationFormatFailure, match="GENERATION_FORMAT_FAILURE"):
            CodexExecAdapter().generate_typed_turn(system_contract="bounded", payload={"nonce": "same"})
    assert len(calls) == 2
    assert '"nonce": "same"' in calls[0][-1] and '"nonce": "same"' in calls[1][-1]
    assert "STRICT RETRY" in calls[1][-1]

def test_grounded_turn_requires_page_and_span():
    from paper2humanities.runtime.model_adapter import validate_typed_turn
    with pytest.raises(GenerationFormatFailure):
        validate_typed_turn({**TURN, "pages": []})
