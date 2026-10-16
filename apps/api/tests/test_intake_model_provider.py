"""The model-backed provider and its router: the model's answer is validated like the agent's
tool, who ran is stamped by the harness, the backend is swapped by configuration, and a
deployment without a key or with an external endpoint in production gets a refusal, not a
fallback. No model is called: the backends are exercised against a recorded transport."""

from __future__ import annotations

import json
from dataclasses import dataclass, field

import httpx
import pytest

from hadp_api.config import get_settings
from hadp_api.modules.intake import model_provider as mp
from hadp_api.modules.intake.pages import load_pages
from hadp_api.modules.intake.providers import TextLayerProvider, get_provider
from tests.intake_support import CASES_DIR

PDF = (CASES_DIR / "01_a_nord_all_green" / "input" / "report.pdf").read_bytes()
GOOD_ANSWER = json.dumps(
    {
        "patient_date_of_birth": "1970-03-12",
        "issue_date": "2026-09-06",
        "values": [
            {
                "analyte_text": "HbA1c",
                "value_text": "5,4",
                "unit_text": "%",
                "observed_at": "2026-09-05",
                "observed_at_is_date_only": True,
                "reference_low": "4,0",
                "reference_high": "6,0",
                "reference_text": "4,0 - 6,0",
                "page": 1,
                "bbox": None,
                "confidence": 0.97,
            }
        ],
    }
)


@dataclass
class FakeBackend:
    answer: str
    calls: list[dict[str, object]] = field(default_factory=list)

    @property
    def name(self) -> str:
        return "fake"

    @property
    def model_id(self) -> str:
        return "fake-model-1"

    def complete(self, system: str, user_text: str, images: list[bytes]) -> str:
        self.calls.append({"system": system, "user": user_text, "images": len(images)})
        return self.answer


def _pages():  # type: ignore[no-untyped-def]
    return load_pages(PDF, get_settings())


def test_a_fitting_answer_becomes_a_proposal_stamped_by_the_harness() -> None:
    backend = FakeBackend(GOOD_ANSWER)
    provider = mp.ModelProvider(backend)
    proposal = provider.extract(PDF, _pages())
    assert proposal.extraction_provider == "model"
    assert proposal.model_id == "fake:fake-model-1"
    assert proposal.prompt_version == mp.PROMPT_VERSION == "intake-extract-1"
    assert proposal.patient_date_of_birth is not None and proposal.values[0].value_text == "5,4"
    [call] = backend.calls
    assert call["images"] == 1  # one page image
    assert "page 1 (text source: text_layer)" in str(call["user"])
    assert "HbA1c 5,4 %" in str(call["user"])
    assert "transcribe the printed results and nothing else" in " ".join(
        str(call["system"]).split()
    )


def test_a_code_fenced_answer_is_accepted_and_free_text_is_not() -> None:
    fenced = f"```json\n{GOOD_ANSWER}\n```"
    assert mp.ModelProvider(FakeBackend(fenced)).extract(PDF, _pages()).values[0].page == 1
    with pytest.raises(mp.ModelOutputInvalid, match="not_json"):
        mp.ModelProvider(FakeBackend("Here are the values: HbA1c 5,4 %")).extract(PDF, _pages())
    with pytest.raises(mp.ModelOutputInvalid, match="not_an_object"):
        mp.ModelProvider(FakeBackend("[1, 2]")).extract(PDF, _pages())


@pytest.mark.parametrize(
    ("poison", "match"),
    [
        ({"status": "green"}, "unexpected_fields:status"),
        ({"model_id": "gpt-x"}, "model_set_model_id"),
        ({"extraction_provider": "trusted"}, "model_set_extraction_provider"),
    ],
)
def test_an_answer_that_sets_what_the_harness_stamps_is_refused_whole(poison, match) -> None:  # type: ignore[no-untyped-def]
    data = json.loads(GOOD_ANSWER)
    data.update(poison)
    with pytest.raises(mp.ModelOutputInvalid, match=match):
        mp.ModelProvider(FakeBackend(json.dumps(data))).extract(PDF, _pages())


