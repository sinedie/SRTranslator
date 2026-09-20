import logging

import pytest

import srtranslator.translators.deepl_api as deepl_api
from srtranslator.translators.deepl_api import DeeplApi


class FakeTextResult:
    def __init__(self, text, billed_characters=0, model_type_used=None):
        self.text = text
        self.billed_characters = billed_characters
        self.model_type_used = model_type_used


class FakeClient:
    def __init__(self, api_key):
        self.api_key = api_key
        self.calls = []

    def translate_text(self, text, **kwargs):
        self.calls.append({"text": text, **kwargs})
        if isinstance(text, list):
            return [
                FakeTextResult(
                    f"translated {item}",
                    billed_characters=len(item),
                    model_type_used="quality_optimized",
                )
                for item in text
            ]
        return FakeTextResult(
            f"translated {text}",
            billed_characters=len(text),
            model_type_used="quality_optimized",
        )


@pytest.fixture
def fake_client(monkeypatch):
    created = []

    def factory(api_key):
        client = FakeClient(api_key)
        created.append(client)
        return client

    monkeypatch.setattr(deepl_api.deepl, "DeepLClient", factory)
    return created


def test_defaults_to_next_gen_model_and_auto_source(fake_client):
    translator = DeeplApi("key")
    translator.translate_single("Hello", "auto", "es")

    call = fake_client[0].calls[0]
    assert call["model_type"] == "quality_optimized"
    assert call["source_lang"] is None
    assert call["target_lang"] == "es"


def test_explicit_source_language_is_forwarded(fake_client):
    DeeplApi("key").translate_single("Hello", "en", "es")

    assert fake_client[0].calls[0]["source_lang"] == "en"


def test_global_and_chunk_context_are_joined(fake_client):
    translator = DeeplApi("key", context="A spy movie")
    translator.translate_single("Hello", "en", "es", context="Previous dialogue:\n1. Hi")

    assert fake_client[0].calls[0]["context"] == "A spy movie\n\nPrevious dialogue:\n1. Hi"


def test_context_omitted_when_empty(fake_client):
    DeeplApi("key").translate_single("Hello", "en", "es")

    assert "context" not in fake_client[0].calls[0]


@pytest.mark.parametrize("target", ["es", "en-GB", "ZH-HANS"])
def test_custom_instructions_forwarded_for_supported_targets(fake_client, target):
    translator = DeeplApi("key", custom_instructions=["Keep names untranslated"])
    translator.translate_single("Hello", "en", target)

    assert fake_client[0].calls[0]["custom_instructions"] == ["Keep names untranslated"]


def test_custom_instructions_dropped_for_unsupported_target(fake_client, caplog):
    translator = DeeplApi("key", custom_instructions=["Keep names untranslated"])

    with caplog.at_level(logging.WARNING, logger="srtranslator"):
        translator.translate_single("Hello", "en", "fi")
        translator.translate_single("Again", "en", "fi")

    assert "custom_instructions" not in fake_client[0].calls[0]
    # Warned once, not per chunk
    assert sum("custom instructions" in r.message.lower() for r in caplog.records) == 1


def test_custom_instructions_reject_latency_model(fake_client):
    with pytest.raises(ValueError, match="latency_optimized"):
        DeeplApi("key", model_type="latency_optimized", custom_instructions=["x"])


def test_too_many_custom_instructions_rejected(fake_client):
    with pytest.raises(ValueError, match="at most"):
        DeeplApi("key", custom_instructions=[f"rule {i}" for i in range(11)])


def test_overlong_custom_instruction_rejected(fake_client):
    with pytest.raises(ValueError, match="300"):
        DeeplApi("key", custom_instructions=["x" * 301])


def test_batch_returns_list_of_strings_and_sums_billed_characters(fake_client):
    translator = DeeplApi("key")
    result = translator.translate_batch(["one", "two"], "en", "es")

    assert result == ["translated one", "translated two"]
    assert translator.billed_characters == len("one") + len("two")


def test_translate_dispatches_list_to_batch(fake_client):
    translator = DeeplApi("key")

    assert translator.translate(["one"], "en", "es") == ["translated one"]
    assert isinstance(fake_client[0].calls[0]["text"], list)


def test_model_used_logged_once(fake_client, caplog):
    translator = DeeplApi("key")

    with caplog.at_level(logging.INFO, logger="srtranslator"):
        translator.translate_single("one", "en", "es")
        translator.translate_single("two", "en", "es")

    assert sum("DeepL model used" in r.message for r in caplog.records) == 1


def test_quit_without_any_call_does_not_raise(fake_client):
    DeeplApi("key").quit()
