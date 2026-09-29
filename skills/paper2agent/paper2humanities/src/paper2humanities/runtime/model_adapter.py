from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import hashlib, json, os, urllib.request, subprocess, tempfile, shutil
from pathlib import Path

class ModelRuntimeUnavailable(RuntimeError):
    def __init__(self, message: str, attempts: int = 0):
        super().__init__(message)
        self.attempts = attempts

class GenerationFormatFailure(ValueError):
    outcome = "GENERATION_FORMAT_FAILURE"
    def __init__(self, message: str, attempts: int = 0):
        super().__init__(message)
        self.attempts = attempts

@dataclass(frozen=True)
class ModelResult:
    text: str
    provider: str
    model: str
    parameters: dict[str, Any]
    prompt_sha256: str

class ModelAdapter:
    provider = "abstract"
    model = "abstract"
    def available(self) -> bool:
        raise NotImplementedError
    def generate_typed_turn(self, *, system_contract: str, payload: dict[str, Any]) -> ModelResult:
        raise NotImplementedError

SCHEMA_PATH = Path(__file__).with_name("typed_turn.schema.json")
REQUIRED_TURN = {"text", "statement_type", "evidence_voice", "support_ids", "pages",
                 "relation_type", "actor_paper", "actor_edition_id", "action",
                 "semantic_support", "evidence_span"}
STATEMENT_TYPES = {"SOURCE_QUOTE", "AUTHOR_CLAIM", "INTERPRETATION", "AI_SYNTHESIS", "CRITIQUE", "UNRESOLVED"}
RELATIONS = {"CONTRADICTS", "TENSIONS_WITH", "QUALIFIES", "EXTENDS", "REFRAMES", "NOT_ADDRESSED", "UNRESOLVED"}
ACTIONS = {"SOURCE_RETRIEVAL", "CRITIQUE", "RESPONSE", "ISSUE", "RESEARCH_GAP", "RESEARCH_QUESTION", "SYNTHESIS"}

