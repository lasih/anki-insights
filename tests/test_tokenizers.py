from anki_insights.tokenizers import (
    IndonesianTokenizer,
    MandarinTokenizer,
    SpacyTokenizer,
)


def test_spacy_tokenizer_french():
    tokenizer = SpacyTokenizer("fr_core_news_sm")
    tokens = tokenizer.tokenize("Bonjour, je m'appelle Jean.")
    assert "bonjour" in tokens
    assert "je" in tokens
    assert "m'" not in tokens
    assert "appeler" in tokens


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
