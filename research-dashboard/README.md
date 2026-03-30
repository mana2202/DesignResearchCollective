# CCM Research Publications Dashboard

An automated pipeline that fetches papers from two Hugging Face datasets, classifies them with an **OpenAlex BERT** topic model (running locally via [Transformers](https://huggingface.co/docs/transformers)), and writes a CSV for the interactive dashboard.

## Repo structure

```
research-dashboard/
├── scripts/
│   ├── 1_fetch_and_classify.py   # Load HF datasets + BERT classification → CSV
│   └── 2_run_pipeline.sh         # One-command runner (installs deps + runs script)
├── data/
│   └── papers.csv                # Generated: enriched & classified papers
├── dashboard/
│   └── index.html                # Self-contained static dashboard
└── requirements.txt
```

## Setup

### 1. Install dependencies

```bash
cd research-dashboard
pip install -r requirements.txt
```

Requires **PyTorch** and **Transformers**; the first run downloads the model weights for:

`OpenAlex/bert-base-multilingual-cased-finetuned-openalex-topic-classification-title-abstract`

### 2. Run the pipeline (build `papers.csv`)

```bash
bash scripts/2_run_pipeline.sh
```

Or directly:

```bash
python scripts/1_fetch_and_classify.py
```

**Runtime:** Classifying the full merged set (tens of thousands of papers) can take **roughly 15–45+ minutes** depending on CPU/GPU (Apple Silicon MPS is used automatically when available). For a quick test, limit how many rows get BERT inference:

```bash
MAX_PAPERS=500 python scripts/1_fetch_and_classify.py
```

(Omit `MAX_PAPERS` for the full export.)

This will:

- Load all rows from both datasets (`ccm/publications`, `ccm/cmu-engineering-publications`)
- Run **BERT** on title + abstract (OpenAlex topic labels as “keywords,” mapped to four design categories)
- Write **`data/papers.csv`** with columns (in order):  
  `title`, `authors`, `year`, `categories`, `keywords`, `hf_dataset`, `data_source`, `bert_topics`, `journal`, `citations`, `url`, `citedby_url`, `url_related_articles`, `abstract`, `bibtex`, `department`  
  For CCM Lab rows, `bibtex`, `citedby_url`, and `url_related_articles` are populated when present in the Hugging Face dataset (see table below).

No API keys are required for classification.

### 3. Open the dashboard

Open `dashboard/index.html` in a browser (double-click or “Open with Live Server”). The page loads `../data/papers.csv` via `fetch`, so some browsers require opening from a local server or adjusting file access; serving the folder with any static server works.

For **GitHub Pages**, point the site at the folder that contains `dashboard/` and `data/` (or adjust `csvPath` in `index.html` to match your published layout).

---

## Dashboard features

- **Overview** — totals, year chart, category bars, keywords, source split
- **Browse** — search and filters (year, category, source)
- **Cluster view** — 2D layout by keyword similarity

## Dataset sources

| Hugging Face dataset | `data_source` column |
|----------------------|----------------------|
| [`ccm/publications`](https://huggingface.co/datasets/ccm/publications) | CCM Lab publications |
| [`ccm/cmu-engineering-publications`](https://huggingface.co/datasets/ccm/cmu-engineering-publications) | CMU Engineering publications |

### What each dataset contains

**[`ccm/publications`](https://huggingface.co/datasets/ccm/publications)** (239 rows) includes full **`bibtex`** strings, structured **`bib_dict`**, **`pub_url`**, **`citedby_url`**, **`url_related_articles`**, embeddings, etc. The pipeline writes **`bibtex`**, normalizes relative Google Scholar paths on **`citedby_url`** / **`url_related_articles`**, and sets **`url`** from **`pub_url`**, or from a `url = {…}` field inside **`bibtex`** if **`pub_url`** is missing.

**[`ccm/cmu-engineering-publications`](https://huggingface.co/datasets/ccm/cmu-engineering-publications)** (~42k rows) only exposes **`title`**, **`pub_year`**, **`citation`**, **`num_citations`**, **`author_pub_id`**, **`faculty`**, **`department`**, and **`embedding`**. There is **no** `bibtex`, `abstract`, or publisher URL in that dataset, so those CSV columns are empty for CMU rows—URLs cannot be recovered from BibTeX unless you merge another source.

## Categories

Each paper gets **exactly one** label (spelling fixed for this project):

- `ideation` — generating ideas, concepts, frameworks, exploratory approaches
- `optimmization` — improving performance, efficiency, cost, or seeking a best solution *(spelled with double **m** to match the label set)*
- `grammar` — formal rules, grammars, parametric logic, structured generative systems
- `decision_making` — supporting or automating choices, tradeoffs, evaluation, recommendations

Classification uses OpenAlex BERT topic labels plus title/abstract text with **heuristic** scoring and tie-breaking—it approximates the rules above but is not an LLM judge.
