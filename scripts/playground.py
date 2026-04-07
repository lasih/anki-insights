import spacy
from spacy.lang.id.stop_words import STOP_WORDS

nlp = spacy.blank("id")

doc = nlp("aku tidak mau pergi ke sana")

tokens = [token.text for token in doc if token.text.lower() not in STOP_WORDS]

print(tokens)
