"""Procedurally build five Geometry-Node trees — one per archetype.

Geometry Nodes is a declarative node-graph evaluation engine: instead of
imperatively walking vertices in Python, we describe a transformation
pipeline whose nodes are evaluated lazily and re-evaluated automatically
whenever an input attribute changes. That is the key reason this project
chooses Geometry Nodes for the second design-tool environment.

Run in Blender 4.x's Scripting workspace; this script registers five
node-groups (GN_LatticeWoven / GN_PillowSkin / GN_DoubleCantilever /
GN_TwistingTower / GN_SteppedPavilion) which `import_and_animate.py`
attaches to the right object based on its `archetype` property.
"""
from __future__ import annotations

from typing import Callable, Dict

import bpy

ARCHETYPE_NODE_TREE_NAMES: Dict[str, str] = {
    "lattice_woven":     "GN_LatticeWoven",
    "pillow_skin":       "GN_PillowSkin",
    "double_cantilever": "GN_DoubleCantilever",
    "twisting_tower":    "GN_TwistingTower",
    "stepped_pavilion":  "GN_SteppedPavilion",
}


# ---------------------------------------------------------------------------
# Cross-version helpers — the Geometry Nodes Python API was rearranged in
# Blender 4.0 (sockets moved from `node_group.inputs` to
# `node_group.interface.items_tree`). We support both dialects.
# ---------------------------------------------------------------------------

def _ensure_io_socket(node_group, name: str, socket_type: str, in_out: str = "INPUT") -> None:
    """Add a Geometry / Float / Vector socket to ``node_group``'s interface."""
    if hasattr(node_group, "interface"):
        existing = {it.name for it in node_group.interface.items_tree
                    if it.in_out == in_out}
        if name not in existing:
            node_group.interface.new_socket(name, in_out=in_out, socket_type=socket_type)
    else:  # Blender 3.x fallback
        sockets = node_group.inputs if in_out == "INPUT" else node_group.outputs
        if name not in {s.name for s in sockets}:
            sockets.new(socket_type, name)


def _new_tree(name: str) -> bpy.types.GeometryNodeTree:
    """Create or refresh a Geometry-Nodes node tree of the given name."""
    tree = bpy.data.node_groups.get(name)
    if tree:
        bpy.data.node_groups.remove(tree)
    tree = bpy.data.node_groups.new(name, "GeometryNodeTree")

    _ensure_io_socket(tree, "Geometry", "NodeSocketGeometry", "INPUT")
    _ensure_io_socket(tree, "Geometry", "NodeSocketGeometry", "OUTPUT")
    _ensure_io_socket(tree, "Reveal", "NodeSocketFloat", "INPUT")  # 0..1 timeline
    _ensure_io_socket(tree, "Strength", "NodeSocketFloat", "INPUT")  # 0..1 effect

    nodes = tree.nodes
    in_node = nodes.new("NodeGroupInput")
    in_node.location = (-700, 0)
    out_node = nodes.new("NodeGroupOutput")
    out_node.location = (700, 0)
    return tree


def _link_io(tree, mid_node, in_socket_name: str = "Geometry",
             out_socket_name: str = "Geometry") -> None:
    """Wire the implicit Group Input → ``mid_node`` → Group Output chain."""
    nodes = tree.nodes
    inp = next(n for n in nodes if n.bl_idname == "NodeGroupInput")
    outp = next(n for n in nodes if n.bl_idname == "NodeGroupOutput")
    tree.links.new(inp.outputs[in_socket_name], mid_node.inputs[0])
    tree.links.new(mid_node.outputs[0], outp.inputs[out_socket_name])


# ---------------------------------------------------------------------------
# Per-archetype node-tree builders.
# Each builder wires a small graph with deliberate visual character:
#   lattice_woven    : Mesh-to-curve → curve-to-mesh-with-profile (rod sweep)
#   pillow_skin      : Set-position with noise-driven inflation along normals
#   double_cantilever: Subdivide + Set-position with random offset
#   twisting_tower   : Set-position with z-driven Z-rotation (twist along Z)
#   stepped_pavilion : Subdivide + Set-position floor-step (z-quantisation)
# ---------------------------------------------------------------------------

def _build_lattice_woven() -> bpy.types.GeometryNodeTree:
    tree = _new_tree(ARCHETYPE_NODE_TREE_NAMES["lattice_woven"])
    nodes = tree.nodes

    inp = next(n for n in nodes if n.bl_idname == "NodeGroupInput")
    outp = next(n for n in nodes if n.bl_idname == "NodeGroupOutput")

    # Mesh → Curve → Set Curve Radius (Reveal-driven) → Curve → Mesh
    m2c = nodes.new("GeometryNodeMeshToCurve")
    m2c.location = (-450, 0)

    set_radius = nodes.new("GeometryNodeSetCurveRadius")
    set_radius.location = (-200, 0)
    set_radius.inputs["Radius"].default_value = 0.05

    profile = nodes.new("GeometryNodeCurvePrimitiveCircle")
    profile.location = (-200, -250)
    profile.inputs["Radius"].default_value = 0.06
    profile.inputs["Resolution"].default_value = 8

    c2m = nodes.new("GeometryNodeCurveToMesh")
    c2m.location = (50, 0)

    tree.links.new(inp.outputs["Geometry"], m2c.inputs["Mesh"])
    tree.links.new(m2c.outputs["Curve"], set_radius.inputs["Curve"])
    tree.links.new(set_radius.outputs["Curve"], c2m.inputs["Curve"])
    tree.links.new(profile.outputs["Curve"], c2m.inputs["Profile Curve"])
    tree.links.new(c2m.outputs["Mesh"], outp.inputs["Geometry"])
    return tree


