"""All-in-one GHPython component for the Millennium-China fragment graph.

WHY THIS FILE EXISTS
====================
The "proper" demo131 graph is a 7-component canvas (see README_GH.md +
ghpython_components.py). For graders / users who don't want to wire that
up by hand, this single file does the whole pipeline inside ONE GHPython
component: read clusters.json → build 20 meshes → grid-lay them out →
export 20 OBJs → return them for preview.

HOW TO USE  (Rhino 7 / 8 + Grasshopper)
=======================================
  1. Open Rhino. Type `grasshopper` in the Rhino command line and press
     Enter — Grasshopper opens.
  2. From the toolbar, drop a "GhPython Script" component onto the canvas
     (Maths → Script → GhPython).
  3. Right-click the component → "Edit Script". A code editor opens.
  4. Paste the ENTIRE contents of this file into the editor and click OK.
  5. Right-click the component's input "x" → Type Hint → str (Python str).
     Right-click "y" → Type Hint → str.
  6. Wire two String Panels into the inputs:
       x  →  E:\\Desktop\\demo\\demo131\\outputs\\fragments_params\\clusters.json
       y  →  E:\\Desktop\\demo\\demo131\\outputs\\gh_meshes
  7. The component evaluates automatically. Output `a` is the list of 20
     Meshes (you'll see them in the Rhino viewport once you connect them
     to a Mesh component or just preview-toggle them on).
  8. Export — the OBJs are written to ``y`` automatically, one file per
     fragment, named ``frag-c{cluster:02d}-v{variant:02d}.obj``.
  9. SAVE THE GRASSHOPPER FILE: File → Save As → millennium_china.gh,
     in this folder. That .gh is what your submission needs.

INPUTS  (set Type Hints as noted in step 5)
   x : str  — absolute path to clusters.json
   y : str  — absolute path to the OBJ output folder
OUTPUTS
   a : list[Mesh] — the 20 generated fragment meshes (laid out on a grid)
   info : str     — a one-line status report

Code style is IronPython-2.7 friendly (no f-strings, no type hints, no
Python-3-only stdlib calls), so it runs unmodified in Rhino 7's GHPython
as well as Rhino 8's CPython 3 GHPython.
"""
# pylint: disable=invalid-name

import json
import math
import os

import Rhino.Geometry as rg


# ===========================================================================
# Helpers shared by every archetype builder
# ===========================================================================

def _box_brep(x, y, z, w, d, h):
    return rg.Box(rg.BoundingBox(rg.Point3d(x, y, z),
                                 rg.Point3d(x + w, y + d, z + h))).ToBrep()


def _mesh_from_brep(brep):
    out = rg.Mesh()
    pieces = rg.Mesh.CreateFromBrep(brep, rg.MeshingParameters.Default)
    if pieces:
        for piece in pieces:
            out.Append(piece)
    return out


def _join(*meshes):
    out = rg.Mesh()
    for m in meshes:
        if m is not None and m.Vertices.Count > 0:
            out.Append(m)
    return out


# ===========================================================================
# Archetype 1 — lattice_woven  (Beijing National Stadium, "Bird's Nest")
# ===========================================================================

def build_lattice_woven(params, radius_base=2.0):
    lattice = float(params.get("lattice", 0.5))
    cantilever = float(params.get("cantilever", 0.5))
    porosity = float(params.get("porosity", 0.5))

    radius = radius_base * (0.7 + 0.6 * lattice)
    squash = 1.0 - 0.45 * cantilever
    n_meridians = int(round(8 + 12 * lattice))
    n_parallels = int(round(5 + 6 * lattice))

    sphere = rg.Sphere(rg.Plane.WorldXY, radius).ToBrep()
    sphere.Transform(rg.Transform.Scale(rg.Plane.WorldXY, 1.0, 1.0, squash))

    curves = []
    for i in range(n_meridians):
        t = (i / float(n_meridians)) * 2.0 * math.pi
        plane = rg.Plane(rg.Point3d(0, 0, 0),
                         rg.Vector3d(math.cos(t), math.sin(t), 0.0))
        section = rg.Intersect.Intersection.BrepPlane(sphere, plane, 0.001)
        if section[0] and section[1]:
            curves.extend(section[1])
    for j in range(1, n_parallels):
        z = (j / float(n_parallels) - 0.5) * 2.0 * radius * squash
        plane = rg.Plane(rg.Point3d(0, 0, z), rg.Vector3d.ZAxis)
        section = rg.Intersect.Intersection.BrepPlane(sphere, plane, 0.001)
        if section[0] and section[1]:
            curves.extend(section[1])

    pipe_radius = 0.05 + 0.04 * (1.0 - porosity)
    out = rg.Mesh()
    for c in curves:
        breps = rg.Brep.CreatePipe(c, pipe_radius, False,
                                   rg.PipeCapMode.Round, False, 0.001, 0.01)
        if not breps:
            continue
        for b in breps:
            out.Append(_mesh_from_brep(b))
    return out


