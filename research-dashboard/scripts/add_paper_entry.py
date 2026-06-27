from __future__ import annotations

import csv
import fcntl
import sys
import threading
from pathlib import Path
from typing import Any

from transformers import pipeline

from category_classifier import (
    classify_categories,
    primary_category_from_multi,
    strip_topic_id,
)

MODEL_ID = "OpenAlex/bert-base-multilingual-cased-finetuned-openalex-topic-classification-title-abstract"
TOP_K = 8
CSV_PATH = Path(__file__).resolve().parents[1] / "data" / "papers.csv"
DRC_HF_DATASET = "ccm/publications"
DRC_DATA_SOURCE = "CCM Lab publications"

_clf = None
_clf_lock = threading.Lock()


def get_clf():
    global _clf
    if _clf is None:
        with _clf_lock:
            if _clf is None:
                print(
                    "[add_paper_entry] Loading BERT classifier – this may take several minutes on first run…",
                    file=sys.stderr,
                    flush=True,
                )
                _clf = pipeline(
                    "text-classification",
                    model=MODEL_ID,
                    top_k=TOP_K,
                    truncation=True,
                    max_length=512,
                )
                print("[add_paper_entry] BERT classifier ready.", file=sys.stderr, flush=True)
    return _clf


def format_input(title: str, abstract: str) -> str:
    t = (title or "").strip()
    a = (abstract or "").strip()
    if not t and not a:
        return " "
    if not a:
        return f" {t}"
    if not t:
        return f" NONE\n {a}"
    return f" {t}\n {a}"


def build_record(payload: dict[str, Any]) -> dict[str, Any]:
    title = str(payload.get("title", "")).strip()
    abstract = str(payload.get("abstract", "")).strip()
    if not title:
        raise ValueError("title is required")

    raw = get_clf()(format_input(title, abstract))
    topics = raw[0] if raw and isinstance(raw[0], list) else raw
    topics = topics or []

    keywords = " | ".join([strip_topic_id(t.get("label", "")) for t in topics[:5] if t.get("label")])
    bert_topics = "; ".join([f"{t.get('label', '')} ({float(t.get('score', 0)):.4f})" for t in topics[:TOP_K]])
    categories = classify_categories(topics, title, abstract)
    primary_category = primary_category_from_multi(categories)

    return {
        "title": title,
        "authors": str(payload.get("authors", "")).strip(),
        "year": str(payload.get("year", "")).strip(),
        "primary_category": primary_category,
        "categories": "|".join(categories),
        "keywords": keywords,
        "hf_dataset": DRC_HF_DATASET,
        "data_source": DRC_DATA_SOURCE,
        "bert_topics": bert_topics,
        "journal": str(payload.get("journal", "")).strip(),
        "citations": int(payload.get("citations", 0) or 0),
        "url": str(payload.get("url", "")).strip(),
        "citedby_url": "",
        "url_related_articles": "",
        "abstract": abstract,
        "bibtex": str(payload.get("bibtex", "")).strip(),
        "department": str(payload.get("department", "")).strip(),
    }


def append_record(record: dict[str, Any]) -> None:
    cols = [
        "title", "authors", "year", "primary_category", "categories", "keywords",
        "hf_dataset", "data_source", "bert_topics", "journal", "citations", "url",
        "citedby_url", "url_related_articles", "abstract", "bibtex", "department",
    ]
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    exists = CSV_PATH.exists() and CSV_PATH.stat().st_size > 0
    with CSV_PATH.open("a", newline="", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            writer = csv.DictWriter(f, fieldnames=cols)
            if not exists:
                writer.writeheader()
            writer.writerow({k: record.get(k, "") for k in cols})
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
