"""
OpenStax Biology 2e Source Ingestion Pipeline (ELZ-201, ELZ-202)
Parses Section 7.2 (Glycolysis) into structured passages with stable IDs,
headings, sentences, and biological glossary terms.
"""

from __future__ import annotations
import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

RAW_HTML_PATH = Path("/Users/jerem/.gemini/antigravity-ide/brain/f2699955-652f-4591-b507-fe21a2da6f75/.system_generated/steps/31/content.md")
OUTPUT_JSON_PATH = Path("data/openstax_bio2e_ch7.json")

# Core biochemical terms to ensure representation in unit glossary
KNOWN_BIO_TERMS = [
    "glycolysis",
    "glucose",
    "pyruvate",
    "hexokinase",
    "isomerase",
    "phosphofructokinase",
    "aldolase",
    "dihydroxyacetone-phosphate",
    "dihydroxyacetone phosphate",
    "glyceraldehyde-3-phosphate",
    "glyceraldehyde-3-phosphate dehydrogenase",
    "phosphoglycerate kinase",
    "phosphoglycerate mutase",
    "enolase",
    "pyruvate kinase",
    "phosphoenolpyruvate",
    "glucose-6-phosphate",
    "fructose-6-phosphate",
    "fructose-1,6-bisphosphate",
    "1,3-bisphosphoglycerate",
    "3-phosphoglycerate",
    "2-phosphoglycerate",
    "ATP",
    "ADP",
    "NAD+",
    "NADH",
    "substrate-level phosphorylation",
    "aerobic respiration",
    "anaerobic respiration",
    "mitochondria",
    "cytoplasm",
    "rate-limiting enzyme",
]

def split_sentences(text: str) -> list[str]:
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    # Sentence splitting avoiding periods inside abbreviations / decimals
    raw_sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z0-9])', text)
    return [s.strip() for s in raw_sentences if len(s.strip()) > 5]

def extract_passages():
    with open(RAW_HTML_PATH, "r", encoding="utf-8") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    
    current_section = "7.2 Glycolysis"
    current_subsection = "Introduction"
    passages = []
    passage_idx = 1
    unit_glossary = set(KNOWN_BIO_TERMS)

    for el in soup.find_all(["h2", "h3", "p"]):
        text = el.get_text().strip()
        if not text:
            continue
        # Skip noise / cookie notice / footer links
        if any(bad in text.lower() for bad in ["cookie", "privacy policy", "terms of use", "learning objectives", "by the end of this section"]):
            continue

        if el.name == "h2":
            current_section = re.sub(r'\s+', ' ', text)
        elif el.name == "h3":
            if "Link to Learning" in text or "References" in text:
                break
            current_subsection = re.sub(r'\s+', ' ', text)
        elif el.name == "p":
            if len(text) < 40 or ("Figure 7." in text and len(text) < 60):
                continue

            cleaned_text = re.sub(r'\s+', ' ', text)
            cleaned_text = cleaned_text.replace("underlinebiend underlinesphosphate", "bisphosphate")
            cleaned_text = cleaned_text.replace("underlinebiend underlines", "bis")
            sentences = split_sentences(cleaned_text)

            # Discover inline bold terms
            for bold in el.find_all(["strong", "b", "em"]):
                b_text = bold.get_text().strip()
                if 2 < len(b_text) < 45 and not b_text.startswith("Figure") and not b_text.startswith("Step"):
                    unit_glossary.add(b_text)

            passage_id = f"openstax-bio2e-7.2-p{passage_idx:02d}"
            passages.append({
                "passage_id": passage_id,
                "section": current_section,
                "subsection": current_subsection,
                "text": cleaned_text,
                "sentences": sentences,
                "token_count": len(cleaned_text.split()),
            })
            passage_idx += 1

    glossary_list = sorted(list(unit_glossary))

    data = {
        "source": "OpenStax Biology 2e",
        "license": "CC BY 4.0",
        "url": "https://openstax.org/books/biology-2e/pages/7-2-glycolysis",
        "chapter": 7,
        "section": "7.2",
        "title": "Glycolysis",
        "passage_count": len(passages),
        "glossary": glossary_list,
        "passages": passages,
    }

    OUTPUT_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as out:
        json.dump(data, out, indent=2)

    print(f"Ingested {len(passages)} passages into {OUTPUT_JSON_PATH}")
    print(f"Glossary contains {len(glossary_list)} terms")

if __name__ == "__main__":
    extract_passages()
