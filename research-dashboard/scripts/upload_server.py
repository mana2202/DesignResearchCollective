from __future__ import annotations

import os
import secrets
import threading

from flask import Flask, jsonify, request

from add_paper_entry import CSV_PATH, append_record, build_record
from author_profiles import load_records_from_csv, write_analysis_outputs

app = Flask(__name__)
PAPERS_ENRICHED_PATH = CSV_PATH.parent / "papers_enriched.json"
AUTHOR_PROFILES_PATH = CSV_PATH.parent / "author_profiles.json"
WHITESPACE_OPPORTUNITIES_PATH = CSV_PATH.parent / "whitespace_opportunities.json"
WHITESPACE_MATCHES_PATH = CSV_PATH.parent / "whitespace_matches.json"
PROPOSAL_ANALYSIS_CACHE_PATH = CSV_PATH.parent / "proposal_analysis_cache.json"

_API_KEY = os.environ.get("UPLOAD_API_KEY") or ""
if not _API_KEY:
    _API_KEY = secrets.token_urlsafe(24)
    print(f"[upload_server] No UPLOAD_API_KEY env var set. Using generated key: {_API_KEY}", flush=True)


def _check_auth() -> bool:
    return request.headers.get("X-Api-Key", "") == _API_KEY


def _rebuild_artifacts() -> None:
    try:
        records = load_records_from_csv(CSV_PATH)
        write_analysis_outputs(
            records,
            papers_enriched_path=PAPERS_ENRICHED_PATH,
            author_profiles_path=AUTHOR_PROFILES_PATH,
            whitespace_opportunities_path=WHITESPACE_OPPORTUNITIES_PATH,
            whitespace_matches_path=WHITESPACE_MATCHES_PATH,
        )
        PROPOSAL_ANALYSIS_CACHE_PATH.write_text("[]", encoding="utf-8")
        print("[upload_server] Artifact rebuild complete.", flush=True)
    except Exception as exc:
        print(f"[upload_server] Background artifact rebuild failed: {exc}", flush=True)


@app.get('/api/health')
def health():
    return jsonify({'ok': True})


@app.post('/api/upload-paper')
def upload_paper():
    if not _check_auth():
        return jsonify({'ok': False, 'error': 'Unauthorized'}), 401
    try:
        payload = request.get_json(force=True, silent=False) or {}
        rec = build_record(payload)
        append_record(rec)
    except ValueError as e:
        return jsonify({'ok': False, 'error': str(e)}), 400
    except Exception:
        return jsonify({'ok': False, 'error': 'Failed to process paper'}), 500
    threading.Thread(target=_rebuild_artifacts, daemon=True).start()
    return jsonify({
        'ok': True,
        'title': rec['title'],
        'primary_category': rec['primary_category'],
        'categories': rec['categories'],
        'note': 'Analysis artifacts are rebuilding in the background.',
    })


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8081)
