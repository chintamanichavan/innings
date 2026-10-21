"""A cricket helmet, modelled and rendered by Blender. It sits on the small "i" of "Innings"
in the site's opening animation, in place of the dot.

Run it with:   blender -b -P animation/helmet.py
Add  -- --keep-frames  to also save the picture as a PNG in animation/check/ to look at.

It writes frontend/public/intro/helmet.webp, on a clear background. The helmet is plain: one
colour, a peak, and a steel grille, with no badge. To change the look, edit the constants
below and run it again.
"""
import math
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))   # Blender does not look beside the script
import studio  # noqa: E402

# ---- what to change ----
SIZE = 320                    # the picture is this many pixels square
SAMPLES = 192
SHELL = (0.02, 0.10, 0.42)    # a clear blue that shows on light and dark pages alike
STEEL = (0.62, 0.63, 0.66)
TURN = math.radians(38)       # the helmet is turned, so we see the peak and the grille from the side

RADIUS = 0.5
SHELL_SHAPE = (1.0, 1.14, 0.96)   # a head is longer front to back than side to side
RIM_HEIGHT = -0.36            # the shell stops here, low enough to cover the ears and neck
# The face opening is a wedge cut from the front: it starts at the brow and slopes back and down.
BROW = (0, -0.57, 0.02)
OPENING_SLOPE = 2.1
GRILLE_BARS = (-0.10, -0.20, -0.30)   # the height of each bar across the face
BAR_THICKNESS = 0.017


def shell_material() -> bpy.types.Material:
    return studio.material("Shell", SHELL, roughness=0.28, lacquer=0.5)


def steel_material() -> bpy.types.Material:
    steel = studio.material("Steel", STEEL, roughness=0.3)
    steel.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 1
    return steel


def keep_one_side(obj: bpy.types.Object, point: tuple, facing: tuple) -> None:
    """Cut an object with a flat plane and throw away the part the plane faces."""
    mesh = bmesh.new()
    mesh.from_mesh(obj.data)
    everything = mesh.verts[:] + mesh.edges[:] + mesh.faces[:]
    bmesh.ops.bisect_plane(mesh, geom=everything, plane_co=point, plane_no=facing, clear_outer=True)
    mesh.to_mesh(obj.data)
    mesh.free()


def add_shell(parent: bpy.types.Object) -> None:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=48, radius=RADIUS)
    shell = bpy.context.object
    shell.scale = SHELL_SHAPE
    bpy.ops.object.transform_apply(scale=True)
    keep_one_side(shell, point=(0, 0, RIM_HEIGHT), facing=(0, 0, -1))
    keep_one_side(shell, point=BROW, facing=(0, -1, -OPENING_SLOPE))
    bpy.ops.object.shade_smooth()
    wall = shell.modifiers.new("Wall", "SOLIDIFY")   # a shell has thickness, which shows at the rim
    wall.thickness = 0.035
    shell.data.materials.append(shell_material())
    shell.parent = parent


def add_peak(parent: bpy.types.Object) -> None:
    """The stiff brim over the eyes."""
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=1)
    peak = bpy.context.object
    peak.scale = (0.40, 0.30, 0.035)
    peak.location = (0, -0.62, 0.03)
    peak.rotation_euler = (math.radians(-10), 0, 0)   # tipped down a little at the front
    bpy.ops.object.shade_smooth()
    peak.data.materials.append(shell_material())
    peak.parent = parent


def add_grille(parent: bpy.types.Object) -> None:
    """Steel bars across the face, and two uprights that hold them to the peak."""
    steel = steel_material()
    for height in GRILLE_BARS:
        bpy.ops.mesh.primitive_torus_add(major_radius=0.47, minor_radius=BAR_THICKNESS,
                                         major_segments=96, location=(0, 0, height))
        bar = bpy.context.object
        bar.scale = (1.0, 1.28, 1.0)                 # bowed out in front of the face
        bpy.ops.object.transform_apply(location=True, scale=True)
        keep_one_side(bar, point=(0, 0.02, 0), facing=(0, 1, 0))   # only the front half is a bar
        bpy.ops.object.shade_smooth()
        bar.data.materials.append(steel)
        bar.parent = parent

    top, bottom = 0.03, GRILLE_BARS[-1]
    for across in (-0.17, 0.17):
        forward = -0.6 * math.sqrt(1 - (across / 0.47) ** 2)   # on the bars' curve at this point
        bpy.ops.mesh.primitive_cylinder_add(radius=BAR_THICKNESS * 0.9, depth=top - bottom, vertices=16,
                                            location=(across, forward, (top + bottom) / 2))
        upright = bpy.context.object
        bpy.ops.object.shade_smooth()
        upright.data.materials.append(steel)
        upright.parent = parent


def build_helmet() -> None:
    helmet = bpy.data.objects.new("Helmet", None)
    bpy.context.collection.objects.link(helmet)
    add_shell(helmet)
    add_peak(helmet)
    add_grille(helmet)
    helmet.rotation_euler = (0, 0, TURN)


def main() -> None:
    scene = studio.start_empty_scene(SIZE, SIZE, SAMPLES)
    build_helmet()
    middle = (0.04, 0, 0.06)   # the helmet's middle: the peak sticks out in front
    studio.add_camera(scene, shows=1.36, looks_at=middle)
    studio.add_lights(scene, around=middle)
    with tempfile.TemporaryDirectory() as folder:
        file = studio.render_png(scene, Path(folder) / "helmet.png")
        if "--keep-frames" in sys.argv:
            studio.CHECK_FOLDER.mkdir(exist_ok=True)
            (studio.CHECK_FOLDER / "helmet.png").write_bytes(file.read_bytes())
        studio.save_webp(scene, bpy.data.images.load(str(file)), "helmet.webp")


main()
