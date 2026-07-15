import pytest

from anki_insights.tokenizers import (
    IndonesianTokenizer,
    MandarinTokenizer,
    build_tokenizer,
)


def test_build_tokenizer_supports_french(monkeypatch):
    class DummySpacyTokenizer:
        def __init__(self, model_name: str) -> None:
            self.model_name = model_name

        def tokenize(self, text: str):
            return {"bonjour"}

    monkeypatch.setattr("anki_insights.tokenizers.SpacyTokenizer", DummySpacyTokenizer)
    tokenizer = build_tokenizer("fr")
    assert tokenizer.tokenize("Bonjour") == {"bonjour"}


def test_build_tokenizer_rejects_unsupported_language():
    with pytest.raises(ValueError, match="Unsupported language"):
        build_tokenizer("pt")


def test_indonesian_tokenizer():
    tokenizer = IndonesianTokenizer()
    tokens = tokenizer.tokenize("Saya makan nasi putih.")
    assert "saya" in tokens
    assert "makan" in tokens
    assert "nasi" in tokens
    assert "putih" in tokens


def test_mandarin_tokenizer():
    tokenizer = MandarinTokenizer(char_fallback=True)
    tokens = tokenizer.tokenize("你好，世界")
    assert "你好" in tokens or "你" in tokens
    assert "世界" in tokens