def validate_typed_turn(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or REQUIRED_TURN - value.keys():
        raise GenerationFormatFailure("typed turn missing required fields")
    if not isinstance(value["text"], str) or not value["text"].strip():
        raise GenerationFormatFailure("typed turn text required")
    if value["statement_type"] not in STATEMENT_TYPES or value["relation_type"] not in RELATIONS:
        raise GenerationFormatFailure("invalid statement or relation type")
    if value["evidence_voice"] not in {"AUTHOR", "EXTERNAL", "UNKNOWN"}:
        raise GenerationFormatFailure("invalid evidence voice")
    if not isinstance(value["support_ids"], list) or any(not isinstance(x, str) for x in value["support_ids"]):
        raise GenerationFormatFailure("support_ids must be string array")
    if not isinstance(value["pages"], list) or any(type(x) is not int or x < 1 for x in value["pages"]):
        raise GenerationFormatFailure("pages must be positive integer array")
    for key in ("actor_paper", "action"):
        if not isinstance(value[key], str) or not value[key]:
            raise GenerationFormatFailure(f"{key} required")
    if value["action"] not in ACTIONS:
        raise GenerationFormatFailure("invalid action")
    if value["actor_edition_id"] is not None and not isinstance(value["actor_edition_id"], str):
        raise GenerationFormatFailure("actor_edition_id must be string or null")
    if value["evidence_span"] is not None and not isinstance(value["evidence_span"], str):
        raise GenerationFormatFailure("evidence_span must be string or null")
    if value["semantic_support"] not in {"SEMANTICALLY_SUPPORTED", "PARTIALLY_SUPPORTED", "OVERSTATED", "UNSUPPORTED"}:
        raise GenerationFormatFailure("invalid semantic_support")
    sufficiency = value.get("evidence_sufficiency")
    if sufficiency is not None and sufficiency not in {"SUFFICIENT", "PARTIAL", "INSUFFICIENT", "CONFLICTING"}:
        raise GenerationFormatFailure("invalid evidence_sufficiency")
    qualification = value.get("qualification")
    if qualification is not None and not isinstance(qualification, str):
        raise GenerationFormatFailure("qualification must be string or null")
    if value["semantic_support"] == "PARTIALLY_SUPPORTED" and "qualification" in value and not (qualification or "").strip():
        raise GenerationFormatFailure("partial support requires qualification")
    if value["statement_type"] == "UNRESOLVED":
        if (value["support_ids"] or value["pages"] or value["evidence_span"] is not None
                or value["evidence_voice"] != "UNKNOWN" or value["semantic_support"] != "UNSUPPORTED"
                or (value.get("evidence_sufficiency") is not None and value.get("evidence_sufficiency") not in {"INSUFFICIENT", "CONFLICTING"})
                or value.get("qualification") is not None or value["relation_type"] != "UNRESOLVED"):
            raise GenerationFormatFailure("UNRESOLVED abstention shape required")
    else:
        if not value["support_ids"] or not value["pages"] or not value["evidence_span"]:
            raise GenerationFormatFailure("grounded turn requires support, page, and span")
    if value["statement_type"] == "AUTHOR_CLAIM" and value["evidence_voice"] != "AUTHOR":
        raise GenerationFormatFailure("author claim requires author voice")
    claims = value.get("claims")
    if claims is not None:
        if not isinstance(claims, list) or (value["statement_type"] != "UNRESOLVED" and not claims):
            raise GenerationFormatFailure("grounded turn requires claim-level typing")
        if value["statement_type"] == "UNRESOLVED" and claims:
            raise GenerationFormatFailure("abstention cannot contain claims")
        for claim in claims:
            if (not isinstance(claim, dict) or not isinstance(claim.get("text"), str)
                    or not claim["text"].strip() or claim.get("statement_type") not in STATEMENT_TYPES - {"UNRESOLVED"}
                    or not isinstance(claim.get("support_ids"), list)
                    or not claim["support_ids"] or not set(claim["support_ids"]) <= set(value["support_ids"])):
                raise GenerationFormatFailure("invalid claim-level support or type")
        if value["statement_type"] == "AUTHOR_CLAIM" and any(
                claim["statement_type"] != "AUTHOR_CLAIM" for claim in claims):
            raise GenerationFormatFailure("derived claim cannot be typed as whole-turn AUTHOR_CLAIM")
    return value

class CodexExecAdapter(ModelAdapter):
    """Fresh, schema constrained Codex CLI invocations using existing authentication."""
    provider = "codex-exec"

    def __init__(self, model: str = "gpt-6-sol", executable: str = "codex", timeout: int = 180):
        self.model, self.executable, self.timeout = model, executable, timeout

    def available(self) -> bool:
        return shutil.which(self.executable) is not None and SCHEMA_PATH.is_file()

    def generate_typed_turn(self, *, system_contract: str, payload: dict[str, Any]) -> ModelResult:
        if not self.available():
            raise ModelRuntimeUnavailable("codex exec or typed-turn schema unavailable")
        canonical = json.dumps({"system_contract": system_contract, "input": payload}, ensure_ascii=False, sort_keys=True)
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        error = ""
        for attempt in range(2):
            instruction = "\nReturn exactly one object matching every schema field. No tools, skills, or session state."
            if attempt:
                instruction += "\nSTRICT RETRY: all required typed-turn fields must be present with correct JSON types; use empty arrays and null only where allowed."
            prompt = canonical + instruction
            with tempfile.TemporaryDirectory(prefix="p2h-codex-exec-") as temp:
                output = Path(temp) / "turn.json"
                argv = [self.executable, "exec", "--ephemeral", "--skip-git-repo-check",
                        "--ignore-user-config", "--ignore-rules", "-s", "read-only", "-m", self.model,
                        "--output-schema", str(SCHEMA_PATH), "-o", str(output), prompt]
                try:
                    completed = subprocess.run(argv, cwd=temp, stdin=subprocess.DEVNULL,
                                               capture_output=True, text=True, timeout=self.timeout, check=False)
                except (OSError, subprocess.TimeoutExpired) as exc:
                    raise ModelRuntimeUnavailable(f"codex exec invocation failed: {type(exc).__name__}", attempt + 1) from exc
                if completed.returncode != 0:
                    raise ModelRuntimeUnavailable(f"codex exec exited {completed.returncode}", attempt + 1)
                try:
                    value = validate_typed_turn(json.loads(output.read_text(encoding="utf-8")))
                except (OSError, ValueError, TypeError) as exc:
                    error = str(exc)
                    continue
                return ModelResult(json.dumps(value, ensure_ascii=False), self.provider, self.model,
                                   {"ephemeral": True, "sandbox": "read-only", "attempts": attempt + 1}, digest)
        raise GenerationFormatFailure(f"GENERATION_FORMAT_FAILURE after two attempts: {error}", 2)

class OpenAICompatibleAdapter(ModelAdapter):
    """Use an already-authorized OpenAI-compatible HTTP endpoint.

    No credentials are discovered, scraped, or persisted. The caller must supply
    endpoint/model and optionally an existing environment-variable name.
    """
    def __init__(self, base_url: str, model: str, api_key_env: str | None = None,
                 temperature: float = 0.0, top_p: float = 1.0):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.provider = "openai-compatible"
        self.api_key_env = api_key_env
        self.temperature = temperature
        self.top_p = top_p

    def available(self) -> bool:
        if not self.base_url or not self.model:
            return False
        if self.api_key_env and not os.environ.get(self.api_key_env):
            return False
        try:
            req = urllib.request.Request(self.base_url + "/v1/models")
            if self.api_key_env:
                req.add_header("Authorization", "Bearer " + os.environ[self.api_key_env])
            with urllib.request.urlopen(req, timeout=3) as resp:
                return 200 <= resp.status < 300
        except Exception:
            return False

    def generate_typed_turn(self, *, system_contract: str, payload: dict[str, Any]) -> ModelResult:
        if not self.available():
            raise ModelRuntimeUnavailable("configured live model runtime is not available")
        prompt = json.dumps({"system_contract": system_contract, "input": payload},
                            ensure_ascii=False, sort_keys=True)
        body = json.dumps({
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_contract},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
            ],
            "temperature": self.temperature,
            "top_p": self.top_p,
            "response_format": {"type": "json_object"},
        }).encode()
        req = urllib.request.Request(self.base_url + "/v1/chat/completions", data=body,
                                     headers={"Content-Type": "application/json"})
        if self.api_key_env:
            req.add_header("Authorization", "Bearer " + os.environ[self.api_key_env])
        error = ""
        for attempt in range(2):
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
            try:
                value = validate_typed_turn(json.loads(data["choices"][0]["message"]["content"]))
            except (ValueError, TypeError, KeyError, IndexError) as exc:
                error = str(exc)
                continue
            return ModelResult(json.dumps(value, ensure_ascii=False), self.provider, self.model,
                               {"temperature": self.temperature, "top_p": self.top_p, "attempts": attempt + 1},
                               hashlib.sha256(prompt.encode()).hexdigest())
        raise GenerationFormatFailure(f"GENERATION_FORMAT_FAILURE after two attempts: {error}", 2)

def require_live_adapter(adapter: ModelAdapter) -> None:
    if not adapter.available():
        raise ModelRuntimeUnavailable("PHASE3_STATUS=BLOCKED_NO_LIVE_MODEL_RUNTIME")
