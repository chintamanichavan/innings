"""What the story-card scenes share: a night scene, a real camera with depth of field,
floodlights, and saving a wide picture for the cards.

The scenes are rendered in shades of grey. The website lays each one over the two teams'
colours and lets the picture's light and shade show through, so one render suits every match.
"""
import math
import os
from pathlib import Path

import bpy
from mathutils import Vector
from studio import material, start_empty_scene

CARDS = Path(__file__).resolve().parents[1] / "frontend" / "public" / "cards"
WIDTH, HEIGHT = 1680, 720          # 21 by 9, the shape of the widest card
SAMPLES = 160
WEBP_QUALITY = 82
PREVIEW = bool(os.environ.get("PREVIEW"))   # PREVIEW=1: a quick, small, noisy look while working


def start(samples: int = SAMPLES, width: int = WIDTH, height: int = HEIGHT) -> bpy.types.Scene:
    if PREVIEW:
        samples, width, height = 24, width // 2, height // 2
    scene = start_empty_scene(width, height, samples)
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX"     # gentle on bright floodlights
    scene.view_settings.look = "AgX - Medium High Contrast"
    return scene


def night_sky(scene: bpy.types.Scene, glow: float = 0.015) -> None:
    world = bpy.data.worlds.new("Night")
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    background.inputs["Color"].default_value = (0.5, 0.52, 0.6, 1)
    background.inputs["Strength"].default_value = glow
    scene.world = world


def grey(name: str, shade: float, roughness: float = 0.6, grain: float = 0.0) -> bpy.types.Material:
    return material(name, (shade, shade, shade), roughness, grain)


def glowing(name: str, strength: float) -> bpy.types.Material:
    """A surface that gives off light: a floodlight panel, a trail."""
    made = bpy.data.materials.new(name)
    made.use_nodes = True
    nodes = made.node_tree.nodes
    nodes.remove(nodes["Principled BSDF"])
    light = nodes.new("ShaderNodeEmission")
    light.inputs["Strength"].default_value = strength
    made.node_tree.links.new(light.outputs["Emission"], nodes["Material Output"].inputs["Surface"])
    return made


def add(primitive, name: str, made: bpy.types.Material, **where) -> bpy.types.Object:
    """Add one mesh from `bpy.ops.mesh`, name it and give it a material."""
    primitive(**where)
    thing = bpy.context.active_object
    thing.name = name
    thing.data.materials.append(made)
    return thing


def camera(scene: bpy.types.Scene, at: tuple, looks_at: tuple, lens: float, focus: float,
           blur: float) -> None:
    """A real camera: `lens` in millimetres, sharp at `focus` metres, `blur` is the aperture f-number."""
    made = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    scene.collection.objects.link(made)
    made.location = at
    made.rotation_euler = (Vector(looks_at) - Vector(at)).to_track_quat("-Z", "Y").to_euler()
    made.data.lens = lens
    made.data.dof.use_dof = True
    made.data.dof.focus_distance = focus
    made.data.dof.aperture_fstop = blur
    scene.camera = made


def spot(scene: bpy.types.Scene, name: str, at: tuple, looks_at: tuple, power: float,
         cone: float = 50, soft: float = 0.3) -> None:
    lamp = bpy.data.objects.new(name, bpy.data.lights.new(name, "SPOT"))
    scene.collection.objects.link(lamp)
    lamp.location = at
    lamp.rotation_euler = (Vector(looks_at) - Vector(at)).to_track_quat("-Z", "Y").to_euler()
    lamp.data.energy = power
    lamp.data.spot_size = math.radians(cone)
    lamp.data.spot_blend = soft
    lamp.data.shadow_soft_size = 0.4


def save(scene: bpy.types.Scene, name: str) -> Path:
    """Render and save as WebP into the website's public folder."""
    folder = CARDS.parent.parent.parent / "animation" / "check" if PREVIEW else CARDS
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / f"{name}.webp"
    scene.render.image_settings.file_format = "WEBP"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.image_settings.quality = WEBP_QUALITY
    scene.render.filepath = str(output)
    bpy.ops.render.render(write_still=True)
    print(f"wrote {output} ({output.stat().st_size // 1024} kB)")
    return output


def textured(name: str, dark: float, light: float, scale: float, roughness: float = 0.8,
             bump: float = 0.2) -> bpy.types.Material:
    """A grey that varies between two shades in soft patches, with fine bumps: grass, a worn pitch."""
    made = bpy.data.materials.new(name)
    made.use_nodes = True
    nodes, links = made.node_tree.nodes, made.node_tree.links
    surface = nodes["Principled BSDF"]
    surface.inputs["Roughness"].default_value = roughness
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 8
    shades = nodes.new("ShaderNodeValToRGB")
    shades.color_ramp.elements[0].color = (dark, dark, dark, 1)
    shades.color_ramp.elements[1].color = (light, light, light, 1)
    links.new(noise.outputs["Fac"], shades.inputs["Fac"])
    links.new(shades.outputs["Color"], surface.inputs["Base Color"])
    fine = nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = scale * 40
    bumps = nodes.new("ShaderNodeBump")
    bumps.inputs["Strength"].default_value = bump
    links.new(fine.outputs["Fac"], bumps.inputs["Height"])
    links.new(bumps.outputs["Normal"], surface.inputs["Normal"])
    return made


def crowd(name: str, scale: float = 260) -> bpy.types.Material:
    """Dark tiers of seats, speckled with tiny lights: a full ground at night."""
    made = bpy.data.materials.new(name)
    made.use_nodes = True
    nodes, links = made.node_tree.nodes, made.node_tree.links
    surface = nodes["Principled BSDF"]
    surface.inputs["Base Color"].default_value = (0.03, 0.03, 0.035, 1)
    surface.inputs["Roughness"].default_value = 0.9
    dots = nodes.new("ShaderNodeTexVoronoi")
    dots.inputs["Scale"].default_value = scale
    only_some = nodes.new("ShaderNodeMath")
    only_some.operation = "LESS_THAN"
    only_some.inputs[1].default_value = 0.12   # the share of seats that glint
    links.new(dots.outputs["Distance"], only_some.inputs[0])
    surface.inputs["Emission Color"].default_value = (1, 1, 1, 1)
    brightness = nodes.new("ShaderNodeMath")
    brightness.operation = "MULTIPLY"
    brightness.inputs[1].default_value = 2.5
    links.new(only_some.outputs["Value"], brightness.inputs[0])
    links.new(brightness.outputs["Value"], surface.inputs["Emission Strength"])
    return made


def bloom(scene: bpy.types.Scene, size: int = 7, threshold: float = 0.8) -> None:
    """Let the brightest lights spill a soft glow, as they do through a broadcast lens."""
    scene.use_nodes = True
    tree = scene.node_tree
    rendered, output = tree.nodes["Render Layers"], tree.nodes["Composite"]
    glow = tree.nodes.new("CompositorNodeGlare")
    glow.glare_type = "FOG_GLOW"
    glow.quality = "HIGH"
    glow.size = size
    glow.threshold = threshold
    tree.links.new(rendered.outputs["Image"], glow.inputs["Image"])
    tree.links.new(glow.outputs["Image"], output.inputs["Image"])
