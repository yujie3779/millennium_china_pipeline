# Grasshopper / Rhino — node-based fragment generation

This is the **first** of the two design-tool environments (the second is Blender Geometry Nodes — see `../blender/`). Both consume the same `outputs/fragments_params/clusters.json` produced by `notebooks/03_clustering.ipynb`, so the data-driven typology drives both.

## Why Grasshopper for fragment generation?

* **Visual node-based dataflow** — Grasshopper's canvas is a directed graph of operators (`Curve`, `Surface`, `Brep`, …) with explicit data-tree semantics. Authoring a `Pipe` from a `Voronoi` of a `Sphere` is a node-wiring task rather than an imperative vertex-walking script, which makes the parametric intent legible at a glance.
* **Architectural lineage** — Grasshopper is the de-facto parametric-architecture tool used to design buildings like the CCTV Headquarters. Using it to generate millennium-China fragments is thematically consistent with the dataset itself.
* **GHPython glue** — five Python script components (one per archetype) embed reproducible logic into the otherwise-graphical canvas. The bodies of those components live in [`ghpython_components.py`](./ghpython_components.py) so they can be code-reviewed without opening Rhino.

## Repo layout

```
grasshopper/
├── README_GH.md                ← this file (background + 7-component canvas spec)
├── HOW_TO_RUN.md               ← step-by-step Rhino-install + run guide (≈10 min)
├── all_in_one_component.py     ← single-component path (recommended for graders)
├── ghpython_components.py      ← the 5 GHPython component bodies (paste-able)
└── millennium_china.gh         ← saved by you in step 6 of HOW_TO_RUN.md
```

## 1. Setup (in Rhino 7 / 8)

> **The fastest path is documented in [`HOW_TO_RUN.md`](./HOW_TO_RUN.md)** —
> ~25 min to install Rhino 7 evaluation + ~10 min to drop one GHPython
> component, paste `all_in_one_component.py`, save as `millennium_china.gh`,
> and overwrite `outputs/gh_meshes/` with real Grasshopper geometry.

1. Install **Rhino 7** (or later — 90-day eval works) and confirm Grasshopper opens (`grasshopper` command at the Rhino prompt).
2. Open `grasshopper/millennium_china.gh` (created in step 6 of `HOW_TO_RUN.md`).
3. The canvas expects `outputs/fragments_params/clusters.json` to exist on disk (run notebooks 01–03 first).

## 2. Node-graph at a glance

```
[File Path: ../outputs/fragments_params/clusters.json]
       │
       ▼
[GHPython · ParseClustersJson]   ─► (params, archetypes, ids)  data-tree
       │
       ├──► [GHPython · BirdsNestSteelLattice]     (cluster 0)  ─┐
       ├──► [GHPython · ETFEPillowFacade]          (cluster 1)  ─┤
       ├──► [GHPython · DoubleZCantilever]         (cluster 2)  ─┤
       ├──► [GHPython · TwistingTowerLoft]         (cluster 3)  ─┤
       └──► [GHPython · SteppedPavilionStack]      (cluster 4)  ─┘
                                                                │
                                          [Move / Grid Layout]  ◄
                                                                │
                                              [Mesh Join + Bake]
                                                                │
                                              [Export ▸ .obj per fragment]
                                                                ▼
                                              ../outputs/gh_meshes/
```

Each archetype component reads the normalised parameters (`lattice`, `pillow`, `cantilever`, `twist`, `stack`, `porosity`) and returns a `Mesh` plus a transform. The grid layout component places them in a 5×4 array.

## 3. The .gh file

`millennium_china.gh` is **produced by you** in step 6 of `HOW_TO_RUN.md` — Grasshopper's `.gh` is a binary canvas snapshot that has to be saved from inside Grasshopper (it can't be generated headlessly). Once saved, it lives in this folder and is what the submission's `design_tool_files/` will contain.

The GHPython component code in `ghpython_components.py` (multi-component reference) and `all_in_one_component.py` (single-component shortcut) is plain Python with `Rhino.Geometry` calls — every line is annotated, so it can be code-reviewed without Rhino.

**Don't want to install Rhino at all?** `blender/import_and_animate.py` includes a primitive-geometry **fallback**: when `outputs/gh_meshes/` is empty, it generates basic meshes (cube/cylinder/ico-sphere) per archetype directly inside Blender, scales them by the cluster parameters, and lays them out in the same 5×4 grid. The animation deliverable is then reproducible with **only Blender** installed — but in that case the "≥ 2 design-tool environments" requirement of the assignment is *not* satisfied; you must install Rhino + run the canvas to claim it.

## 4. Reproducible export from inside Rhino

`all_in_one_component.py` writes the OBJs **directly** as a side-effect of the GH recompute — no manual `Bake → Export` needed. The output folder is whatever you wired into the component's `y` input (recommended: `outputs/gh_meshes/`). Each `.obj` is named `frag-c{cluster:02d}-v{variant:02d}.obj` and the file header is `# demo131 millennium-China fragment` (vs. `# trimesh` for the placeholder fallbacks).

## 5. Continuity with Blender (Geometry Nodes)

Blender's `import_and_animate.py` reads every `.obj` from `outputs/gh_meshes/` (or builds primitive fallbacks if absent), applies a Geometry-Nodes modifier per cluster (one shared modifier per archetype), and animates a 64-second camera flight. The same `clusters.json` then drives the Geometry-Nodes input attributes — so the visual output of Blender is a *post-process* of the Grasshopper geometry, not an independent re-implementation.
