"""A spinning cricket ball, modelled and rendered by Blender, for the site's opening animation.

Run it with:   blender -b -P animation/ball.py
Add  -- --keep-frames  to also save three single frames in animation/check/ to look at.

It writes one picture, frontend/public/intro/ball.webp: every frame of one full turn of the
ball, side by side on a clear background. The website moves and bounces that picture; all
this file decides is what the ball looks like and how it spins.

To change the look, edit the numbers in the block of constants below and run it again.
"""
import math
import sys
import tempfile
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))   # Blender does not look beside the script
import studio  # noqa: E402

# ---- what to change ----
FRAMES = 24                   # pictures in one full turn
FRAME_SIZE = 256              # each picture is this many pixels square
SAMPLES = 128
LEATHER = (0.50, 0.008, 0.016)  # deep cherry red, in linear colour
THREAD = (0.92, 0.86, 0.74)   # the off-white of the stitching
SEAM_TILT = math.radians(24)  # how far the seam leans from upright: this makes it wobble
STITCHES_PER_ROW = 76
STITCH_ROWS = (0.075, 0.15)   # how far each row sits from the seam, as an angle in radians


def add_leather(parent: bpy.types.Object) -> None:
    leather = studio.material("Leather", LEATHER, roughness=0.33, grain=0.18, lacquer=0.35)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=128, ring_count=64, radius=1)
    ball = bpy.context.object
    bpy.ops.object.shade_smooth()
    ball.data.materials.append(leather)
    ball.parent = parent

    # The raised ridge where the two halves of the ball are sewn together.
    bpy.ops.mesh.primitive_torus_add(major_radius=0.992, minor_radius=0.03, major_segments=128)
    ridge = bpy.context.object
    bpy.ops.object.shade_smooth()
    ridge.data.materials.append(leather)
    ridge.parent = parent


def add_stitches(parent: bpy.types.Object) -> None:
    """Rows of short slanted stitches on both sides of the seam."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=12, ring_count=6, radius=1)
    first = bpy.context.object
    first.data.materials.append(studio.material("Thread", THREAD, roughness=0.7))
    stitch_shape = first.data          # every stitch shares this one shape
    bpy.data.objects.remove(first)

    for side in (1, -1):
        for row in STITCH_ROWS:
            height = side * row        # the row's angle above or below the seam
            for index in range(STITCHES_PER_ROW):
                around = 2 * math.pi * index / STITCHES_PER_ROW
                on_ball = Vector((math.cos(height) * math.cos(around),
                                  math.cos(height) * math.sin(around), math.sin(height)))
                along_seam = Vector((-math.sin(around), math.cos(around), 0))
                across_seam = on_ball.cross(along_seam)
                slant = (along_seam * 0.55 + across_seam * side).normalized()

                stitch = bpy.data.objects.new("Stitch", stitch_shape)
                bpy.context.collection.objects.link(stitch)
                stitch.location = on_ball * 1.004
                stitch.scale = (0.034, 0.011, 0.009)       # long, thin, and nearly flat
                # Lay the stitch's long side along the slant, with its flat side on the ball.
                stitch.rotation_mode = "QUATERNION"
                stitch.rotation_quaternion = slant.to_track_quat("X", "Z")
                stitch.parent = parent


def build_ball() -> bpy.types.Object:
    """The ball, held by two handles: `seam` sets how the seam sits, `spin` turns the ball."""
    spin = bpy.data.objects.new("Spin", None)
    seam = bpy.data.objects.new("Seam", None)
    for handle in (spin, seam):
        bpy.context.collection.objects.link(handle)
    seam.parent = spin
    # Stand the seam upright, then lean it. A leaning seam wobbles as the ball turns.
    seam.rotation_euler = (0, math.radians(90), SEAM_TILT)
    add_leather(seam)
    add_stitches(seam)
    return spin


def spin_one_turn(spin: bpy.types.Object) -> None:
    """Turn the ball once, at a steady rate, about a level axis: a ball bowled with backspin."""
    spin.rotation_euler = (0, 0, 0)
    spin.keyframe_insert("rotation_euler", frame=1)
    spin.rotation_euler = (-2 * math.pi, 0, 0)
    spin.keyframe_insert("rotation_euler", frame=FRAMES + 1)   # frame FRAMES+1 equals frame 1
    for curve in spin.animation_data.action.fcurves:
        for point in curve.keyframe_points:
            point.interpolation = "LINEAR"


def join_side_by_side(files: list[Path]) -> bpy.types.Image:
    """Every frame in one row, as a single picture."""
    frames = []
    for file in files:
        image = bpy.data.images.load(str(file))
        frames.append(np.array(image.pixels[:], dtype=np.float32).reshape(FRAME_SIZE, FRAME_SIZE, 4))
        bpy.data.images.remove(image)
    sheet = bpy.data.images.new("Sheet", width=FRAME_SIZE * len(frames), height=FRAME_SIZE, alpha=True)
    sheet.pixels.foreach_set(np.hstack(frames).ravel())
    return sheet


def main() -> None:
    scene = studio.start_empty_scene(FRAME_SIZE, FRAME_SIZE, SAMPLES)
    spin_one_turn(build_ball())
    studio.add_camera(scene, shows=2.16)   # the ball is 2 units across, so it nearly fills the picture
    studio.add_lights(scene)
    with tempfile.TemporaryDirectory() as folder:
        files = []
        for frame in range(1, FRAMES + 1):
            scene.frame_set(frame)
            files.append(studio.render_png(scene, Path(folder) / f"{frame:03d}.png"))
        if "--keep-frames" in sys.argv:
            studio.CHECK_FOLDER.mkdir(exist_ok=True)
            for file in files[::8]:
                (studio.CHECK_FOLDER / f"ball-{file.name}").write_bytes(file.read_bytes())
        studio.save_webp(scene, join_side_by_side(files), "ball.webp")


if __name__ == "__main__":   # run as a script; other scenes import the ball from here
    main()
