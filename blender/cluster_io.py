"""Shared loaders for the Blender Geometry-Nodes pipeline.

Three artefacts drive the scene:

    outputs/fragments_params/clusters.json   ← per-fragment 6-D parameters
    outputs/clusters/summary.json            ← Ward cluster sizes + linkage
    outputs/gh_meshes/*.obj                  ← geometry from Grasshopper
                                               (or grasshopper/standalone_runner.py)

This module is `import`-clean from inside Blender's bundled Python — no
project-wide config dependency, no third-party imports.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def project_root() -> Path:
    """Project root regardless of where Blender's CWD points."""
    return Path(__file__).resolve().parents[1]


def load_clusters(path: Path | None = None) -> dict[str, Any]:
    """Load the parametric-fragments JSON written by notebook 03."""
    path = path or (project_root() / "outputs" / "fragments_params" / "clusters.json")
    if not path.exists():
        sys.stderr.write(
            f"\n[blender] clusters.json not found at {path}.\n"
            f"          Run notebooks/03_clustering.ipynb first.\n\n"
        )
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def load_summary(path: Path | None = None) -> dict[str, Any]:
    """Load Ward cluster summary (cluster_sizes + linkage matrix)."""
    path = path or (project_root() / "outputs" / "clusters" / "summary.json")
    if not path.exists():
        return {"cluster_sizes": [], "linkage": []}
    return json.loads(path.read_text(encoding="utf-8"))


def gh_mesh_dir() -> Path:
    return project_root() / "outputs" / "gh_meshes"


def remap(value: float, lo: float, hi: float) -> float:
    """Linearly map a 0..1 value into [lo, hi]."""
    return lo + (hi - lo) * float(value)


def merge_order_from_linkage(linkage: list[list[float]], n_leaves: int) -> list[int]:
    """Return leaf indices in the order they get absorbed by Ward merges.

    The leaf ordering is what drives the "branch unfolding" reveal — leaves
    that join the tree late (large linkage distance) appear last in the
    animation timeline.

    Defensive: scipy linkage rows reference leaves [0..n_leaves-1] and
    internal nodes [n_leaves..2*n_leaves-2]. If the linkage was built on a
    different leaf count than ``n_leaves`` (e.g. doc-level dendrogram vs
    fragment count), the indices won't match — return a trivial order and
    let the caller fall back.
    """
    if not linkage:
        return list(range(n_leaves))

    max_idx = max(int(max(row[0], row[1])) for row in linkage)
    if max_idx >= 2 * n_leaves - 1:
        return list(range(n_leaves))

    children = [[i] for i in range(n_leaves)]
    out: list[int] = []
    for row in linkage:
        a, b = int(row[0]), int(row[1])
        merged: list[int] = []
        for x in (a, b):
            if x < n_leaves:
                merged.append(x)
            else:
                idx = x - n_leaves
                if idx >= len(children) - n_leaves:
                    return list(range(n_leaves))
                merged.extend(children[n_leaves + idx])
        children.append(merged)
        for leaf in merged:
            if leaf not in out:
                out.append(leaf)
                if len(out) >= n_leaves:
                    return out
    for i in range(n_leaves):
        if i not in out:
            out.append(i)
    return out


def fragment_reveal_order(payload: dict[str, Any]) -> list[int]:
    """Reveal order for the 20 fragments.

    Strategy: cluster-id ascending, then variant-id ascending — so the
    animation walks one archetype at a time, completes its four variants,
    then moves to the next archetype. Each cluster therefore unfolds as a
    little "branch" of the higher-level dendrogram.
    """
    fragments = payload.get("fragments", [])
    pairs = sorted(
        range(len(fragments)),
        key=lambda i: (int(fragments[i].get("cluster", 0)),
                       int(fragments[i].get("variant", 0))),
    )
    return pairs
