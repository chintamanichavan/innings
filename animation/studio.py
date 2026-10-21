"""What every picture we render shares: an empty scene, the graphics card, plain materials,
the same three lights, a camera with no perspective, and saving with a clear background.

ball.py and bat.py each build one object and call these.
"""
from pathlib import Path

import bpy
from mathutils import Vector

PUBLIC = Path(__file__).resolve().parents[1] / "frontend" / "public" / "intro"
CHECK_FOLDER = Path(__file__).resolve().parent / "check"   # single frames saved to look at
WEBP_QUALITY = 90


def start_empty_scene(width: int, height: int, samples: int) -> bpy.types.Scene:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples                # light rays per pixel: more is cleaner and slower
    scene.cycles.use_denoising = True
    scene.render.film_transparent = True          # nothing behind the object
    scene.render.resolution_x, scene.render.resolution_y = width, height
    scene.render.resolution_percentage = 100
    scene.view_settings.view_transform = "Standard"   # keeps colours as vivid as we chose them
    _use_graphics_card(scene)
    return scene


def _use_graphics_card(scene: bpy.types.Scene) -> None:
    """Render on the graphics card if there is one; otherwise the processor does it."""
    settings = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA"):
        try:
            settings.compute_device_type = kind
        except TypeError:
            continue
        settings.get_devices()
        if any(device.type == kind for device in settings.devices):
            for device in settings.devices:
                device.use = device.type == kind
            scene.cycles.device = "GPU"
            return


def material(name: str, colour: tuple, roughness: float, grain: float = 0.0,
             lacquer: float = 0.0) -> bpy.types.Material:
    """A surface of one colour. `grain` adds fine bumps; `lacquer` adds a clear shiny coat."""
    made = bpy.data.materials.new(name)
    made.use_nodes = True
    nodes, links = made.node_tree.nodes, made.node_tree.links
    surface = nodes["Principled BSDF"]
    surface.inputs["Base Color"].default_value = (*colour, 1)
    surface.inputs["Roughness"].default_value = roughness
    surface.inputs["Coat Weight"].default_value = lacquer
    surface.inputs["Coat Roughness"].default_value = 0.2
    if grain:
        noise = nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 90
        bump = nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = grain
        links.new(noise.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], surface.inputs["Normal"])
    return made


def add_camera(scene: bpy.types.Scene, shows: float, looks_at: tuple = (0, 0, 0)) -> None:
    """A camera in front of the object, with no perspective. `shows` is how many units of the
    scene fit along the picture's longer side."""
    camera = bpy.data.objects.new("Camera", bpy.data.cameras.new("Camera"))
    scene.collection.objects.link(camera)
    camera.location = (looks_at[0], looks_at[1] - 6, looks_at[2])
    camera.rotation_euler = (1.5707963, 0, 0)     # a quarter turn: looking level, straight ahead
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = shows
    scene.camera = camera


def add_lights(scene: bpy.types.Scene, around: tuple = (0, 0, 0), brightness: float = 1.0) -> None:
    """The same three lights for every object, so they look as if they share one room."""
    centre = Vector(around)

    def lamp(name: str, offset: tuple, power: float, size: float) -> None:
        light = bpy.data.objects.new(name, bpy.data.lights.new(name, "AREA"))
        scene.collection.objects.link(light)
        light.location = centre + Vector(offset)
        light.data.energy = power * brightness
        light.data.size = size
        light.rotation_euler = (-Vector(offset)).to_track_quat("-Z", "Y").to_euler()

    lamp("Key", (-3.5, -4.5, 4.5), power=420, size=4)    # the main light, from upper left
    lamp("Fill", (4.5, -3.5, -1.5), power=70, size=5)    # lifts the shadow side
    lamp("Rim", (2.5, 4.5, 3.5), power=380, size=3)      # a bright edge from behind

    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    background = world.node_tree.nodes["Background"]
    background.inputs["Color"].default_value = (0.62, 0.62, 0.66, 1)
    background.inputs["Strength"].default_value = 0.22
    scene.world = world


def render_png(scene: bpy.types.Scene, file: Path) -> Path:
    """Render the current frame to a PNG with a clear background."""
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.filepath = str(file)
    bpy.ops.render.render(write_still=True)
    return file


def save_webp(scene: bpy.types.Scene, image: bpy.types.Image, name: str) -> Path:
    """Save a picture into the website's public folder, small enough to load at once."""
    PUBLIC.mkdir(parents=True, exist_ok=True)
    output = PUBLIC / name
    scene.render.image_settings.file_format = "WEBP"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.image_settings.quality = WEBP_QUALITY
    image.save_render(str(output), scene=scene)
    print(f"wrote {output} ({output.stat().st_size // 1024} kB)")
    return output