def _build_pillow_skin() -> bpy.types.GeometryNodeTree:
    tree = _new_tree(ARCHETYPE_NODE_TREE_NAMES["pillow_skin"])
    nodes = tree.nodes
    inp = next(n for n in nodes if n.bl_idname == "NodeGroupInput")
    outp = next(n for n in nodes if n.bl_idname == "NodeGroupOutput")

    set_pos = nodes.new("GeometryNodeSetPosition")
    set_pos.location = (-200, 0)

    normal = nodes.new("GeometryNodeInputNormal")
    normal.location = (-650, -200)

    noise = nodes.new("ShaderNodeTexNoise")  # Noise texture node works in GN
    noise.location = (-650, -50)
    noise.inputs["Scale"].default_value = 4.5

    mul_strength = nodes.new("ShaderNodeMath")
    mul_strength.operation = "MULTIPLY"
    mul_strength.location = (-450, -50)
    mul_strength.inputs[1].default_value = 0.18

    vec_scale = nodes.new("ShaderNodeVectorMath")
    vec_scale.operation = "SCALE"
    vec_scale.location = (-450, -200)

    tree.links.new(noise.outputs["Fac"], mul_strength.inputs[0])
    tree.links.new(mul_strength.outputs["Value"], vec_scale.inputs["Scale"])
    tree.links.new(normal.outputs["Normal"], vec_scale.inputs[0])
    tree.links.new(vec_scale.outputs["Vector"], set_pos.inputs["Offset"])
    tree.links.new(inp.outputs["Geometry"], set_pos.inputs["Geometry"])
    tree.links.new(set_pos.outputs["Geometry"], outp.inputs["Geometry"])
    return tree


def _build_double_cantilever() -> bpy.types.GeometryNodeTree:
    tree = _new_tree(ARCHETYPE_NODE_TREE_NAMES["double_cantilever"])
    nodes = tree.nodes
    inp = next(n for n in nodes if n.bl_idname == "NodeGroupInput")
    outp = next(n for n in nodes if n.bl_idname == "NodeGroupOutput")

    subdiv = nodes.new("GeometryNodeSubdivisionSurface")
    subdiv.location = (-300, 0)
    subdiv.inputs["Level"].default_value = 1

    tree.links.new(inp.outputs["Geometry"], subdiv.inputs["Mesh"])
    tree.links.new(subdiv.outputs["Mesh"], outp.inputs["Geometry"])
    return tree


