# Digital Skills Final Report 25/26 — Millennium-China Architecture Reimagined

> **主题 / Theme**: 中国千禧年代地标建筑 (mainland China's 2000–2010 landmark buildings).
> Data-driven exploration of Chinese millennium architecture, transforming web-scraped Chinese text + photo metadata + video-platform comments into 20 procedurally-generated 3D architectural fragments and a 1-minute animation.

A coherent end-to-end pipeline that ties together:

1. **Web scraping** from three different domains — **Wikidata SPARQL + zh.wiki** (semantic structured query), **Pixabay** (keyword-driven photo API, metadata only), **Bilibili** (Chinese video search + XML danmaku stream).
2. **Two text-vectorization techniques** with completely different training regimes: **Doc2Vec (PV-DM, gensim)** trained from scratch on this corpus vs **Sentence-BERT (paraphrase-multilingual-MiniLM-L12-v2)** zero-shot pretrained.
3. **OpenAI API augmentation** — Chinese system prompt + JSON `response_format` → 50 fictional millennium-architecture reviews.
4. **Ward hierarchical clustering** + **t-SNE** 2-D projection.
5. **Matplotlib + Seaborn** for six analytic plots (incl. dendrogram and the fragment-parameter heatmap).
6. **Grasshopper / Rhino** — five GHPython components, one per archetype, sharing the same `clusters.json`.
7. **Blender 4.x Geometry Nodes** — declarative node-based modifier per archetype, a dendrogram-driven branch-unfold reveal, and a 64-second helical camera flight rendered in EEVEE Next (Blender 4.2+ real-time engine, 64 TAA samples, Filmic Medium Contrast). Studio black-background look (pure-black world, no ground plane, top-key + side-fill + rim three-point rig, single porcelain-white BSDF on every fragment) so each archetype reads as a museum-catalogue plate. Includes a **primitive-geometry fallback** so the animation pipeline runs end-to-end even without Rhino installed.

## Methodological highlights

Each layer of the pipeline is paired with a deliberate technical choice; the table below is a quick map of the design space we traversed:

| Layer | Choice | Why |
|---|---|---|
| Theme | China 2000–2010 landmarks | A coherent decade with five recognisable archetypes (lattice / pillow / cantilever / twist / stepped) |
| Scraper 1 | Wikidata SPARQL + zh.wiki REST/search | Semantic structured query, fully Chinese-language enrichment |
| Scraper 2 | Pixabay REST (metadata only) | Keyword-first retrieval; no pixel data needed (text-only pipeline) |
| Scraper 3 | Bilibili search + XML danmaku | Distinctive Chinese-social-media surface form |
| Text NLP | jieba 中文 + bilingual stop-list | 中文不靠空格切词，需要专用切分器 |
| Vectorizer A | Doc2Vec PV-DM (200-D, trained) | Captures word-order context on this exact corpus |
| Vectorizer B | Sentence-BERT multilingual MiniLM | Frozen pretrained Transformer baseline, zero-shot |
| Augmentation | OpenAI gpt-4o-mini · Chinese review register · structured JSON | Synthetic 50 entries diversify the corpus before clustering |
| Clustering | Ward hierarchical clustering, k=5 | Full dendrogram drives the Blender branch-unfold reveal animation |
| Manifold | t-SNE | Local-neighbourhood preservation for the cluster scatter plot |
| 3D tool 1 | Rhino Grasshopper (node-based) | De-facto parametric-architecture canvas; CCTV / Bird's Nest lineage |
| 3D tool 2 | Blender Geometry Nodes (declarative) | Lazy-evaluated node-graph modifier per archetype |
| Reveal animation | Branch unfolding from Ward dendrogram | Animation timing literally derived from the ML output |
| Camera | 64-second helical orbit | Continuous fly-through emphasising spatial relationships |

## Project structure

```
demo131/
├── data/
│   ├── raw/{wikidata,pixabay,bilibili}/   ← scraped jsonl
│   ├── processed/                         ← unified parquet
│   └── vectors/                           ← serialized embeddings
├── notebooks/                             ← 4 sequential notebooks (the narrative)
├── src/                                   ← reusable Python modules
│   ├── scraping/                          ← 3 scrapers + shared HTTP helper
│   ├── vectorize/                         ← Doc2Vec + SBERT + comparator
│   ├── ml/                                ← Ward + t-SNE + bridge JSON
│   ├── viz/                               ← 6 plots
│   ├── api/                               ← OpenAI Chinese augment
│   └── preprocess.py                      ← jieba + corpus build
├── grasshopper/
│   ├── README_GH.md                       ← background + 7-component canvas spec
│   ├── HOW_TO_RUN.md                      ← step-by-step Rhino-install + run guide
│   ├── all_in_one_component.py            ← single-component shortcut (recommended)
│   ├── ghpython_components.py             ← five GHPython component bodies
│   └── millennium_china.gh                ← created by you in Grasshopper (step 6)
├── blender/
│   ├── cluster_io.py
│   ├── geometry_nodes_setup.py            ← five GN node-trees
│   ├── import_and_animate.py              ← imports OBJs OR builds primitive fallback
│   └── render_setup.py                    ← EEVEE Next, 1080p/24
├── outputs/                               ← plots, clusters, gh_meshes, renders (auto-generated)
├── submission_yujie/                      ← OneDrive submission staging
└── requirements.txt
```

## How the workflow connects

```
[Wikidata SPARQL]   ─┐
[zh.wiki summary]   ─┤
[Pixabay tags]      ─┼──► clean (jieba) ──► Doc2Vec  ─┐
[Bilibili danmaku]  ─┤                                ├──► compare → pick SBERT
[OpenAI synthetic]  ─┘                  ──► SBERT  ───┘             │
                                                                    ▼
                                                        Ward + t-SNE
                                                                    │
                                                                    ▼
                                          outputs/fragments_params/clusters.json
                                                                    │
                              ┌─────────────────────────────────────┴───────────────────────┐
                              ▼                                                             ▼
                    Grasshopper / Rhino                                        Blender (Geometry Nodes)
                    5 GHPython components                                      5 GN trees, branch-unfold reveal
                    → outputs/gh_meshes/*.obj  ─────────────────►  primitive fallback if missing
                                                                              │
                                                              ▼
                                          outputs/renders/millennium_china.mp4
```

The same `clusters.json` drives both 3D environments — that's the "continuity across platforms" the brief asks for.

## Quick start

### 1. Setup (one-time)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

You will also need two keys (each gitignored):

* `.openai_key`     — OpenAI (or compatible proxy) chat key
* `.openai_base_url` — optional; for OpenAI-compatible proxies (api2d / openrouter)
* `.pixabay_key`    — optional; free key from https://pixabay.com/api/docs/ (Pixabay step is skipped if absent)

### 2. Run the pipeline

Open the notebooks in order:

1. `notebooks/01_scraping.ipynb` — collect ≥250 items per dataset
2. `notebooks/02_vectorization.ipynb` — Doc2Vec vs Sentence-BERT
3. `notebooks/03_clustering.ipynb` — Ward + t-SNE → `clusters.json`
4. `notebooks/04_visualization.ipynb` — six plots + final fragment heatmap

### 3. 3D production

* **Path A — with Rhino (REQUIRED to satisfy "≥ 2 design-tool environments")**: install Rhino 7 (90-day eval) and follow [`grasshopper/HOW_TO_RUN.md`](grasshopper/HOW_TO_RUN.md) — drop a single GHPython component, paste `all_in_one_component.py`, save the canvas as `millennium_china.gh`, and the OBJs in `outputs/gh_meshes/` get overwritten with real Grasshopper-baked geometry.
* **Path B — without Rhino**: Blender's `import_and_animate.py` builds primitive fallbacks (cube/cylinder/ico-sphere) per archetype, scaled by `clusters.json` parameters. The animation deliverable still works end-to-end, **but only one design-tool environment (Blender) is exercised**, which is below the assignment's "≥ 2" threshold.

Then in Blender 4.x's Scripting workspace:
1. Run `blender/geometry_nodes_setup.py` (creates five GN node-trees).
2. Run `blender/import_and_animate.py` (imports OBJs *or* builds primitive fallbacks, attaches GN modifier, builds animation).
3. Run `blender/render_setup.py` (configures EEVEE Next + 1080p/24/MP4 output).
4. `Render → Render Animation` → `outputs/renders/millennium_china.mp4`.

## Data sources & attributions

| Dataset | Source | License | Items |
|---|---|---|---|
| Wikidata + zh.wiki | https://query.wikidata.org / zh.wikipedia.org | CC BY-SA 3.0 | ~250 |
| Pixabay metadata | https://pixabay.com (REST API) | Pixabay License (CC0-equivalent) | ~250 |
| Bilibili videos + danmaku | https://api.bilibili.com | Bilibili ToS — research-only | ~250 |
| OpenAI synthetic | gpt-4o-mini (via api2d proxy) | Synthetic, this report | 50 |

## Third-party / pretrained model credits

- **Doc2Vec** — Le & Mikolov, 2014. via `gensim`.
- **Sentence-BERT (paraphrase-multilingual-MiniLM-L12-v2)** — Reimers & Gurevych, 2019; multilingual fine-tune by HuggingFace.
- **t-SNE** — van der Maaten & Hinton, 2008. via `scikit-learn`.
- **OpenAI gpt-4o-mini** — used for synthetic Chinese text augmentation only. All outputs reviewed before inclusion.
- **jieba** — sun, 2012-. Apache-2.0.
- **Rhino / Grasshopper** — Robert McNeel & Associates.
- **Blender 4.x Python API** — Blender Foundation.

## Reproducibility

All random seeds are fixed in `src/config.py` (`RANDOM_STATE = 42`). The `data/` and `outputs/` folders are excluded from Git but can be regenerated from `notebooks/01_scraping.ipynb` end-to-end (≈ 15 min on broadband; no GPU required).

## License

This project is released under the MIT License. Scraped data retains its original license (see Attributions table above).
