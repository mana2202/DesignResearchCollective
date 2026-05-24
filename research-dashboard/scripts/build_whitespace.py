from __future__ import annotations

from pathlib import Path

from author_profiles import load_records_from_csv, write_analysis_outputs


ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
PAPERS_CSV_PATH = DATA_DIR / "papers.csv"
PAPERS_ENRICHED_PATH = DATA_DIR / "papers_enriched.json"
AUTHOR_PROFILES_PATH = DATA_DIR / "author_profiles.json"
WHITESPACE_OPPORTUNITIES_PATH = DATA_DIR / "whitespace_opportunities.json"
WHITESPACE_MATCHES_PATH = DATA_DIR / "whitespace_matches.json"


def main() -> None:
    records = load_records_from_csv(PAPERS_CSV_PATH)
    _, _, whitespace_count = write_analysis_outputs(
        records,
        papers_enriched_path=PAPERS_ENRICHED_PATH,
        author_profiles_path=AUTHOR_PROFILES_PATH,
        whitespace_opportunities_path=WHITESPACE_OPPORTUNITIES_PATH,
        whitespace_matches_path=WHITESPACE_MATCHES_PATH,
    )
    print(f"Generated {WHITESPACE_OPPORTUNITIES_PATH.name} with {whitespace_count} whitespace opportunities.")
    print(f"Updated legacy mirror {WHITESPACE_MATCHES_PATH.name} for dashboard compatibility.")


if __name__ == "__main__":
    main()
