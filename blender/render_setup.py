"""Configure render settings for the millennium-China animation.

Run *after* geometry_nodes_setup.py and import_and_animate.py. This script
does not start the render — that's `Render → Render Animation`. Output
goes to outputs/renders/ as either a PNG sequence or an MP4.

Engine: EEVEE Next (Blender 4.2+ default real-time renderer) with 64 TAA
samples, at 1080p / 24 fps for ≥ 60 s. EEVEE Next is chosen over Cycles
to keep wall-clock render time under ~1 hour for the 1536-frame helical
fly-through.

Look: studio black background. The world shader is a flat black
emission, the floor plane is removed (in import_and_animate.py), and the
camera is the only light direction-sensitive element — this turns each
fragment into a floating archetype against pure black, the studio /
museum-catalogue look that suits an architectural typology study far
better than the previous "outdoor sky" framing.
"""
from __future__ import annotations

import sys
from pathlib import Path

import bpy


def _script_dir() -> Path:
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

from cluster_io import project_root  # noqa: E402

RENDER_DIR = project_root() / "outputs" / "renders"
PNG_DIR = RENDER_DIR / "frames"
MP4_PATH = RENDER_DIR / "millennium_china.mp4"

EEVEE_TAA_SAMPLES = 64
RESOLUTION = (1920, 1080)


def _ensure_dirs() -> None:
    PNG_DIR.mkdir(parents=True, exist_ok=True)


def _configure_engine() -> None:
    scene = bpy.context.scene

    # Blender 4.2+ uses BLENDER_EEVEE_NEXT; older 4.x falls back gracefully.
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"

    if hasattr(scene, "eevee"):
        if hasattr(scene.eevee, "taa_render_samples"):
            scene.eevee.taa_render_samples = EEVEE_TAA_SAMPLES
        # Raytracing OFF — on RTX 3060 Laptop it pushes per-frame from 1.5s
        # to 6.5s and GPU temp to 89°C. The scene has no mirror surfaces
        # that would visually need it; shadows + AO from screen-space are
        # sufficient for the architectural fragment fly-through.
        if hasattr(scene.eevee, "use_raytracing"):
            scene.eevee.use_raytracing = False
        if hasattr(scene.eevee, "use_shadow_jitter_viewport"):
            scene.eevee.use_shadow_jitter_viewport = True

    scene.render.resolution_x = RESOLUTION[0]
    scene.render.resolution_y = RESOLUTION[1]
    scene.render.resolution_percentage = 100

    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.look = "Medium Contrast"
    # Slight negative exposure so the porcelain-white BSDFs don't bloom
    # against the pure-black world.
    scene.view_settings.exposure = -0.3


def _configure_world() -> None:
    """Pure-black studio world — single Background node, zero strength sky.

    Replaces the previous Nishita sky / outdoor look. With a black world
    the only contribution to lighting comes from the SUN + AREA lamps in
    import_and_animate.py, which gives each fragment a clean rim/key
    silhouette and lets the geometry read as a museum-catalogue plate.
    """
    world = bpy.context.scene.world
    world.use_nodes = True
    nt = world.node_tree
    for node in list(nt.nodes):
        nt.nodes.remove(node)
    bg = nt.nodes.new("ShaderNodeBackground")
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    bg.inputs["Strength"].default_value = 0.0
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])


def _configure_png_output() -> None:
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.compression = 15
    scene.render.filepath = str(PNG_DIR / "frame_")
    scene.render.use_file_extension = True


def _configure_mp4_output() -> None:
    scene = bpy.context.scene
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    scene.render.ffmpeg.audio_codec = "NONE"
    scene.render.filepath = str(MP4_PATH)


def main(target: str = "mp4") -> None:
    """target='png' (frame sequence) or 'mp4' (single video file)."""
    _ensure_dirs()
    _configure_engine()
    _configure_world()
    if target == "mp4":
        _configure_mp4_output()
    else:
        _configure_png_output()
    print(f"[render] engine={bpy.context.scene.render.engine} "
          f"samples={EEVEE_TAA_SAMPLES} resolution={RESOLUTION} target={target}")
    print(f"[render] output → {bpy.context.scene.render.filepath}")


if __name__ == "__main__":
    main(target="mp4")
