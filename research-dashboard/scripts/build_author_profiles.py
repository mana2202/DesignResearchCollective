from __future__ import annotations

import json
from pathlib import Path

from author_profiles import load_records_from_csv, write_analysis_outputs


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
PAPERS_CSV_PATH = DATA_DIR / "papers.csv"
PAPERS_ENRICHED_PATH = DATA_DIR / "papers_enriched.json"
AUTHOR_PROFILES_PATH = DATA_DIR / "author_profiles.json"
WHITESPACE_OPPORTUNITIES_PATH = DATA_DIR / "whitespace_opportunities.json"
WHITESPACE_MATCHES_PATH = DATA_DIR / "whitespace_matches.json"
PROPOSAL_ANALYSIS_CACHE_PATH = DATA_DIR / "proposal_analysis_cache.json"


def main() -> None:
    records = load_records_from_csv(PAPERS_CSV_PATH)
    paper_count, profile_count, whitespace_count = write_analysis_outputs(
        records,
        papers_enriched_path=PAPERS_ENRICHED_PATH,
        author_profiles_path=AUTHOR_PROFILES_PATH,
        whitespace_opportunities_path=WHITESPACE_OPPORTUNITIES_PATH,
        whitespace_matches_path=WHITESPACE_MATCHES_PATH,
    )
    if not PROPOSAL_ANALYSIS_CACHE_PATH.exists():
        PROPOSAL_ANALYSIS_CACHE_PATH.write_text("[]\n", encoding="utf-8")

    print(f"Generated {PAPERS_ENRICHED_PATH.name} with {paper_count} enriched papers.")
    print(f"Generated {AUTHOR_PROFILES_PATH.name} with {profile_count} author profiles.")
    print(f"Generated {WHITESPACE_OPPORTUNITIES_PATH.name} with {whitespace_count} whitespace opportunities.")
    if profile_count == 0:
        print("Warning: no author data was available; author_profiles.json contains [].")
    if not json.loads(PROPOSAL_ANALYSIS_CACHE_PATH.read_text(encoding="utf-8")):
        print(f"Ensured {PROPOSAL_ANALYSIS_CACHE_PATH.name} exists.")


if __name__ == "__main__":
    main()
