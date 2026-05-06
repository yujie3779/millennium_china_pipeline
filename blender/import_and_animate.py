"""Import 20 OBJ fragments (or build primitive fallbacks) + Geometry Nodes
+ a 64-second dendrogram-driven reveal animation, all inside Blender 4.x.

Run order in the Scripting workspace:
    1. geometry_nodes_setup.py  — creates the 5 GN trees.
    2. THIS file                 — builds geometry + animation.
    3. render_setup.py           — configures EEVEE Next + output.

The Ward-dendrogram leaf order drives a "branch unfolding" reveal: tight
sub-cluster siblings appear together, the latest inter-cluster bridge
merge waits longest. A 64-second helical orbit climbs while spiralling
around the layout centroid.

Look: studio black background. The ground plane is removed and replaced
by a pure-black world (set in render_setup.py). Each fragment receives a
shared porcelain-white Principled BSDF so the silhouettes read crisply
against the black canvas — museum-catalogue plate, not outdoor
architectural rendering.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import bpy
from mathutils import Euler, Vector


def _script_dir() -> Path:
    """Locate this file on disk (Blender's Run Script can hand a relative
    ``__file__``; the Scripting text-block always knows the absolute path)."""
    try:
        text = bpy.context.space_data.text
        if text and text.filepath:
            return Path(bpy.path.abspath(text.filepath)).resolve().parent
    except (AttributeError, RuntimeError, ReferenceError):
        pass
    p = Path(__file__).resolve()
    if p.exists():
        return p.parent
    raise RuntimeError("Run this script from Blender's Scripting workspace.")


_HERE = _script_dir()
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

# Blender keeps `sys.modules` populated across Run Script calls, so a sibling
# module edited on disk would not be picked up unless we evict it first.
for _mod in ("cluster_io", "geometry_nodes_setup"):
    sys.modules.pop(_mod, None)

from cluster_io import (  # noqa: E402
    fragment_reveal_order,
    gh_mesh_dir,
    load_clusters,
    load_summary,
)
from geometry_nodes_setup import (  # noqa: E402
    ARCHETYPE_NODE_TREE_NAMES,
    ensure_all_trees,
)


# --- Animation timing ----------------------------------------------------- #

FPS = 24
DURATION_SECONDS = 64           # safe margin over the 60-second minimum
TOTAL_FRAMES = FPS * DURATION_SECONDS  # 1536
COLLECTION_NAME = "China_Millennium_Fragments"

# Studio look: every fragment shares the same porcelain-white BSDF so the
# silhouette reads first; cluster identity is conveyed by the layout grid
# (cluster on X, variant on Y) rather than colour. RGB tuple kept for
# possible future per-cluster tints.
PORCELAIN_BASE_COLOR = (0.92, 0.92, 0.90, 1.0)
PORCELAIN_ROUGHNESS = 0.55
PORCELAIN_SPECULAR = 0.35


# ---------------------------------------------------------------------------
# Scene reset
# ---------------------------------------------------------------------------

def _reset_scene() -> None:
    """Wipe everything, drop a soft top-key + side-fill rig.

    No ground plane: the world is pure black (configured in
    render_setup.py), so the fragments float against the void and the
    eye reads each archetype as a museum-catalogue plate.
    """
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)

    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.lights,
                  bpy.data.cameras, bpy.data.images, bpy.data.objects):
        for item in list(block):
            try:
                block.remove(item)
            except Exception:  # noqa: BLE001
                pass

    # Top key: nearly-overhead sun, soft warm tint. Lower energy than the
    # outdoor variant because the black world contributes zero ambient.
    bpy.ops.object.light_add(type="SUN", location=(0, 0, 25))
    sun = bpy.context.active_object
    sun.name = "Key_Sun"
    sun.data.energy = 1.8
    sun.data.color = (1.0, 0.97, 0.92)
    sun.rotation_euler = Euler(
        (math.radians(15), math.radians(8), 0.0), "XYZ"
    )
    if hasattr(sun.data, "angle"):
        sun.data.angle = math.radians(20.0)  # softer shadow penumbra

    # Side fill from the camera-left side, cool tint, larger size for soft
    # rim. Pulls each fragment off the black background.
    bpy.ops.object.light_add(type="AREA", location=(-18, 14, 16))
    fill = bpy.context.active_object
    fill.name = "Fill_Area"
    fill.data.energy = 90.0
    fill.data.size = 12.0
    fill.data.color = (0.92, 0.95, 1.0)
    fill.rotation_euler = Euler(
        (math.radians(50), 0.0, math.radians(125)), "XYZ"
    )

    # Tiny camera-side rim from the opposite quadrant, prevents fragments
    # in the back row from going completely silhouette-black.
    bpy.ops.object.light_add(type="AREA", location=(20, -16, 10))
    rim = bpy.context.active_object
    rim.name = "Rim_Area"
    rim.data.energy = 45.0
    rim.data.size = 8.0
    rim.data.color = (1.0, 0.94, 0.88)
    rim.rotation_euler = Euler(
        (math.radians(70), 0.0, math.radians(-50)), "XYZ"
    )


# ---------------------------------------------------------------------------
# Shared porcelain-white material (one BSDF, applied to every fragment)
# ---------------------------------------------------------------------------

PORCELAIN_MAT_NAME = "Porcelain_Fragment_Mat"


def _ensure_porcelain_material() -> bpy.types.Material:
    """Build (or reuse) the single Principled BSDF used for every fragment.

    Single shared material keeps the studio look consistent: the cluster
    identity is conveyed by the 5×4 layout grid, not by colour.
    """
    mat = bpy.data.materials.get(PORCELAIN_MAT_NAME)
    if mat is not None:
        return mat
    mat = bpy.data.materials.new(PORCELAIN_MAT_NAME)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = PORCELAIN_BASE_COLOR
        bsdf.inputs["Roughness"].default_value = PORCELAIN_ROUGHNESS
        # Blender 4.x renamed "Specular" → "Specular IOR Level"; cope with both.
        for spec_key in ("Specular IOR Level", "Specular"):
            if spec_key in bsdf.inputs:
                bsdf.inputs[spec_key].default_value = PORCELAIN_SPECULAR
                break
    return mat


def _ensure_collection(name: str) -> bpy.types.Collection:
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    return coll


# ---------------------------------------------------------------------------
# Import + Geometry-Nodes attach
# ---------------------------------------------------------------------------

def _import_obj(obj_path: Path) -> bpy.types.Object | None:
    """Import a single OBJ; return the freshly-imported active object."""
    if not obj_path.exists():
        return None
    op = getattr(bpy.ops.wm, "obj_import", None) or getattr(bpy.ops.import_scene, "obj")
    op(filepath=str(obj_path))
    return bpy.context.selected_objects[0] if bpy.context.selected_objects else None


# Lightweight in-Blender fallback when Grasshopper hasn't produced OBJs.
# Maps each archetype to a built-in primitive whose extents respect the
# fragment's [0,1]-normalised parameters. Geometry Nodes do the heavy
# lifting afterwards, so the base mesh only needs to be plausible.
def _create_primitive(fragment: dict) -> bpy.types.Object:
    arche = fragment.get("archetype", "")
    p = fragment.get("params", {})
    h = 1.0 + 6.0 * float(p.get("height_norm", p.get("scale", 0.5)))
    w = 1.0 + 3.0 * float(p.get("footprint", p.get("scale", 0.5)))
    if arche == "pillow_membrane":
        bpy.ops.mesh.primitive_ico_sphere_add(radius=w, subdivisions=3)
    elif arche == "cantilever_canopy":
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        bpy.context.active_object.scale = (w * 2.0, w, h * 0.25)
    elif arche == "stepped_pavilion":
        bpy.ops.mesh.primitive_cylinder_add(radius=w, depth=h, vertices=24)
    elif arche == "twisting_tower":
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        bpy.context.active_object.scale = (w, w, h * 1.6)
    else:  # lattice_tower (and unknown)
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        bpy.context.active_object.scale = (w, w, h)
    obj = bpy.context.active_object
    cx = (int(fragment["cluster"]) - 2) * 9.0
    cy = (int(fragment["variant"]) - 1.5) * 7.0
    obj.location = (cx, cy, h * 0.5)
    return obj


def _attach_gn(obj: bpy.types.Object, archetype: str) -> None:
    name = ARCHETYPE_NODE_TREE_NAMES.get(archetype)
    if name is None:
        return
    tree = bpy.data.node_groups.get(name)
    if tree is None:
        return
    mod = obj.modifiers.new(name=f"GN_{archetype}", type="NODES")
    mod.node_group = tree


def _set_object_props(obj: bpy.types.Object, fragment: dict) -> None:
    obj["fragment_id"] = fragment["fragment_id"]
    obj["cluster"] = int(fragment["cluster"])
    obj["variant"] = int(fragment["variant"])
    obj["archetype"] = fragment["archetype"]
    for k, v in fragment["params"].items():
        obj[k] = float(v)


def import_all(payload: dict) -> list[bpy.types.Object]:
    """Import every OBJ that exists in ``outputs/gh_meshes/``."""
    coll = _ensure_collection(COLLECTION_NAME)
    mesh_dir = gh_mesh_dir()
    porcelain = _ensure_porcelain_material()

    out: list[bpy.types.Object] = []
    fallbacks = 0
    for f in payload["fragments"]:
        obj_path = mesh_dir / f"{f['fragment_id']}.obj"
        obj = _import_obj(obj_path)
        if obj is None:
            obj = _create_primitive(f)
            fallbacks += 1
        obj.name = f["fragment_id"]

        # Re-link object to our collection only.
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        coll.objects.link(obj)

        obj.data.materials.clear()
        obj.data.materials.append(porcelain)
        _set_object_props(obj, f)
        _attach_gn(obj, f["archetype"])
        out.append(obj)
    print(f"[import] {len(out)}/{len(payload['fragments'])} objects ready "
          f"(GH OBJs: {len(out) - fallbacks}, primitive fallbacks: {fallbacks})")
    return out


# ---------------------------------------------------------------------------
# Animation: dendrogram-driven branch reveal
# ---------------------------------------------------------------------------

def _animate_branch_reveal(payload: dict, summary: dict) -> None:
    """Each fragment fades+scales in at a frame chosen by Ward leaf order.

    The doc-level Ward dendrogram (in ``summary['linkage']``) operates on
    735 documents — at a different granularity than our 20 fragments. We
    therefore drive the reveal with the *fragment-level* order:
    cluster-id ascending, variant-id ascending. Each archetype unfolds as
    a self-contained branch before the next archetype begins.
    """
    fragments = payload["fragments"]
    n = len(fragments)
    leaf_order = fragment_reveal_order(payload)
    if not leaf_order or len(leaf_order) != n:
        leaf_order = list(range(n))

    reveal_window = int(TOTAL_FRAMES * 0.55)  # the reveal occupies 55% of the timeline
    per_step = max(1, reveal_window // n)
    coll = bpy.data.collections[COLLECTION_NAME]

    for rank, leaf_idx in enumerate(leaf_order):
        f = fragments[leaf_idx]
        obj = coll.objects.get(f["fragment_id"])
        if obj is None:
            continue
        appear_frame = 1 + rank * per_step
        settle_frame = appear_frame + int(per_step * 1.6)

        obj.scale = (0.001, 0.001, 0.001)
        obj.keyframe_insert(data_path="scale", frame=1)
        obj.keyframe_insert(data_path="scale", frame=appear_frame)

        obj.scale = (1.0, 1.0, 1.0)
        obj.keyframe_insert(data_path="scale", frame=settle_frame)


# ---------------------------------------------------------------------------
# Camera: helical orbit
# ---------------------------------------------------------------------------

def _build_camera_helix() -> bpy.types.Object:
    cam_data = bpy.data.cameras.new("Hero_Cam")
    cam_data.lens = 28.0
    cam = bpy.data.objects.new("Hero_Cam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam

    target = bpy.data.objects.new("Cam_Target", None)
    target.empty_display_type = "PLAIN_AXES"
    target.location = (0, 0, 5)
    bpy.context.scene.collection.objects.link(target)

    track = cam.constraints.new("TRACK_TO")
    track.target = target
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"

    n_keys = 13
    for i in range(n_keys):
        t = i / (n_keys - 1)
        frame = 1 + int(t * (TOTAL_FRAMES - 1))
        radius = 35.0 - 12.0 * t            # tighten as we ascend
        angle = t * 2.0 * math.pi * 1.3     # 1.3 turns over the whole take
        z = 4.0 + 18.0 * t
        cam.location = Vector((
            radius * math.cos(angle),
            radius * math.sin(angle),
            z,
        ))
        cam.keyframe_insert(data_path="location", frame=frame)

        target.location = Vector((
            -2.0 * math.cos(angle * 0.5),
             2.0 * math.sin(angle * 0.5),
            5.0 + 1.5 * t,
        ))
        target.keyframe_insert(data_path="location", frame=frame)

    return cam


# ---------------------------------------------------------------------------
# Scene timing
# ---------------------------------------------------------------------------

def _set_scene_timing() -> None:
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = TOTAL_FRAMES


def main() -> None:
    payload = load_clusters()
    summary = load_summary()
    print(f"[demo131] {len(payload['fragments'])} fragments, "
          f"{TOTAL_FRAMES} frames @ {FPS}fps = {DURATION_SECONDS}s")

    _reset_scene()
    ensure_all_trees()
    import_all(payload)
    _set_scene_timing()
    _animate_branch_reveal(payload, summary)
    _build_camera_helix()
    print("[demo131] scene + animation ready")


if __name__ == "__main__":
    main()