# ===========================================================================
# Archetype 2 — pillow_skin  (National Aquatics Center, "Water Cube")
# ===========================================================================

def _pillow_quad(p0, p1, p2, p3, apex):
    m = rg.Mesh()
    m.Vertices.Add(p0)
    m.Vertices.Add(p1)
    m.Vertices.Add(p2)
    m.Vertices.Add(p3)
    m.Vertices.Add(apex)
    m.Faces.AddFace(0, 1, 4)
    m.Faces.AddFace(1, 2, 4)
    m.Faces.AddFace(2, 3, 4)
    m.Faces.AddFace(3, 0, 4)
    m.Normals.ComputeNormals()
    return m


def build_pillow_skin(params, edge_length=4.0):
    pillow = float(params.get("pillow", 0.5))
    porosity = float(params.get("porosity", 0.5))
    n_cells = max(2, int(round(3 + 5 * pillow)))
    inflate = 0.10 + 0.35 * pillow

    box = _box_brep(-edge_length / 2.0, -edge_length / 2.0, 0.0,
                    edge_length, edge_length, edge_length)

    out = rg.Mesh()
    for face in box.Faces:
        u_dom = face.Domain(0)
        v_dom = face.Domain(1)
        for iu in range(n_cells):
            for iv in range(n_cells):
                if (iu + iv) % 7 == 0 and porosity > 0.55:
                    continue
                u0 = u_dom.ParameterAt(iu / float(n_cells))
                u1 = u_dom.ParameterAt((iu + 1) / float(n_cells))
                v0 = v_dom.ParameterAt(iv / float(n_cells))
                v1 = v_dom.ParameterAt((iv + 1) / float(n_cells))
                cu = (u0 + u1) / 2.0
                cv = (v0 + v1) / 2.0
                p_centre = face.PointAt(cu, cv)
                normal = face.NormalAt(cu, cv) * inflate
                out.Append(_pillow_quad(
                    face.PointAt(u0, v0),
                    face.PointAt(u1, v0),
                    face.PointAt(u1, v1),
                    face.PointAt(u0, v1),
                    p_centre + normal,
                ))
    return out


# ===========================================================================
# Archetype 3 — double_cantilever  (CCTV Headquarters)
# ===========================================================================

def build_double_cantilever(params, unit=2.0):
    cantilever = float(params.get("cantilever", 0.5))
    twist = float(params.get("twist", 0.5))
    width = unit
    depth = unit
    height = unit * (3.0 + 5.0 * (1.0 - twist))
    bridge_thickness = unit * (0.6 + 0.8 * cantilever)
    horiz_offset = unit * (1.5 + 3.5 * cantilever)

    breps = [
        _box_brep(0.0, 0.0, 0.0, width, depth, height),
        _box_brep(horiz_offset, 0.0, 0.0, width, depth, height),
        _box_brep(0.0, 0.0, height - bridge_thickness,
                  horiz_offset + width, depth, bridge_thickness),
        _box_brep(horiz_offset * 0.4, 0.0, height * 0.45,
                  horiz_offset * 0.6, depth, bridge_thickness * 0.7),
    ]
    out = rg.Mesh()
    for b in breps:
        out.Append(_mesh_from_brep(b))
    return out


# ===========================================================================
# Archetype 4 — twisting_tower  (Shanghai Tower)
# ===========================================================================

