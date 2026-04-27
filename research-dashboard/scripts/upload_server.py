from __future__ import annotations

from flask import Flask, jsonify, request
from add_paper_entry import append_record, build_record
from author_profiles import load_records_from_csv, write_author_outputs
from add_paper_entry import CSV_PATH

app = Flask(__name__)
AUTHOR_PROFILES_PATH = CSV_PATH.parent / "author_profiles.json"
WHITESPACE_MATCHES_PATH = CSV_PATH.parent / "whitespace_matches.json"

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
        write_author_outputs(records, AUTHOR_PROFILES_PATH, WHITESPACE_MATCHES_PATH)
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
