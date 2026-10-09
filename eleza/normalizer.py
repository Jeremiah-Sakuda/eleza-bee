"""
Term Normalization Engine (ELZ-105, INV-4)
Deterministic fuzzy and multi-token matching against unit glossaries.
Normalizes spoken transcription artifacts (e.g. 'phospho fructo kinase' -> 'phosphofructokinase')
before semantic alignment.
"""

from __future__ import annotations
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from rapidfuzz import fuzz, utils

@dataclass
class NormalizationResult:
    original_text: str
    normalized_text: str
    replacements: list[dict] = field(default_factory=list)

    @property
    def replacement_count(self) -> int:
        return len(self.replacements)

    @property
    def correction_rate(self) -> float:
        words = len(self.original_text.split())
        return (self.replacement_count / words) if words > 0 else 0.0

class TermNormalizer:
    def __init__(self, glossary: list[str] | set[str]):
        self.raw_glossary = sorted(list(glossary), key=len, reverse=True)
        # Create canonical lookup keys
        # We index both stripped/squashed versions (e.g. 'phosphofructokinase' -> 'phosphofructokinase')
        self.glossary_map = {}
        for term in self.raw_glossary:
            squashed = self._squash(term)
            self.glossary_map[squashed] = term

        # Pre-compile spoken phrase aliases for biochemical naming
        self.spoken_aliases = {
            "nad plus": "NAD+",
            "n a d plus": "NAD+",
            "nad+": "NAD+",
            "nadh": "NADH",
            "n a d h": "NADH",
            "atp": "ATP",
            "a t p": "ATP",
            "adp": "ADP",
            "a d p": "ADP",
            "pep": "phosphoenolpyruvate",
            "p e p": "phosphoenolpyruvate",
            "g3p": "glyceraldehyde-3-phosphate",
            "g 3 p": "glyceraldehyde-3-phosphate",
            "dhap": "dihydroxyacetone phosphate",
            "d h a p": "dihydroxyacetone phosphate",
            "fructose 1 6 bisphosphate": "fructose-1,6-bisphosphate",
            "fructose one six bisphosphate": "fructose-1,6-bisphosphate",
            "fructose 1,6 bisphosphate": "fructose-1,6-bisphosphate",
            "glucose 6 phosphate": "glucose-6-phosphate",
            "glucose six phosphate": "glucose-6-phosphate",
            "1 3 bisphosphoglycerate": "1,3-bisphosphoglycerate",
            "one three bisphosphoglycerate": "1,3-bisphosphoglycerate",
            "3 phosphoglycerate": "3-phosphoglycerate",
            "three phosphoglycerate": "3-phosphoglycerate",
            "2 phosphoglycerate": "2-phosphoglycerate",
            "two phosphoglycerate": "2-phosphoglycerate",
        }

    @staticmethod
    def _squash(s: str) -> str:
        """Strip hyphens, numbers, punctuation, spaces, and lowercase."""
        return re.sub(r'[^a-zA-Z0-9]', '', s).lower()

    @classmethod
    def from_json(cls, json_path: str | Path) -> TermNormalizer:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(data.get("glossary", []))

    def normalize(self, text: str, threshold: float = 85.0) -> NormalizationResult:
        normalized = text
        replacements = []

        # 1. Spoken aliases matching (case-insensitive boundary matching)
        for alias, canonical in sorted(self.spoken_aliases.items(), key=lambda x: len(x[0]), reverse=True):
            pattern = re.compile(rf'\b{re.escape(alias)}\b', re.IGNORECASE)
            for m in pattern.finditer(normalized):
                replacements.append({
                    "original": m.group(0),
                    "canonical": canonical,
                    "method": "alias_exact",
                    "score": 100.0,
                })
            normalized = pattern.sub(canonical, normalized)

        # 2. Sliding window n-gram matching for multi-token words (e.g. 'phospho fructo kinase' -> 'phosphofructokinase')
        # We check n-grams of lengths 4 down to 1
        words = normalized.split()
        if not words:
            return NormalizationResult(text, text, [])

        i = 0
        new_words = []
        while i < len(words):
            matched = False
            # Try combining up to 4 consecutive tokens
            for window_size in range(min(4, len(words) - i), 0, -1):
                chunk = words[i:i + window_size]
                chunk_str = " ".join(chunk)
                # Clean punctuation for matching
                clean_chunk = re.sub(r'[^\w\s]', '', chunk_str).strip()
                squashed_chunk = self._squash(clean_chunk)

                if not squashed_chunk or len(squashed_chunk) < 4:
                    continue

                # Check exact squashed match in glossary
                if squashed_chunk in self.glossary_map:
                    canonical = self.glossary_map[squashed_chunk]
                    # Preserve trailing punctuation if any (e.g. comma, period)
                    trailing_punct = re.search(r'[.,!?;:]+$', chunk[-1])
                    punct_suffix = trailing_punct.group(0) if trailing_punct else ""

                    replacement_term = canonical + punct_suffix
                    if chunk_str.strip() != replacement_term.strip():
                        replacements.append({
                            "original": chunk_str,
                            "canonical": replacement_term,
                            "method": "squashed_exact",
                            "score": 100.0,
                        })
                    new_words.append(replacement_term)
                    i += window_size
                    matched = True
                    break

                # Fuzzy match against squashed glossary terms for longer terms (> 7 chars)
                if len(squashed_chunk) > 7:
                    best_match = None
                    best_score = 0.0
                    for squashed_glossary, canonical in self.glossary_map.items():
                        score = fuzz.ratio(squashed_chunk, squashed_glossary)
                        if score > best_score and score >= threshold:
                            best_score = score
                            best_match = canonical

                    if best_match and best_score >= threshold:
                        trailing_punct = re.search(r'[.,!?;:]+$', chunk[-1])
                        punct_suffix = trailing_punct.group(0) if trailing_punct else ""
                        replacement_term = best_match + punct_suffix
                        replacements.append({
                            "original": chunk_str,
                            "canonical": replacement_term,
                            "method": "fuzzy_match",
                            "score": round(best_score, 1),
                        })
                        new_words.append(replacement_term)
                        i += window_size
                        matched = True
                        break

            if not matched:
                new_words.append(words[i])
                i += 1

        final_text = " ".join(new_words)
        return NormalizationResult(
            original_text=text,
            normalized_text=final_text,
            replacements=replacements,
        )
