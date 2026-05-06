Millennium-China Architecture Reimagined — Final Submission
==============================================================
Author: Yujie
Course: Digital Skills Report 25/26
Theme : 中国千禧年代建筑 (China's millennial-decade landmarks, 2000–2010)

Folder structure
----------------
datasets/
  wikidata/    - Wikidata SPARQL + zh.wiki extracts (.jsonl) — 250+ entries
  pixabay/     - Pixabay metadata (.jsonl, photo URLs only) — 250+ entries
  bilibili/    - Bilibili video metadata + danmaku (.jsonl) — 250+ entries
  openai/      - 50 synthetic Chinese architecture reviews (gpt-4o-mini)

design_tool_files/
  millennium_china.gh        - Rhino / Grasshopper canvas. Save it from
                               Grasshopper after running
                               grasshopper/all_in_one_component.py
                               (see grasshopper/HOW_TO_RUN.md, ~10 min).
  millennium_china.blend     - Blender 4.x project (Geometry Nodes modifier
                               per cluster, dendrogram-driven reveal,
                               helical camera path).

animation/
  millennium_china.mp4       - Blender EEVEE Next render, ≥ 60 s @ 24 fps,
                               1080p, H.264

report.pdf
  TODO: drop your final PDF report next to this README before zipping.

GitHub repository
-----------------
All source code, notebooks, and Python scripts that produced this output:
https://github.com/<your-username>/<repo-name>


Pipeline summary (also in the PDF report)
-----------------------------------------
1. Web scraping — three completely different domains:
   * Wikidata SPARQL — semantic structured query, then enriched with
     zh.wiki REST summaries (with a zh.wiki full-text-search fallback
     for buildings whose Wikidata page lacks an inception date).
   * Pixabay REST  — keyword-driven CC0 photo bank, metadata only.
   * Bilibili      — Chinese video search + XML danmaku stream, a
     distinctive Chinese-social-media surface form.

2. Vectorization — two text methods at opposite ends of the spectrum
   (Doc2Vec PV-DM trained on this corpus vs frozen multilingual
   Sentence-BERT). Empirical comparison written to
   outputs/clusters/comparison.json.

3. Generative API — OpenAI gpt-4o-mini in *Chinese* with a structured-JSON
   response_format, augmenting the corpus with 50 fictional millennium
   building reviews.

4. Machine learning — Ward agglomerative clustering produces a full
   dendrogram (cut at k=5); t-SNE provides 2-D plots. The dendrogram
   itself drives Blender's branch-unfold reveal animation.

5. Visualisation — Matplotlib + Seaborn, six figures, all inline in the
   four numbered Jupyter notebooks.

6. Design tools — Grasshopper (Rhino) generates the geometry, Blender
   then applies a per-cluster Geometry-Nodes modifier and renders a
   helical 64-second camera flight. The same outputs/fragments_params/
   clusters.json drives both environments — that's the cross-platform
   continuity Part 2 asks for.

Notes
-----
- The Grasshopper canvas is produced by you in Rhino: install Rhino 7
  (90-day evaluation) and follow grasshopper/HOW_TO_RUN.md — drop one
  GHPython component, paste grasshopper/all_in_one_component.py, save the
  canvas as grasshopper/millennium_china.gh. The component itself imports
  clusters.json, builds 20 meshes, and exports them as .obj into
  outputs/gh_meshes/ on every recompute, no manual bake/export needed.
- If you skip Rhino, blender/import_and_animate.py auto-falls back to
  primitive geometry (cube/cylinder/ico-sphere per archetype, scaled by
  the same clusters.json), so the .mp4 animation still reproduces — but
  in that case only Blender is exercised, which is below the assignment's
  "≥ 2 design-tool environments" threshold.
- The OpenAI synthetic dataset was generated via an OpenAI-compatible
  proxy (api2d.net); the project root holds .openai_key + .openai_base_url
  (gitignored).
