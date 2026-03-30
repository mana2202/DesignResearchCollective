# CCM Research Publications Dashboard

An automated pipeline that fetches, classifies, and visualizes research publications from two Hugging Face datasets into an interactive dashboard.

## 🗂️ Repo Structure

```
research-dashboard/
├── scripts/
│   ├── 1_fetch_and_classify.py   # Fetches HuggingFace data + classifies via Claude API
│   └── 2_run_pipeline.sh         # One-command runner
├── data/
│   └── papers.csv                # Output: enriched & classified papers
├── dashboard/
│   └── index.html                # Self-contained interactive dashboard
└── requirements.txt
```

## 🚀 Setup & Usage

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your Anthropic API key

```bash
export ANTHROPIC_API_KEY=your_key_here
```

### 3. Run the pipeline

```bash
bash scripts/2_run_pipeline.sh
```

This will:
- Fetch all papers from both HuggingFace datasets
- Use Claude to extract keywords and classify each paper into categories
- Output `data/papers.csv`

### 4. Open the dashboard

Open `dashboard/index.html` in your browser — **no server needed**.

Or deploy to **GitHub Pages** for public access:
1. Push this repo to GitHub
2. Go to Settings → Pages → Source: `main` branch, `/ (root)` folder
3. Your dashboard will be live at `https://yourusername.github.io/research-dashboard/dashboard/`

---

## 📊 Dashboard Features

- **Overview tab** — publication stats, year trends, category breakdown
- **Browse tab** — filterable paper cards with search, year, category, and source filters
- **Cluster View tab** — 2D scatter plot of papers clustered by keyword similarity to find research whitespaces

## 📁 Dataset Sources

- [`ccm/publications`](https://huggingface.co/datasets/ccm/publications) — CCM Lab publications
- [`ccm/cmu-engineering-publications`](https://huggingface.co/datasets/ccm/cmu-engineering-publications) — CMU Engineering publications

## 🏷️ Categories

Papers are classified (can belong to multiple) into:
- **Ideation** — concept generation, brainstorming, creative design
- **Optimization** — design optimization, performance, computational methods
- **Grammar** — design grammars, rule-based systems, structured representations
- **Decision Making** — decision support, agent-based, strategy, human factors