def test_a_value_with_a_status_or_a_kpi_is_refused_and_the_detail_names_no_content() -> None:
    data = json.loads(GOOD_ANSWER)
    data["values"][0]["status"] = "green"
    data["values"][0]["kpi_code"] = "metabolic.hba1c"
    with pytest.raises(mp.ModelOutputInvalid) as err:
        mp.ModelProvider(FakeBackend(json.dumps(data))).extract(PDF, _pages())
    assert "extra_forbidden" in err.value.detail
    assert "5,4" not in err.value.detail and "HbA1c" not in err.value.detail


def test_the_anthropic_backend_sends_images_text_and_the_model_and_reads_the_text_back() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["key"] = request.headers.get("x-api-key")
        body = json.loads(request.content)
        seen["model"] = body["model"]
        seen["system"] = body["system"]
        seen["blocks"] = [b["type"] for b in body["messages"][0]["content"]]
        return httpx.Response(
            200,
            json={
                "content": [
                    {"type": "text", "text": "ignored "},
                    {"type": "text", "text": GOOD_ANSWER},
                ]
            },
        )

    backend = mp.AnthropicBackend(
        api_key="test-key",
        model="claude-haiku-5-5",
        base_url="https://api.example.test",
        transport=httpx.MockTransport(handler),
    )
    answer = backend.complete("SYS", "USER", [b"\x89PNG\r\n\x1a\nxx"])
    assert answer.endswith(GOOD_ANSWER)
    assert seen["url"] == "https://api.example.test/v1/messages"
    assert seen["key"] == "test-key" and seen["model"] == "claude-haiku-5-5"
    assert seen["system"] == "SYS" and seen["blocks"] == ["image", "text"]


def test_the_openai_compatible_backend_speaks_chat_completions_without_a_key() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        body = json.loads(request.content)
        seen["roles"] = [m["role"] for m in body["messages"]]
        seen["parts"] = [p["type"] for p in body["messages"][1]["content"]]
        seen["temperature"] = body["temperature"]
        return httpx.Response(200, json={"choices": [{"message": {"content": GOOD_ANSWER}}]})

    backend = mp.OpenAICompatibleBackend(
        base_url="http://127.0.0.1:11434/v1",
        model="qwen2.5vl:7b",
        transport=httpx.MockTransport(handler),
    )
    assert (
        backend.complete("SYS", "USER", [b"\x89PNG\r\n\x1a\nxx", b"\x89PNG\r\n\x1a\nyy"])
        == GOOD_ANSWER
    )
    assert seen["url"] == "http://127.0.0.1:11434/v1/chat/completions"
    assert seen["auth"] is None and seen["roles"] == ["system", "user"]
    assert seen["parts"] == ["image_url", "image_url", "text"] and seen["temperature"] == 0


def test_a_backend_error_is_raised_not_swallowed() -> None:
    backend = mp.AnthropicBackend(
        api_key="k",
        model="m",
        base_url="https://api.example.test",
        transport=httpx.MockTransport(lambda _r: httpx.Response(529, json={"error": "overloaded"})),
    )
    with pytest.raises(httpx.HTTPStatusError):
        backend.complete("SYS", "USER", [])


# --- the router --------------------------------------------------------------------------------


