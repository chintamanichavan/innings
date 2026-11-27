"""A six: the ball climbing into the night, under the floodlights, with the trail of its flight.

    blender -b -P animation/card_six.py      # writes frontend/public/cards/six.webp
"""
import random
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ball import build_ball  # noqa: E402
from stage import add, bloom, camera, glowing, night_sky, save, spot, start  # noqa: E402

LIGHTS_IN_THE_DISTANCE = 70
# The ball's path, from low on the left to high on the right, as (x, y, z) in metres.
FLIGHT = [(-9, 2, -4.2), (-5.5, 1.4, -0.9), (-2, 0.8, 0.6), (1, 0.3, 1.0), (2.3, 0, 0.9)]


def add_trail() -> None:
    """A thin streak of light behind the ball, fading to nothing where it began."""
    curve = bpy.data.curves.new("Trail", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = 0.022
    curve.use_fill_caps = True
    path = curve.splines.new("NURBS")
    path.points.add(len(FLIGHT) - 1)
    for point, (x, y, z) in zip(path.points, FLIGHT, strict=True):
        point.co = (x, y, z, 1)
    path.use_endpoint_u = True
    path.order_u = 4
    for index, point in enumerate(path.points):
        point.radius = index / (len(FLIGHT) - 1)       # thin at the start, full width at the ball
    trail = bpy.data.objects.new("Trail", curve)
    bpy.context.scene.collection.objects.link(trail)
    curve.materials.append(glowing("Streak", 1.2))


def add_far_lights() -> None:
    """Floodlights and stand lights far behind, so out of focus they become soft discs."""
    random.seed(4)
    lamp = glowing("Lamp", 25)
    for _ in range(LIGHTS_IN_THE_DISTANCE):        # the stands: a low band of small lights
        add(bpy.ops.mesh.primitive_uv_sphere_add, "Lamp", lamp, radius=random.uniform(0.12, 0.3),
            location=(random.uniform(-50, 50), random.uniform(60, 80), random.uniform(-9, -2)))
    for x in (-34, 30):                            # two floodlight banks, high up
        for row in range(3):
            for column in range(4):
                add(bpy.ops.mesh.primitive_uv_sphere_add, "Flood", lamp, radius=0.35,
                    location=(x + column * 1.2, 70, 9 + row * 1.2))


def main() -> None:
    scene = start()
    night_sky(scene, glow=0.01)
    add_trail()
    add_far_lights()
    ball = build_ball()
    ball.location = FLIGHT[-1]
    ball.scale = (0.2, 0.2, 0.2)        # larger than life: the ball is the hero of this picture
    ball.rotation_euler = (1.25, 0.5, 0.25)   # turned so the seam faces the light
    spot(scene, "Key", at=(-3, -5, 4), looks_at=FLIGHT[-1], power=2500, cone=25, soft=0.4)
    spot(scene, "Rim", at=(5, 6, 4), looks_at=FLIGHT[-1], power=2500, cone=25, soft=0.4)
    camera(scene, at=(0.4, -7, 0.1), looks_at=(0.4, 0, 0.3), lens=45, focus=7.1, blur=1.2)
    bloom(scene, size=8, threshold=0.7)
    save(scene, "six")


main()
