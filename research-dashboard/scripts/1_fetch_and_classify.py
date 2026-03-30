"""
1_fetch_and_classify.py

Fetches papers from two HuggingFace datasets, uses Claude to extract
keywords and classify each paper, then outputs data/papers.csv.

Usage:
    export ANTHROPIC_API_KEY=your_key_here
    python scripts/1_fetch_and_classify.py
"""

import os
import json
import time
import re
import pandas as pd
from datasets import load_dataset
from tqdm import tqdm
import anthropic

# ── Config ────────────────────────────────────────────────────────────────────

DATASETS = [
    {"hf_id": "ccm/publications",               "source": "CCM Lab"},
    {"hf_id": "ccm/cmu-engineering-publications","source": "CMU Engineering"},
]

CATEGORIES = ["ideation", "optimization", "grammar", "decision_making"]

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "papers.csv")

# How many papers to classify per API call (batching saves tokens)
BATCH_SIZE = 5

# ── Helpers ───────────────────────────────────────────────────────────────────

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def extract_bib_fields(row: dict, source: str) -> dict:
    """Pull title, authors, year, abstract from a dataset row."""
    # Dataset 1: bib_dict column (rich structured data)
    if "bib_dict" in row and isinstance(row["bib_dict"], dict):
        bd = row["bib_dict"]
        return {
            "title":    bd.get("title", "").strip(),
            "authors":  bd.get("author", "").strip(),
            "year":     bd.get("pub_year") or "",
            "abstract": bd.get("abstract", "").strip(),
            "journal":  (bd.get("journal") or bd.get("conference") or "").strip(),
            "url":      row.get("pub_url", "") or "",
            "citations":row.get("num_citations", 0) or 0,
            "source":   source,
        }

    # Dataset 2: flat columns
    return {
        "title":    str(row.get("title", "")).strip(),
        "authors":  str(row.get("faculty", "")).strip(),
        "year":     str(row.get("pub_year", "")).strip()[:4],
        "abstract": "",
        "journal":  str(row.get("citation", "")).strip(),
        "url":      "",
        "citations":int(row.get("num_citations", 0) or 0),
        "source":   source,
        "department": str(row.get("department", "")).strip(),
    }


def classify_batch(papers: list[dict]) -> list[dict]:
    """
    Send a batch of papers to Claude for keyword extraction + categorisation.
    Returns a list of dicts with 'keywords' and 'categories' keys.
    """
    items = []
    for i, p in enumerate(papers):
        items.append(
            f"[{i}] TITLE: {p['title']}\n"
            f"    ABSTRACT: {p['abstract'][:400] if p['abstract'] else '(none)'}"
        )

    prompt = f"""You are a research taxonomy assistant. For each paper below, extract:
1. keywords: 5–8 concise topic keywords (lowercase, comma-separated)
2. categories: which of these apply: ideation, optimization, grammar, decision_making
   - ideation: concept generation, brainstorming, creative design, design exploration
   - optimization: computational optimization, performance improvement, machine learning for design
   - grammar: design grammars, rule-based systems, shape grammars, structured representations
   - decision_making: decision support, agent-based systems, human factors, team dynamics, strategy

A paper can belong to multiple categories. If none clearly apply, use the closest match.

Return ONLY a JSON array (no markdown, no explanation) with one object per paper:
[
  {{"index": 0, "keywords": "keyword1, keyword2, ...", "categories": ["ideation","optimization"]}},
  ...
]

Papers:
{chr(10).join(items)}"""

    for attempt in range(3):
        try:
            msg = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = msg.content[0].text.strip()
            # Strip markdown fences if present
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            results = json.loads(raw)
            return results
        except Exception as e:
            print(f"  ⚠️  Attempt {attempt+1} failed: {e}")
            time.sleep(2 ** attempt)

    # Fallback: return empty classifications
    return [{"index": i, "keywords": "", "categories": []} for i in range(len(papers))]


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    all_rows = []

    # 1. Load datasets
    for ds_config in DATASETS:
        print(f"\n📥  Loading {ds_config['hf_id']} ...")
        try:
            ds = load_dataset(ds_config["hf_id"], split="train")
            print(f"    → {len(ds)} rows")
            for row in ds:
                record = extract_bib_fields(dict(row), ds_config["source"])
                if record["title"]:  # Skip blank titles
                    all_rows.append(record)
        except Exception as e:
            print(f"    ✗ Failed to load: {e}")

    print(f"\n✅  Loaded {len(all_rows)} papers total")

    # 2. Classify in batches
    print(f"\n🤖  Classifying with Claude (batch size={BATCH_SIZE}) ...")
    for i in tqdm(range(0, len(all_rows), BATCH_SIZE)):
        batch = all_rows[i : i + BATCH_SIZE]
        results = classify_batch(batch)

        result_map = {r["index"]: r for r in results}
        for j, record in enumerate(batch):
            res = result_map.get(j, {})
            record["keywords"]   = res.get("keywords", "")
            record["categories"] = ", ".join(res.get("categories", []))

        # Small delay to respect rate limits
        time.sleep(0.3)

    # 3. Build DataFrame and save
    df = pd.DataFrame(all_rows)

    # Normalise year to int where possible
    def parse_year(y):
        try:
            return int(str(y)[:4])
        except Exception:
            return None

    df["year"] = df["year"].apply(parse_year)
    df = df.sort_values("year", ascending=False, na_position="last")

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    df.to_csv(OUTPUT_PATH, index=False)
    print(f"\n💾  Saved {len(df)} rows → {OUTPUT_PATH}")
    print(df[["title","year","categories","keywords"]].head(5).to_string())


if __name__ == "__main__":
    main()