def build_twisting_tower(params, section_size=1.4):
    twist = float(params.get("twist", 0.5))
    lattice = float(params.get("lattice", 0.5))
    stack = float(params.get("stack", 0.5))
    n_sections = 9
    height_total = (lattice * 0.5 + stack * 0.5 + 0.5) * 12.0
    twist_total = math.radians(60.0 + 200.0 * twist)

    sections = []
    for i in range(n_sections):
        z = i * (height_total / (n_sections - 1))
        ang = (i / float(n_sections - 1)) * twist_total
        scale = 1.0 - 0.4 * (i / float(n_sections - 1))
        plane = rg.Plane(rg.Point3d(0.0, 0.0, z), rg.Vector3d.ZAxis)
        plane.Rotate(ang, rg.Vector3d.ZAxis)
        side = section_size * scale
        rect = rg.Polyline([
            plane.PointAt(-side, -side, 0.0),
            plane.PointAt(side, -side, 0.0),
            plane.PointAt(side, side, 0.0),
            plane.PointAt(-side, side, 0.0),
            plane.PointAt(-side, -side, 0.0),
        ])
        sections.append(rect.ToNurbsCurve())

    loft = rg.Brep.CreateFromLoft(
        sections, rg.Point3d.Unset, rg.Point3d.Unset,
        rg.LoftType.Tight, False,
    )
    out = rg.Mesh()
    if loft:
        for b in loft:
            out.Append(_mesh_from_brep(b))
    return out


# ===========================================================================
# Archetype 5 — stepped_pavilion  (Shanghai Expo China Pavilion, 斗拱 stack)
# ===========================================================================

def build_stepped_pavilion(params, base=4.0):
    stack = float(params.get("stack", 0.5))
    cantilever = float(params.get("cantilever", 0.5))
    n_layers = int(round(3 + 6 * stack))
    height_per = 1.0 + 0.6 * stack
    expand = 0.10 + 0.40 * cantilever

    out = rg.Mesh()
    for i in range(n_layers):
        scale = 1.0 + i * expand
        z0 = i * height_per
        z1 = (i + 1) * height_per
        size = base * scale
        out.Append(_mesh_from_brep(
            _box_brep(-size / 2.0, -size / 2.0, z0, size, size, z1 - z0)
        ))
    return out


ARCHETYPE_BUILDERS = {
    "lattice_woven":     build_lattice_woven,
    "pillow_skin":       build_pillow_skin,
    "double_cantilever": build_double_cantilever,
    "twisting_tower":    build_twisting_tower,
    "stepped_pavilion":  build_stepped_pavilion,
}


# ===========================================================================
# OBJ export — IronPython has no `pathlib`, write OBJ ourselves
# ===========================================================================

def _write_obj(mesh, out_path):
    if mesh is None or mesh.Vertices.Count == 0:
        return False
    with open(out_path, "w") as fh:
        fh.write("# demo131 millennium-China fragment\n")
        for v in mesh.Vertices:
            fh.write("v %.6f %.6f %.6f\n" % (v.X, v.Y, v.Z))
        for f in mesh.Faces:
            if f.IsQuad:
                fh.write("f %d %d %d %d\n" % (f.A + 1, f.B + 1, f.C + 1, f.D + 1))
            else:
                fh.write("f %d %d %d\n" % (f.A + 1, f.B + 1, f.C + 1))
    return True


# ===========================================================================
# Main pipeline — runs once per Grasshopper recompute
# ===========================================================================

def _layout_xy(cluster_idx, variant_idx,
               cluster_spacing=10.0, variant_spacing=8.0):
    return (cluster_idx * cluster_spacing - 20.0,
            variant_idx * variant_spacing - 12.0)


def main(json_path, out_dir):
    if not json_path or not os.path.exists(json_path):
        return [], "ERROR: clusters.json not found at " + str(json_path)
    if not out_dir:
        return [], "ERROR: please connect an output directory to input `y`."
    if not os.path.isdir(out_dir):
        try:
            os.makedirs(out_dir)
        except OSError as exc:
            return [], "ERROR: cannot create output dir: " + str(exc)

    with open(json_path, "r") as fh:
        payload = json.load(fh)

    fragments = payload.get("fragments", [])
    out_meshes = []
    written = 0
    for frag in fragments:
        builder = ARCHETYPE_BUILDERS.get(frag["archetype"])
        if builder is None:
            continue
        mesh = builder(frag["params"])
        ci = int(frag["cluster"])
        vi = int(frag["variant"])
        dx, dy = _layout_xy(ci, vi)
        mesh.Transform(rg.Transform.Translation(dx, dy, 0.0))
        out_meshes.append(mesh)
        path = os.path.join(out_dir, frag["fragment_id"] + ".obj")
        if _write_obj(mesh, path):
            written += 1

    info = "OK: %d / %d meshes built, %d OBJs exported to %s" % (
        len(out_meshes), len(fragments), written, out_dir,
    )
    return out_meshes, info


# ===========================================================================
# Grasshopper entry — reads inputs `x` and `y`, sets outputs `a` and `info`
# ===========================================================================

a, info = main(x, y)  # noqa: F821 (x, y are GH-injected globals)
