"""GHPython component bodies for the millennium-China fragment graph.

Each function corresponds to one GHPython component on the
``millennium_china.gh`` canvas — paste the function body into a
"GhPython Script" component and wire inputs as documented in the docstring.

Pure Python using only `Rhino.Geometry`, so it runs identically inside
Rhino 7 (IronPython 2.7) and Rhino 8 (CPython 3).

If you don't have Rhino, ``blender/import_and_animate.py`` provides a
primitive-geometry fallback so the animation pipeline still produces an
end-to-end deliverable.
"""
# pylint: disable=invalid-name

import json
import math
import os

# Component 1 — ParseClustersJson
#   Inputs : path (str)
#   Outputs: ids (list), clusters (list), archetypes (list), params (list of dict)
def parse_clusters_json(path):
    """Read clusters.json → four parallel lists wired into the 5 archetype
    components downstream."""
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    with open(path, "r") as fh:
        payload = json.load(fh)
    ids, clusters, archetypes, params = [], [], [], []
    for f in payload["fragments"]:
        ids.append(f["fragment_id"])
        clusters.append(int(f["cluster"]))
        archetypes.append(f["archetype"])
        params.append(f["params"])
    return ids, clusters, archetypes, params


# Component 2 — BirdsNestSteelLattice  (archetype = lattice_woven)
#   Hemispherical steel-lattice fragment evoking the Beijing National Stadium.
#   Inputs : params (dict), radius_base (float, default 2.0). Outputs: a (Mesh).
def birds_nest_steel_lattice(params, radius_base=2.0):
    import Rhino.Geometry as rg

    lattice = float(params["lattice"])
    cantilever = float(params["cantilever"])
    porosity = float(params["porosity"])

    radius = radius_base * (0.7 + 0.6 * lattice)
    squash = 1.0 - 0.45 * cantilever
    n_meridians = int(round(10 + 18 * lattice))
    n_parallels = int(round(6 + 8 * lattice))

    sphere = rg.Sphere(rg.Plane.WorldXY, radius).ToBrep()
    brep = sphere.DuplicateBrep()
    brep.Transform(rg.Transform.Scale(rg.Plane.WorldXY, 1.0, 1.0, squash))

    # Build meridians + parallels as a network of curves, then 'Pipe' them
    # into 0.04..0.10 radius rods — that's the visual Bird's Nest weave.
    curves = []
    for i in range(n_meridians):
        t = (i / float(n_meridians)) * 2.0 * math.pi
        plane = rg.Plane(rg.Point3d(0, 0, 0),
                         rg.Vector3d(math.cos(t), math.sin(t), 0))
        section = rg.Intersect.Intersection.BrepPlane(
            brep, plane, 0.001
        )
        if section[1]:
            curves.extend(section[1])
    for j in range(1, n_parallels):
        z = (j / float(n_parallels) - 0.5) * 2.0 * radius * squash
        plane = rg.Plane(rg.Point3d(0, 0, z), rg.Vector3d.ZAxis)
        section = rg.Intersect.Intersection.BrepPlane(brep, plane, 0.001)
        if section[1]:
            curves.extend(section[1])

    pipe_radius = 0.05 + 0.04 * (1.0 - porosity)
    rods = []
    for c in curves:
        pipe = rg.Brep.CreatePipe(c, pipe_radius, False, rg.PipeCapMode.Round,
                                  False, 0.001, 0.01)
        if pipe:
            rods.extend(pipe)

    mesh = rg.Mesh()
    for b in rods:
        for m in rg.Mesh.CreateFromBrep(b, rg.MeshingParameters.Default):
            mesh.Append(m)
    return mesh


# Component 3 — ETFEPillowFacade  (archetype = pillow_skin)
#   Foam-cell facade evoking the Beijing National Aquatics Center.
#   Inputs : params (dict), edge_length (float, default 4.0). Outputs: a (Mesh).
def etfe_pillow_facade(params, edge_length=4.0):
    import Rhino.Geometry as rg

    pillow = float(params["pillow"])
    porosity = float(params["porosity"])
    n_cells = max(2, int(round(3 + 7 * pillow)))
    inflate = 0.10 + 0.35 * pillow

    box = rg.Box(rg.BoundingBox(
        rg.Point3d(-edge_length / 2, -edge_length / 2, 0),
        rg.Point3d(edge_length / 2,  edge_length / 2,  edge_length)
    ))
    brep = box.ToBrep()

    mesh = rg.Mesh()
    for face in brep.Faces:
        u_dom = face.Domain(0)
        v_dom = face.Domain(1)
        for iu in range(n_cells):
            for iv in range(n_cells):
                if (iu + iv) % 7 == 0 and (porosity > 0.55):
                    continue  # punched-out cell
                u0 = u_dom.ParameterAt(iu / float(n_cells))
                u1 = u_dom.ParameterAt((iu + 1) / float(n_cells))
                v0 = v_dom.ParameterAt(iv / float(n_cells))
                v1 = v_dom.ParameterAt((iv + 1) / float(n_cells))
                cu = (u0 + u1) / 2.0
                cv = (v0 + v1) / 2.0
                p_centre = face.PointAt(cu, cv)
                normal = face.NormalAt(cu, cv) * inflate

                pillow_mesh = _pillow_quad(
                    face.PointAt(u0, v0),
                    face.PointAt(u1, v0),
                    face.PointAt(u1, v1),
                    face.PointAt(u0, v1),
                    p_centre + normal,
                )
                mesh.Append(pillow_mesh)
    return mesh