def _settings(monkeypatch, **env: str):  # type: ignore[no-untyped-def]
    for key in (
        "INTAKE_PROVIDER",
        "INTAKE_MODEL_BACKEND",
        "INTAKE_MODEL_ID",
        "INTAKE_MODEL_BASE_URL",
        "INTAKE_MODEL_API_KEY",
        "ANTHROPIC_API_KEY",
        "INTAKE_MODEL_EXTERNAL_ALLOWED",
        "APP_ENV",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("APP_ENV", "test")
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    get_settings.cache_clear()
    return get_settings()


@pytest.fixture(autouse=True)
def _restore_settings():  # type: ignore[no-untyped-def]
    yield
    get_settings.cache_clear()


def test_the_default_provider_needs_no_model_and_the_model_provider_needs_a_key(
    monkeypatch,
) -> None:  # type: ignore[no-untyped-def]
    settings = _settings(monkeypatch)
    assert isinstance(get_provider(settings.intake_provider, settings), TextLayerProvider)
    settings = _settings(monkeypatch, INTAKE_PROVIDER="model", INTAKE_MODEL_ID="claude-haiku-5-5")
    with pytest.raises(mp.ProviderUnavailable, match="API_KEY"):
        get_provider("model", settings)
    settings = _settings(monkeypatch, INTAKE_PROVIDER="model", INTAKE_MODEL_BACKEND="anthropic")
    with pytest.raises(mp.ProviderUnavailable, match="INTAKE_MODEL_ID"):
        get_provider("model", settings)
    with pytest.raises(LookupError):
        get_provider("something-else", settings)


def test_the_backend_is_chosen_by_configuration(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    settings = _settings(
        monkeypatch,
        INTAKE_MODEL_BACKEND="anthropic",
        INTAKE_MODEL_ID="claude-haiku-5-5",
        ANTHROPIC_API_KEY="k",
    )
    provider = get_provider("model", settings)
    assert (
        isinstance(provider, mp.ModelProvider) and provider.model_id == "anthropic:claude-haiku-5-5"
    )
    settings = _settings(
        monkeypatch,
        INTAKE_MODEL_BACKEND="openai_compatible",
        INTAKE_MODEL_ID="qwen2.5vl:7b",
        INTAKE_MODEL_BASE_URL="http://127.0.0.1:11434/v1",
    )
    provider = get_provider("model", settings)
    assert (
        isinstance(provider, mp.ModelProvider)
        and provider.model_id == "openai_compatible:qwen2.5vl:7b"
    )
    settings = _settings(monkeypatch, INTAKE_MODEL_BACKEND="openai_compatible", INTAKE_MODEL_ID="x")
    with pytest.raises(mp.ProviderUnavailable, match="BASE_URL"):
        get_provider("model", settings)
    settings = _settings(monkeypatch, INTAKE_MODEL_BACKEND="other", INTAKE_MODEL_ID="x")
    with pytest.raises(mp.ProviderUnavailable, match="unknown INTAKE_MODEL_BACKEND"):
        get_provider("model", settings)


def test_in_production_an_external_endpoint_is_refused_until_the_vendor_decision_is_recorded() -> (
    None
):
    from hadp_api.config import Settings

    # A production configuration the settings' own guard accepts (config.py).
    base = {
        "app_env": "production",
        "intake_model_backend": "anthropic",
        "intake_model_id": "claude-haiku-5-5",
        "intake_model_api_key": "k",
        "session_secret": "x" * 40,
        "database_url": "postgresql+psycopg://postgres:x@db/hadp",
        "app_database_url": "postgresql+psycopg://hadp_app:x@db/hadp",
        "s3_access_key_id": "prod-key",
        "s3_secret_access_key": "prod-secret",
        "session_cookie_name": "__Host-hadp_session",
        "csrf_cookie_name": "__Host-hadp_csrf",
        "trusted_proxies": "10.0.0.1",
    }
    with pytest.raises(mp.ProviderUnavailable, match="EXTERNAL_ALLOWED"):
        mp.build_model_provider(Settings(**base))  # type: ignore[arg-type]
    provider = mp.build_model_provider(Settings(**base, intake_model_external_allowed=True))  # type: ignore[arg-type]
    assert isinstance(provider, mp.ModelProvider)
    local = mp.build_model_provider(
        Settings(  # type: ignore[arg-type]
            **{
                **base,
                "intake_model_backend": "openai_compatible",
                "intake_model_base_url": "http://127.0.0.1:8080/v1",
            }
        )
    )
    assert local.model_id.startswith("openai_compatible:")
