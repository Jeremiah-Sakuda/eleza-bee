"""
Unit tests for TermNormalizer (ELZ-105, D2)
"""

import pytest
from eleza.normalizer import TermNormalizer

GLOSSARY = [
    "glycolysis",
    "glucose",
    "pyruvate",
    "hexokinase",
    "phosphofructokinase",
    "fructose-1,6-bisphosphate",
    "dihydroxyacetone phosphate",
    "glyceraldehyde-3-phosphate",
    "glyceraldehyde-3-phosphate dehydrogenase",
    "phosphoglycerate kinase",
    "phosphoenolpyruvate",
    "ATP",
    "ADP",
    "NAD+",
    "NADH",
]

@pytest.fixture
def normalizer():
    return TermNormalizer(GLOSSARY)

def test_multi_token_squash(normalizer):
    # 'phospho fructo kinase' -> 'phosphofructokinase'
    res = normalizer.normalize("The enzyme phospho fructo kinase consumes an ATP molecule.")
    assert "phosphofructokinase" in res.normalized_text
    assert res.replacement_count >= 1

def test_alias_matching(normalizer):
    res = normalizer.normalize("NAD plus is reduced to NADH while ADP becomes ATP.")
    assert "NAD+" in res.normalized_text
    assert "NADH" in res.normalized_text
    assert "ADP" in res.normalized_text
    assert "ATP" in res.normalized_text

def test_hyphenated_multiword(normalizer):
    res = normalizer.normalize("Aldolase breaks fructose 1 6 bisphosphate into two sugars.")
    assert "fructose-1,6-bisphosphate" in res.normalized_text

def test_punctuation_preservation(normalizer):
    res = normalizer.normalize("First step uses hexo kinase, then isomerase.")
    assert "hexokinase," in res.normalized_text

def test_fuzzy_slight_misspell(normalizer):
    res = normalizer.normalize("The pathway generates phospho enol pyruvat before pyruvate.")
    assert "phosphoenolpyruvate" in res.normalized_text
