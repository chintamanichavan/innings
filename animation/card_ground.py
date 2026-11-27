"""The broadcast view: from high behind the bowler's stumps, down the pitch, under floodlights.

    blender -b -P animation/card_ground.py      # writes frontend/public/cards/ground.webp
"""
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stage import (  # noqa: E402
    add,
    bloom,
    camera,
    crowd,
    glowing,
    grey,
    night_sky,
    save,
    spot,
    start,
    textured,
)

PITCH_LENGTH = 20.12      # metres between the stumps
PITCH_WIDTH = 3.05
FIELD_RADIUS = 70
STUMP_HEIGHT = 0.71
STUMP_GAP = 0.114         # stump to stump, centre to centre: three of them fill 22.86 cm


def add_stumps(at_y: float, wood) -> None:
    for side in (-1, 0, 1):
        add(bpy.ops.mesh.primitive_cylinder_add, "Stump", wood, radius=0.019, depth=STUMP_HEIGHT,
            location=(side * STUMP_GAP, at_y, STUMP_HEIGHT / 2))
    for side in (-0.5, 0.5):
        add(bpy.ops.mesh.primitive_cylinder_add, "Bail", wood, radius=0.008, depth=0.11,
            location=(side * STUMP_GAP, at_y, STUMP_HEIGHT + 0.01), rotation=(0, math.pi / 2, 0))


def add_creases(at_y: float, chalk, facing: int) -> None:
    """The popping crease in front of the stumps and the two return creases."""
    add(bpy.ops.mesh.primitive_cube_add, "Crease", chalk, size=1,
        location=(0, at_y + facing * 1.22, 0.003), scale=(3.66, 0.05, 0.004))
    for side in (-1, 1):
        add(bpy.ops.mesh.primitive_cube_add, "Return", chalk, size=1,
            location=(side * 1.32, at_y + facing * 0.6, 0.003), scale=(0.05, 2.4, 0.004))


def add_floodlight(scene, angle: float, panels) -> None:
    """A tower at the edge of the ground with a bank of lamps that light the middle."""
    x, y = 104 * math.cos(angle), 104 * math.sin(angle)
    add(bpy.ops.mesh.primitive_cylinder_add, "Tower", grey("Steel", 0.08, 0.5), radius=0.7, depth=34,
        location=(x, y, 17))
    head = add(bpy.ops.mesh.primitive_cube_add, "Lamps", panels, size=1, location=(x, y, 36),
               scale=(9, 0.6, 5))
    head.rotation_euler = (math.radians(70), 0, angle + math.pi / 2)
    spot(scene, "Flood", (x * 0.9, y * 0.9, 48), (0, 0, 0), power=7e4, cone=75, soft=0.8)


def main() -> None:
    scene = start()
    night_sky(scene)
    grass = textured("Grass", 0.09, 0.2, scale=0.6, bump=0.15)
    add(bpy.ops.mesh.primitive_cylinder_add, "Field", grass, radius=FIELD_RADIUS, depth=0.1,
        location=(0, 0, -0.05), vertices=128)
    add(bpy.ops.mesh.primitive_cylinder_add, "Outfield", grass, radius=82, depth=0.1,
        location=(0, 0, -0.06), vertices=128)   # out to the foot of the stands
    # Mowing stripes: bands of lighter and darker grass across the ground.
    light_grass = textured("Stripe", 0.14, 0.28, scale=0.6, bump=0.15)
    for band in range(-6, 7, 2):
        add(bpy.ops.mesh.primitive_cube_add, "Stripe", light_grass, size=1,
            location=(0, band * 9, 0.002), scale=(2 * FIELD_RADIUS * 0.95, 9, 0.002))
    add(bpy.ops.mesh.primitive_cube_add, "Pitch", textured("Pitch", 0.3, 0.55, scale=1.5, bump=0.5), size=1,
        location=(0, 0, 0.004), scale=(PITCH_WIDTH, PITCH_LENGTH + 2.5, 0.006))
    chalk = grey("Chalk", 0.9, 0.7)
    wood = grey("Wood", 0.75, 0.45)
    for end in (-1, 1):
        add_stumps(end * PITCH_LENGTH / 2, wood)
        add_creases(end * PITCH_LENGTH / 2, chalk, facing=-end)
    # The stands: a dark wall of seats rising all round, beyond the boundary.
    stand = crowd("Stand")
    add(bpy.ops.mesh.primitive_cone_add, "Stand", stand, radius1=96, radius2=78, depth=15,
        location=(0, 0, 7.5), vertices=96, end_fill_type="NOTHING")
    panels = glowing("Floodlight", 400)
    for angle in (60, 120, 215, 325):     # two beyond the far end are in the picture
        add_floodlight(scene, math.radians(angle), panels)
    camera(scene, at=(0, -PITCH_LENGTH / 2 - 22, 9), looks_at=(0, 40, 8), lens=30, focus=32, blur=2.8)
    bloom(scene)
    save(scene, "ground")


main()
