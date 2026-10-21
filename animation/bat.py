"""A cricket bat standing upright, modelled and rendered by Blender. It stands in for the
letter "I" of "Innings" in the site's opening animation. It is a plain bat: clean willow,
no stickers and no maker's mark.

Run it with:   blender -b -P animation/bat.py
Add  -- --keep-frames  to also save the picture as a PNG in animation/check/ to look at.

It writes frontend/public/intro/bat.webp, on a clear background. Sizes are in metres and
follow a real bat. To change the look, edit the constants below and run it again.
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
WIDTH, HEIGHT = 224, 1024     # the picture, in pixels
SAMPLES = 192
WILLOW = (0.80, 0.63, 0.38)   # pale bat willow, in linear colour
GRAIN = (0.62, 0.45, 0.24)    # the darker lines of the wood's grain
GRIP = (0.70, 0.70, 0.73)     # a pale rubber grip, so it shows on light and dark pages alike
CANE = (0.58, 0.40, 0.20)     # the handle's cane, seen where it joins the blade
SPLICE_LENGTH = 0.11          # how far the handle's V runs down the blade
TURN = math.radians(-28)      # the bat is turned a little, so its thickness shows

BLADE_WIDTH, BLADE_LENGTH, BLADE_DEPTH = 0.108, 0.56, 0.045
HANDLE_RADIUS, HANDLE_LENGTH = 0.0165, 0.29
# The blade from toe to shoulder: (height, width, depth at the edges, depth at the spine).
# The spine is the ridge down the back that gives a bat its weight.
PROFILE = [
    (0.000, 0.094, 0.012, 0.018),
    (0.020, 0.106, 0.016, 0.034),
    (0.170, BLADE_WIDTH, 0.018, BLADE_DEPTH),
    (0.400, BLADE_WIDTH, 0.016, 0.034),
    (0.500, BLADE_WIDTH, 0.014, 0.022),
    (BLADE_LENGTH, 0.050, 0.014, 0.018),
]


def willow() -> bpy.types.Material:
    """Pale wood with fine straight grain running the length of the blade."""
    wood = studio.material("Willow", WILLOW, roughness=0.42, lacquer=0.15)
    nodes, links = wood.node_tree.nodes, wood.node_tree.links
    place = nodes.new("ShaderNodeTexCoord")
    stretch = nodes.new("ShaderNodeMapping")
    stretch.inputs["Scale"].default_value = (150, 150, 1.5)   # tight across the blade, long along it
    lines = nodes.new("ShaderNodeTexNoise")
    lines.inputs["Scale"].default_value = 1.0
    lines.inputs["Detail"].default_value = 3
    blend = nodes.new("ShaderNodeMixRGB")
    blend.inputs["Color1"].default_value = (*WILLOW, 1)
    blend.inputs["Color2"].default_value = (*GRAIN, 1)
    links.new(place.outputs["Object"], stretch.inputs["Vector"])
    links.new(stretch.outputs["Vector"], lines.inputs["Vector"])
    links.new(lines.outputs["Fac"], blend.inputs["Fac"])
    links.new(blend.outputs["Color"], wood.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    return wood


def add_blade(parent: bpy.types.Object) -> None:
    """The blade, built as a stack of five-sided slices: a flat face and a ridged back."""
    mesh = bmesh.new()
    rings = []
    for height, width, edge_depth, spine_depth in PROFILE:
        half = width / 2
        corners = [(-half, 0), (half, 0), (half, edge_depth), (0, spine_depth), (-half, edge_depth)]
        rings.append([mesh.verts.new((x, y, height)) for x, y in corners])
    for lower, upper in zip(rings, rings[1:], strict=False):
        for index in range(len(lower)):
            after = (index + 1) % len(lower)
            mesh.faces.new((lower[index], lower[after], upper[after], upper[index]))
    mesh.faces.new(reversed(rings[0]))     # the toe
    mesh.faces.new(rings[-1])              # the shoulder, where the handle goes in
    bmesh.ops.recalc_face_normals(mesh, faces=mesh.faces)

    shape = bpy.data.meshes.new("Blade")
    mesh.to_mesh(shape)
    mesh.free()
    blade = bpy.data.objects.new("Blade", shape)
    bpy.context.collection.objects.link(blade)
    blade.data.materials.append(willow())
    soften = blade.modifiers.new("Soften", "BEVEL")   # no real bat has knife-sharp edges
    soften.width, soften.segments = 0.004, 3
    blade.parent = parent


def add_splice(parent: bpy.types.Object) -> None:
    """The V where the cane handle is glued into the blade. A plain bat shows it clearly."""
    top, depth, half = BLADE_LENGTH - 0.012, SPLICE_LENGTH, HANDLE_RADIUS * 1.25
    mesh = bmesh.new()
    front = [mesh.verts.new(corner) for corner in
             ((-half, -0.0006, top), (half, -0.0006, top), (0, -0.0006, top - depth))]
    mesh.faces.new(front)
    shape = bpy.data.meshes.new("Splice")
    mesh.to_mesh(shape)
    mesh.free()
    splice = bpy.data.objects.new("Splice", shape)
    bpy.context.collection.objects.link(splice)
    splice.data.materials.append(studio.material("Cane", CANE, roughness=0.5))
    splice.parent = parent


def add_handle(parent: bpy.types.Object) -> None:
    """A round handle wrapped in rubber, with the ridges of a grip and a rounded cap."""
    middle = BLADE_LENGTH - 0.02 + HANDLE_LENGTH / 2
    bpy.ops.mesh.primitive_cylinder_add(radius=HANDLE_RADIUS, depth=HANDLE_LENGTH, vertices=48,
                                        location=(0, 0.009, middle))
    handle = bpy.context.object
    bpy.ops.object.shade_smooth()
    rubber = studio.material("Grip", GRIP, roughness=0.75)
    nodes, links = rubber.node_tree.nodes, rubber.node_tree.links
    rings = nodes.new("ShaderNodeTexWave")           # the ridges that run round a grip
    rings.bands_direction = "Z"
    rings.inputs["Scale"].default_value = 26
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.6
    links.new(rings.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], nodes["Principled BSDF"].inputs["Normal"])
    handle.data.materials.append(rubber)
    handle.parent = parent

    bpy.ops.mesh.primitive_uv_sphere_add(radius=HANDLE_RADIUS * 1.12, segments=32, ring_count=16,
                                         location=(0, 0.009, middle + HANDLE_LENGTH / 2))
    cap = bpy.context.object
    cap.scale.z = 0.55
    bpy.ops.object.shade_smooth()
    cap.data.materials.append(rubber)
    cap.parent = parent


def build_bat() -> float:
    """Stand the bat on its toe, turned a little. Returns its full height."""
    bat = bpy.data.objects.new("Bat", None)
    bpy.context.collection.objects.link(bat)
    add_blade(bat)
    add_splice(bat)
    add_handle(bat)
    bat.rotation_euler = (0, 0, TURN)
    return BLADE_LENGTH - 0.02 + HANDLE_LENGTH + HANDLE_RADIUS


def main() -> None:
    scene = studio.start_empty_scene(WIDTH, HEIGHT, SAMPLES)
    height = build_bat()
    middle = (0, 0, height / 2)
    studio.add_camera(scene, shows=height * 1.03, looks_at=middle)
    # The ball's lights sit metres away; the bat is a tenth the size, so it needs far less light.
    studio.add_lights(scene, around=middle, brightness=0.9)
    with tempfile.TemporaryDirectory() as folder:
        file = studio.render_png(scene, Path(folder) / "bat.png")
        if "--keep-frames" in sys.argv:
            studio.CHECK_FOLDER.mkdir(exist_ok=True)
            (studio.CHECK_FOLDER / "bat.png").write_bytes(file.read_bytes())
        studio.save_webp(scene, bpy.data.images.load(str(file)), "bat.webp")


main()
