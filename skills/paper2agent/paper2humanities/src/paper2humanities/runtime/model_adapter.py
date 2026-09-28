from __future__ import annotations
from dataclasses import dataclass
from typing import Any
import hashlib, json, os, urllib.request

class ModelRuntimeUnavailable(RuntimeError):
    pass

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
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
        text = data["choices"][0]["message"]["content"]
        return ModelResult(text, self.provider, self.model,
                           {"temperature": self.temperature, "top_p": self.top_p},
                           hashlib.sha256(prompt.encode()).hexdigest())

def require_live_adapter(adapter: ModelAdapter) -> None:
    if not adapter.available():
        raise ModelRuntimeUnavailable("PHASE3_STATUS=BLOCKED_NO_LIVE_MODEL_RUNTIME")