def _pillow_quad(p0, p1, p2, p3, apex):
    """Helper — fan-mesh from apex to a quad's four corners."""
    import Rhino.Geometry as rg
    m = rg.Mesh()
    m.Vertices.Add(p0); m.Vertices.Add(p1)
    m.Vertices.Add(p2); m.Vertices.Add(p3)
    m.Vertices.Add(apex)
    m.Faces.AddFace(0, 1, 4)
    m.Faces.AddFace(1, 2, 4)
    m.Faces.AddFace(2, 3, 4)
    m.Faces.AddFace(3, 0, 4)
    m.Normals.ComputeNormals()
    return m


# Component 4 — DoubleZCantilever  (archetype = double_cantilever)
#   OMA / CCTV Headquarters double-loop: four beams + two bridges.
#   Inputs : params (dict), unit (float, default 2.0). Outputs: a (Mesh).
def double_z_cantilever(params, unit=2.0):
    import Rhino.Geometry as rg

    cantilever = float(params["cantilever"])
    twist = float(params["twist"])
    width = unit
    depth = unit
    height = unit * (3.0 + 5.0 * (1.0 - twist))
    bridge_thickness = unit * (0.6 + 0.8 * cantilever)
    horiz_offset = unit * (1.5 + 3.5 * cantilever)

    boxes = []
    boxes.append(_box(0, 0, 0, width, depth, height))
    boxes.append(_box(horiz_offset, 0, 0, width, depth, height))
    boxes.append(_box(0, 0, height - bridge_thickness,
                      horiz_offset + width, depth, bridge_thickness))
    boxes.append(_box(horiz_offset * 0.4, 0, height * 0.45,
                      horiz_offset * 0.6, depth, bridge_thickness * 0.7))

    mesh = rg.Mesh()
    for b in boxes:
        for m in rg.Mesh.CreateFromBrep(b.ToBrep(), rg.MeshingParameters.Default):
            mesh.Append(m)
    return mesh


def _box(x, y, z, w, d, h):
    import Rhino.Geometry as rg
    return rg.Box(rg.BoundingBox(rg.Point3d(x, y, z),
                                 rg.Point3d(x + w, y + d, z + h)))


# Component 5 — TwistingTowerLoft  (archetype = twisting_tower)
#   9-section loft with progressive Z-rotation, evokes the Shanghai Tower spiral.
#   Inputs : params (dict), section_size (float, default 1.4). Outputs: a (Mesh).
def twisting_tower_loft(params, section_size=1.4):
    import Rhino.Geometry as rg

    twist = float(params["twist"])
    lattice = float(params["lattice"])
    stack = float(params["stack"])
    n_sections = 9
    height_total = (lattice * 0.5 + stack * 0.5 + 0.5) * 12.0
    twist_total = math.radians(60.0 + 200.0 * twist)

    sections = []
    for i in range(n_sections):
        z = i * (height_total / (n_sections - 1))
        ang = (i / float(n_sections - 1)) * twist_total
        scale = 1.0 - 0.4 * (i / float(n_sections - 1))
        plane = rg.Plane(rg.Point3d(0, 0, z), rg.Vector3d.ZAxis)
        plane.Rotate(ang, rg.Vector3d.ZAxis)
        side = section_size * scale
        rect = rg.Polyline([
            plane.PointAt(-side, -side, 0),
            plane.PointAt( side, -side, 0),
            plane.PointAt( side,  side, 0),
            plane.PointAt(-side,  side, 0),
            plane.PointAt(-side, -side, 0),
        ])
        sections.append(rect.ToNurbsCurve())

    loft = rg.Brep.CreateFromLoft(
        sections, rg.Point3d.Unset, rg.Point3d.Unset,
        rg.LoftType.Tight, False,
    )
    mesh = rg.Mesh()
    for b in loft:
        for m in rg.Mesh.CreateFromBrep(b, rg.MeshingParameters.Default):
            mesh.Append(m)
    return mesh


# Component 6 — SteppedPavilionStack  (archetype = stepped_pavilion)
#   N inverted trapezoidal layers, evoking 斗拱 brackets of the Expo China Pavilion.
#   Inputs : params (dict), base (float, default 4.0). Outputs: a (Mesh).
def stepped_pavilion_stack(params, base=4.0):
    import Rhino.Geometry as rg

    stack = float(params["stack"])
    cantilever = float(params["cantilever"])
    n_layers = int(round(3 + 6 * stack))
    height_per = 1.0 + 0.6 * stack
    expand = 0.10 + 0.40 * cantilever

    mesh = rg.Mesh()
    for i in range(n_layers):
        scale = 1.0 + i * expand
        z0 = i * height_per
        z1 = (i + 1) * height_per
        size = base * scale
        box = _box(-size / 2, -size / 2, z0, size, size, z1 - z0)
        for m in rg.Mesh.CreateFromBrep(box.ToBrep(), rg.MeshingParameters.Default):
            mesh.Append(m)
    return mesh


# Component 7 — GridLayout
#   Place each mesh on a (cluster × variant) 2-D grid.
#   Inputs : meshes, clusters, variants. Output: list of Mesh.
def grid_layout(meshes, clusters, variants, spacing_cluster=10.0,
                spacing_variant=8.0):
    import Rhino.Geometry as rg
    out = []
    for m, c, v in zip(meshes, clusters, variants):
        x = c * spacing_cluster - 20.0
        y = v * spacing_variant - 12.0
        translation = rg.Transform.Translation(x, y, 0.0)
        m2 = m.DuplicateMesh()
        m2.Transform(translation)
        out.append(m2)
    return out