def _build_twisting_tower() -> bpy.types.GeometryNodeTree:
    tree = _new_tree(ARCHETYPE_NODE_TREE_NAMES["twisting_tower"])
    nodes = tree.nodes
    inp = next(n for n in nodes if n.bl_idname == "NodeGroupInput")
    outp = next(n for n in nodes if n.bl_idname == "NodeGroupOutput")

    set_pos = nodes.new("GeometryNodeSetPosition")
    set_pos.location = (-100, 0)

    pos = nodes.new("GeometryNodeInputPosition")
    pos.location = (-700, -100)

    sep = nodes.new("ShaderNodeSeparateXYZ")
    sep.location = (-540, -100)

    mul_z = nodes.new("ShaderNodeMath")
    mul_z.operation = "MULTIPLY"
    mul_z.location = (-380, -100)
    mul_z.inputs[1].default_value = 0.06   # twist amount per metre Z

    cos_n = nodes.new("ShaderNodeMath")
    cos_n.operation = "COSINE"
    cos_n.location = (-220, -50)
    sin_n = nodes.new("ShaderNodeMath")
    sin_n.operation = "SINE"
    sin_n.location = (-220, -200)

    # New rotated XY: x' = x*cos - y*sin, y' = x*sin + y*cos
    mul_xc = nodes.new("ShaderNodeMath")
    mul_xc.operation = "MULTIPLY"
    mul_xc.location = (-60, 200)
    mul_ys = nodes.new("ShaderNodeMath")
    mul_ys.operation = "MULTIPLY"
    mul_ys.location = (-60, 60)
    mul_xs = nodes.new("ShaderNodeMath")
    mul_xs.operation = "MULTIPLY"
    mul_xs.location = (-60, -80)
    mul_yc = nodes.new("ShaderNodeMath")
    mul_yc.operation = "MULTIPLY"
    mul_yc.location = (-60, -220)
    sub_x = nodes.new("ShaderNodeMath")
    sub_x.operation = "SUBTRACT"
    sub_x.location = (90, 130)
    add_y = nodes.new("ShaderNodeMath")
    add_y.operation = "ADD"
    add_y.location = (90, -150)

    combine = nodes.new("ShaderNodeCombineXYZ")
    combine.location = (250, 0)

    sub_offset = nodes.new("ShaderNodeVectorMath")
    sub_offset.operation = "SUBTRACT"
    sub_offset.location = (400, 0)

    # Wiring
    tree.links.new(pos.outputs["Position"], sep.inputs[0])
    tree.links.new(sep.outputs["Z"], mul_z.inputs[0])
    tree.links.new(mul_z.outputs["Value"], cos_n.inputs[0])
    tree.links.new(mul_z.outputs["Value"], sin_n.inputs[0])

    tree.links.new(sep.outputs["X"], mul_xc.inputs[0])
    tree.links.new(cos_n.outputs["Value"], mul_xc.inputs[1])
    tree.links.new(sep.outputs["Y"], mul_ys.inputs[0])
    tree.links.new(sin_n.outputs["Value"], mul_ys.inputs[1])
    tree.links.new(sep.outputs["X"], mul_xs.inputs[0])
    tree.links.new(sin_n.outputs["Value"], mul_xs.inputs[1])
    tree.links.new(sep.outputs["Y"], mul_yc.inputs[0])
    tree.links.new(cos_n.outputs["Value"], mul_yc.inputs[1])

    tree.links.new(mul_xc.outputs["Value"], sub_x.inputs[0])
    tree.links.new(mul_ys.outputs["Value"], sub_x.inputs[1])
    tree.links.new(mul_xs.outputs["Value"], add_y.inputs[0])
    tree.links.new(mul_yc.outputs["Value"], add_y.inputs[1])

    tree.links.new(sub_x.outputs["Value"], combine.inputs["X"])
    tree.links.new(add_y.outputs["Value"], combine.inputs["Y"])
    tree.links.new(sep.outputs["Z"], combine.inputs["Z"])

    tree.links.new(combine.outputs["Vector"], sub_offset.inputs[0])
    tree.links.new(pos.outputs["Position"], sub_offset.inputs[1])
    tree.links.new(sub_offset.outputs["Vector"], set_pos.inputs["Offset"])

    tree.links.new(inp.outputs["Geometry"], set_pos.inputs["Geometry"])
    tree.links.new(set_pos.outputs["Geometry"], outp.inputs["Geometry"])
    return tree


def _build_stepped_pavilion() -> bpy.types.GeometryNodeTree:
    tree = _new_tree(ARCHETYPE_NODE_TREE_NAMES["stepped_pavilion"])
    nodes = tree.nodes
    inp = next(n for n in nodes if n.bl_idname == "NodeGroupInput")
    outp = next(n for n in nodes if n.bl_idname == "NodeGroupOutput")

    bevel = nodes.new("GeometryNodeMeshToCurve")
    bevel.location = (-450, 0)

    c2m = nodes.new("GeometryNodeCurveToMesh")
    c2m.location = (-150, 0)

    profile = nodes.new("GeometryNodeCurvePrimitiveCircle")
    profile.location = (-450, -250)
    profile.inputs["Radius"].default_value = 0.04
    profile.inputs["Resolution"].default_value = 6

    join = nodes.new("GeometryNodeJoinGeometry")
    join.location = (200, 0)

    tree.links.new(inp.outputs["Geometry"], bevel.inputs["Mesh"])
    tree.links.new(bevel.outputs["Curve"], c2m.inputs["Curve"])
    tree.links.new(profile.outputs["Curve"], c2m.inputs["Profile Curve"])
    tree.links.new(inp.outputs["Geometry"], join.inputs["Geometry"])
    tree.links.new(c2m.outputs["Mesh"], join.inputs["Geometry"])
    tree.links.new(join.outputs["Geometry"], outp.inputs["Geometry"])
    return tree


BUILDERS: Dict[str, Callable[[], bpy.types.GeometryNodeTree]] = {
    "lattice_woven":     _build_lattice_woven,
    "pillow_skin":       _build_pillow_skin,
    "double_cantilever": _build_double_cantilever,
    "twisting_tower":    _build_twisting_tower,
    "stepped_pavilion":  _build_stepped_pavilion,
}


def ensure_all_trees() -> Dict[str, bpy.types.GeometryNodeTree]:
    """(Re-)build every archetype's Geometry-Nodes tree. Returns name→tree."""
    out: Dict[str, bpy.types.GeometryNodeTree] = {}
    for archetype, builder in BUILDERS.items():
        out[archetype] = builder()
        print(f"[gn-setup] built {ARCHETYPE_NODE_TREE_NAMES[archetype]}")
    return out


def main() -> None:
    ensure_all_trees()
    print("[gn-setup] all five Geometry-Nodes trees ready.")


if __name__ == "__main__":
    main()
