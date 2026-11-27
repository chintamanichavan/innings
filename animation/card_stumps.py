"""Bowled: the stumps knocked back, the bails flying, the ball rolling away.

    blender -b -P animation/card_stumps.py      # writes frontend/public/cards/stumps.webp
"""
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ball import build_ball  # noqa: E402
from stage import add, bloom, camera, grey, night_sky, save, spot, start, textured  # noqa: E402

STUMP_HEIGHT = 0.71
STUMP_GAP = 0.114


def add_stump(wood, side: int, lean: tuple) -> None:
    """One stump, pivoting at its foot: `lean` is (forward, sideways) in degrees."""
    stump = add(bpy.ops.mesh.primitive_cylinder_add, "Stump", wood, radius=0.019, depth=STUMP_HEIGHT,
                location=(0, 0, STUMP_HEIGHT / 2), vertices=48)
    bpy.ops.object.shade_smooth()
    foot = bpy.data.objects.new("Foot", None)
    bpy.context.scene.collection.objects.link(foot)
    foot.location = (side * STUMP_GAP, 0, 0)
    stump.parent = foot
    stump.location = (0, 0, STUMP_HEIGHT / 2)
    foot.rotation_euler = (math.radians(lean[0]), math.radians(lean[1]), 0)


def add_bail(wood, at: tuple, turn: tuple) -> None:
    add(bpy.ops.mesh.primitive_cylinder_add, "Bail", wood, radius=0.009, depth=0.11, vertices=32,
        location=at, rotation=tuple(math.radians(angle) for angle in turn))
    bpy.ops.object.shade_smooth()


def main() -> None:
    scene = start()
    night_sky(scene, glow=0.004)
    add(bpy.ops.mesh.primitive_plane_add, "Pitch", textured("Pitch", 0.22, 0.42, scale=6, bump=0.6),
        size=30, location=(0, 0, 0))
    add(bpy.ops.mesh.primitive_cube_add, "Crease", grey("Chalk", 0.85, 0.7), size=1,
        location=(0, -1.22, 0.002), scale=(3.66, 0.05, 0.004))
    wood = grey("Wood", 0.8, 0.35)
    add_stump(wood, -1, lean=(6, -9))
    add_stump(wood, 0, lean=(24, -22))     # the middle stump, knocked back and over by the ball
    add_stump(wood, 1, lean=(9, 12))
    add_bail(wood, at=(-0.22, 0.05, 0.96), turn=(20, 70, 35))
    add_bail(wood, at=(0.24, 0.12, 0.84), turn=(-30, 120, -20))
    ball = build_ball()
    ball.location = (0.16, 0.45, 0.036)
    ball.scale = (0.036, 0.036, 0.036)     # the model has a radius of one; a real ball, 3.6 cm
    spot(scene, "Key", at=(-2.5, -3, 4), looks_at=(0, 0.1, 0.4), power=900, cone=35, soft=0.5)
    spot(scene, "Rim", at=(1.5, 4, 2.5), looks_at=(0, 0, 0.4), power=1400, cone=30, soft=0.5)
    camera(scene, at=(0.2, -3.6, 0.6), looks_at=(-0.55, 0.1, 0.45), lens=55, focus=3.75, blur=2.2)
    bloom(scene, size=6, threshold=1.2)
    save(scene, "stumps")


main()
