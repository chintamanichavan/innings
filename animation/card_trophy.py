"""A final: the trophy under a spotlight, with paper falling around it.

The cup is not any real trophy. It is a plain cup turned on a lathe: a profile spun around
its axis.

    blender -b -P animation/card_trophy.py      # writes frontend/public/cards/trophy.webp
"""
import math
import random
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stage import add, bloom, camera, glowing, grey, night_sky, save, spot, start  # noqa: E402

# The cup's outline, as (distance from the axis, height) in metres, from the foot to the rim.
PROFILE = [(0.001, 0), (0.30, 0), (0.30, 0.12), (0.24, 0.14), (0.22, 0.26), (0.08, 0.32),
           (0.05, 0.50), (0.09, 0.55), (0.05, 0.60), (0.07, 0.66), (0.20, 0.76), (0.29, 0.93),
           (0.31, 1.08), (0.33, 1.12)]
PAPER = 220


def metal(name: str, shade: float, roughness: float) -> bpy.types.Material:
    made = grey(name, shade, roughness)
    made.node_tree.nodes["Principled BSDF"].inputs["Metallic"].default_value = 1.0
    return made


def add_cup(shine) -> bpy.types.Object:
    """Spin the outline once around the upright axis, then give the wall a thickness."""
    mesh = bpy.data.meshes.new("Outline")
    mesh.from_pydata([(r, 0, z) for r, z in PROFILE], [(i, i + 1) for i in range(len(PROFILE) - 1)], [])
    cup = bpy.data.objects.new("Cup", mesh)
    bpy.context.scene.collection.objects.link(cup)
    lathe = cup.modifiers.new("Lathe", "SCREW")
    lathe.steps = lathe.render_steps = 128
    lathe.use_smooth_shade = True
    wall = cup.modifiers.new("Wall", "SOLIDIFY")
    wall.thickness = 0.012
    cup.data.materials.append(shine)
    return cup


def add_handles(shine) -> None:
    for side in (-1, 1):
        handle = add(bpy.ops.mesh.primitive_torus_add, "Handle", shine, major_radius=0.13,
                     minor_radius=0.018, location=(side * 0.36, 0, 0.92), rotation=(math.pi / 2, 0, 0))
        bpy.ops.object.shade_smooth()
        handle.scale = (0.8, 1, 1.25)


def add_paper() -> None:
    """Scraps of paper in the air, some lit, some in shadow, most out of focus."""
    random.seed(7)
    shades = [grey(f"Paper {shade}", shade, 0.5) for shade in (0.35, 0.6, 0.85)]
    for _ in range(PAPER):
        add(bpy.ops.mesh.primitive_plane_add, "Paper", random.choice(shades), size=0.035,
            location=(random.uniform(-2.6, 2.6), random.uniform(-1.2, 2.5), random.uniform(0.1, 2.0)),
            rotation=tuple(random.uniform(0, math.tau) for _ in range(3)))


def main() -> None:
    scene = start()
    night_sky(scene, glow=0.006)
    add(bpy.ops.mesh.primitive_plane_add, "Floor", grey("Floor", 0.05, 0.25), size=40)
    add(bpy.ops.mesh.primitive_cylinder_add, "Plinth", grey("Plinth", 0.08, 0.4), radius=0.5, depth=0.5,
        location=(0, 0, 0.25), vertices=96)
    cup = add_cup(metal("Silver", 0.85, 0.18))
    cup.location = (0, 0, 0.5)
    add_handles(metal("Silver handles", 0.85, 0.18))
    for handle in [thing for thing in scene.objects if thing.name.startswith("Handle")]:
        handle.location.z += 0.5
    add_paper()
    # Soft panels out of the picture. Polished metal shows what it reflects, so it needs these.
    panel = glowing("Softbox", 6)
    for x, turn in ((-2.6, -1.0), (2.6, 1.0)):
        add(bpy.ops.mesh.primitive_plane_add, "Softbox", panel, size=1, location=(x, -2.2, 1.4),
            rotation=(math.pi / 2, 0, turn), scale=(1.6, 2.4, 1))
    spot(scene, "Above", at=(0, -0.5, 5), looks_at=(0, 0, 1.1), power=1800, cone=28, soft=0.6)
    spot(scene, "Left", at=(-3, -2, 2), looks_at=(0, 0, 1.1), power=500, cone=30, soft=0.5)
    spot(scene, "Behind", at=(1.5, 3, 2.2), looks_at=(0, 0, 1.2), power=900, cone=30, soft=0.5)
    camera(scene, at=(0.6, -5.4, 1.2), looks_at=(-0.6, 0, 1.05), lens=50, focus=5.45, blur=2.0)
    bloom(scene, size=6, threshold=1.0)
    save(scene, "trophy")


main()
