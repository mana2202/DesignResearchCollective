from __future__ import annotations

from flask import Flask, jsonify, request
from add_paper_entry import append_record, build_record
from author_profiles import load_records_from_csv, write_analysis_outputs
from add_paper_entry import CSV_PATH

app = Flask(__name__)
PAPERS_ENRICHED_PATH = CSV_PATH.parent / "papers_enriched.json"
AUTHOR_PROFILES_PATH = CSV_PATH.parent / "author_profiles.json"
WHITESPACE_OPPORTUNITIES_PATH = CSV_PATH.parent / "whitespace_opportunities.json"
WHITESPACE_MATCHES_PATH = CSV_PATH.parent / "whitespace_matches.json"
PROPOSAL_ANALYSIS_CACHE_PATH = CSV_PATH.parent / "proposal_analysis_cache.json"

@app.get('/api/health')
def health():
    return jsonify({'ok': True})

@app.post('/api/upload-paper')
def upload_paper():
    try:
        payload = request.get_json(force=True, silent=False) or {}
        rec = build_record(payload)
        append_record(rec)
        records = load_records_from_csv(CSV_PATH)
        write_analysis_outputs(
            records,
            papers_enriched_path=PAPERS_ENRICHED_PATH,
            author_profiles_path=AUTHOR_PROFILES_PATH,
            whitespace_opportunities_path=WHITESPACE_OPPORTUNITIES_PATH,
            whitespace_matches_path=WHITESPACE_MATCHES_PATH,
        )
        PROPOSAL_ANALYSIS_CACHE_PATH.write_text("[]", encoding="utf-8")
        return jsonify({
            'ok': True,
            'title': rec['title'],
            'primary_category': rec['primary_category'],
            'categories': rec['categories'],
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 400

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8081)
