import bpy
import math
import os
import random
from mathutils import Vector

# -----------------------------
# TEXTURE PATH
# -----------------------------
texture_dir = r"C:\solar_system"

def load_texture(name):
    for ext in [".jpg", ".png", ".jpeg"]:
        path = os.path.join(texture_dir, name + ext)
        if os.path.exists(path):
            return bpy.data.images.load(path)
    print("Missing texture:", name)
    return None

# -----------------------------
# CLEAN SCENE
# -----------------------------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# -----------------------------
# SETTINGS
# -----------------------------
EARTH_RADIUS = 2.0
PLUTO_RADIUS = EARTH_RADIUS * 0.186  # = 0.372
PLUTO_TILT = 57
CHARON_RADIUS = PLUTO_RADIUS * 0.51

scene = bpy.context.scene

# ✅ EEVEE (Venus-style)
scene.render.engine = 'BLENDER_EEVEE'
scene.eevee.taa_render_samples = 32
scene.eevee.taa_samples = 16
scene.eevee.use_soft_shadows = True

# -----------------------------
# PLUTO
# ✅ FIX: 128×64 segments = silky smooth, no disco-ball facets
# -----------------------------
bpy.ops.mesh.primitive_uv_sphere_add(
    radius=PLUTO_RADIUS,
    segments=128,
    ring_count=64,
    location=(0, 0, 0)
)
pluto = bpy.context.object
pluto.name = "Pluto"
pluto.rotation_euler[1] = math.radians(PLUTO_TILT)
bpy.ops.object.shade_smooth()

mat = bpy.data.materials.new("Pluto_Mat")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
nodes.clear()

out = nodes.new("ShaderNodeOutputMaterial")
bsdf = nodes.new("ShaderNodeBsdfPrincipled")
tex_color = nodes.new("ShaderNodeTexImage")
tex_bump = nodes.new("ShaderNodeTexImage")
bump = nodes.new("ShaderNodeBump")

tex_color.image = load_texture("pluto_map")
tex_bump.image = load_texture("pluto_bump")

if tex_color.image:
    tex_color.image.colorspace_settings.name = 'sRGB'
if tex_bump.image:
    tex_bump.image.colorspace_settings.name = 'Non-Color'

links.new(tex_color.outputs["Color"], bsdf.inputs["Base Color"])
links.new(tex_bump.outputs["Color"], bump.inputs["Height"])
links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

bump.inputs["Strength"].default_value = 0.6
bump.inputs["Distance"].default_value = 0.2

# ✅ Venus-style: matte + subtle emission mix
bsdf.inputs["Roughness"].default_value = 0.85
bsdf.inputs["Specular"].default_value = 0.1

emission = nodes.new("ShaderNodeEmission")
emission.inputs["Strength"].default_value = 0.1
links.new(tex_color.outputs["Color"], emission.inputs["Color"])

mix = nodes.new("ShaderNodeMixShader")
mix.inputs["Fac"].default_value = 0.15   # subtle — Pluto is very dark
links.new(bsdf.outputs["BSDF"], mix.inputs[1])
links.new(emission.outputs["Emission"], mix.inputs[2])
links.new(mix.outputs["Shader"], out.inputs["Surface"])

pluto.data.materials.append(mat)

# -----------------------------
# ATMOSPHERE (THIN)
# ✅ Smooth segments here too
# -----------------------------
bpy.ops.mesh.primitive_uv_sphere_add(
    radius=PLUTO_RADIUS + 0.01,
    segments=128,
    ring_count=64,
    location=(0, 0, 0)
)
atm = bpy.context.object
atm.name = "Pluto_Atmosphere"
atm.parent = pluto

mat_atm = bpy.data.materials.new("Atmosphere_Mat")
mat_atm.use_nodes = True
nodes = mat_atm.node_tree.nodes
links = mat_atm.node_tree.links
nodes.clear()

out = nodes.new("ShaderNodeOutputMaterial")
emission = nodes.new("ShaderNodeEmission")
transparent = nodes.new("ShaderNodeBsdfTransparent")
mix = nodes.new("ShaderNodeMixShader")
layer = nodes.new("ShaderNodeLayerWeight")

emission.inputs["Color"].default_value = (0.6, 0.7, 1, 1)
emission.inputs["Strength"].default_value = 0.4

links.new(layer.outputs["Facing"], mix.inputs["Fac"])
links.new(transparent.outputs["BSDF"], mix.inputs[1])
links.new(emission.outputs["Emission"], mix.inputs[2])
links.new(mix.outputs["Shader"], out.inputs["Surface"])

mat_atm.blend_method = 'BLEND'
atm.data.materials.append(mat_atm)

# -----------------------------
# BARYCENTER
# -----------------------------
bpy.ops.object.empty_add(location=(0, 0, 0))
bary = bpy.context.object
bary.name = "Pluto_Charon_Barycenter"

pluto.parent = bary
pluto.location = (-PLUTO_RADIUS * 0.5, 0, 0)

# -----------------------------
# CHARON
# ✅ Smooth segments
# -----------------------------
bpy.ops.mesh.primitive_uv_sphere_add(
    radius=CHARON_RADIUS,
    segments=128,
    ring_count=64,
    location=(PLUTO_RADIUS * 2.5, 0, 0)
)
charon = bpy.context.object
charon.name = "Charon"
charon.parent = bary
bpy.ops.object.shade_smooth()

mat_c = bpy.data.materials.new("Charon_Mat")
mat_c.use_nodes = True
nodes = mat_c.node_tree.nodes
links = mat_c.node_tree.links
nodes.clear()

out = nodes.new("ShaderNodeOutputMaterial")
bsdf = nodes.new("ShaderNodeBsdfPrincipled")
tex_c = nodes.new("ShaderNodeTexImage")
tex_c.image = load_texture("charon_map")

if tex_c.image:
    tex_c.image.colorspace_settings.name = 'sRGB'
    links.new(tex_c.outputs["Color"], bsdf.inputs["Base Color"])
else:
    bsdf.inputs["Base Color"].default_value = (0.5, 0.48, 0.45, 1)

bsdf.inputs["Roughness"].default_value = 0.95
links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
charon.data.materials.append(mat_c)

# -----------------------------
# SMALL MOONS
# ✅ Smooth segments + LINEAR keyframes
# -----------------------------
def small_moon(name, dist, size):
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=size,
        segments=64,
        ring_count=32,
        location=(dist, 0, 0)
    )
    moon = bpy.context.object
    moon.name = name
    bpy.ops.object.shade_smooth()

    mat = bpy.data.materials.new(name + "_Mat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.6, 0.6, 0.6, 1)
    bsdf.inputs["Roughness"].default_value = 1
    moon.data.materials.append(mat)

    bpy.ops.object.empty_add(location=(0, 0, 0))
    orbit = bpy.context.object
    orbit.name = name + "_Orbit"
    moon.parent = orbit

    orbit.rotation_euler[2] = 0
    orbit.keyframe_insert(data_path="rotation_euler", frame=1)
    orbit.rotation_euler[2] = math.radians(360 * random.uniform(0.5, 2))
    orbit.keyframe_insert(data_path="rotation_euler", frame=240)

    # ✅ LINEAR interpolation (Venus-style)
    if orbit.animation_data:
        for fcurve in orbit.animation_data.action.fcurves:
            for kp in fcurve.keyframe_points:
                kp.interpolation = 'LINEAR'

small_moon("Nix",      PLUTO_RADIUS * 12, PLUTO_RADIUS * 0.07)
small_moon("Hydra",    PLUTO_RADIUS * 15, PLUTO_RADIUS * 0.07)
small_moon("Kerberos", PLUTO_RADIUS * 18, PLUTO_RADIUS * 0.05)
small_moon("Styx",     PLUTO_RADIUS * 20, PLUTO_RADIUS * 0.05)

# -----------------------------
# ROTATION
# ✅ LINEAR keyframes on barycenter
# -----------------------------
scene.frame_start = 1
scene.frame_end = 240

bary.rotation_euler[2] = 0
bary.keyframe_insert(data_path="rotation_euler", frame=1)
bary.rotation_euler[2] = math.radians(360)
bary.keyframe_insert(data_path="rotation_euler", frame=240)

if bary.animation_data:
    for fcurve in bary.animation_data.action.fcurves:
        for kp in fcurve.keyframe_points:
            kp.interpolation = 'LINEAR'

# -----------------------------
# LIGHTING
# ✅ Cinematic: strong directional sun aiming at Pluto
# -----------------------------
bpy.ops.object.light_add(type='SUN', location=(10, -20, 5))
sun = bpy.context.object
sun.name = "Sun_Light"
sun.data.energy = 8
sun.data.angle = math.radians(0.5) # Sharp shadows in space

# Aim the sun directly at Pluto
track_sun = sun.constraints.new(type='TRACK_TO')
track_sun.target = pluto
track_sun.track_axis = 'TRACK_NEGATIVE_Z'
track_sun.up_axis = 'UP_Y'

# Just a very subtle fill so shadows aren't pitch black
bpy.ops.object.light_add(type='AREA', location=(-5, 5, -5))
fill = bpy.context.object
fill.name = "Fill"
fill.data.energy = 5
fill.data.size = 10

track_fill = fill.constraints.new(type='TRACK_TO')
track_fill.target = pluto
track_fill.track_axis = 'TRACK_NEGATIVE_Z'
track_fill.up_axis = 'UP_Y'

# -----------------------------
# STARS BACKGROUND
# -----------------------------
world = bpy.context.scene.world
world.use_nodes = True
nodes = world.node_tree.nodes
links = world.node_tree.links
nodes.clear()

bg = nodes.new("ShaderNodeBackground")
env = nodes.new("ShaderNodeTexEnvironment")
out_world = nodes.new("ShaderNodeOutputWorld")

env.image = load_texture("stars")
links.new(env.outputs["Color"], bg.inputs["Color"])
bg.inputs["Strength"].default_value = 1.0   # ✅ matched to Venus/Neptune
links.new(bg.outputs["Background"], out_world.inputs["Surface"])

# -----------------------------
# CAMERA — Focus Only on Pluto
# -----------------------------
CAM_DIST = PLUTO_RADIUS * 4.5  # Closer to focus only on Pluto

bpy.ops.object.camera_add(location=(pluto.location.x, pluto.location.y - CAM_DIST, CAM_DIST * 0.15))
cam = bpy.context.object
cam.name = "Main_Camera"
cam.data.lens = 85
cam.data.clip_start = 0.001
cam.data.clip_end = 1000

# Do NOT parent the camera so it stays stationary and Pluto rotates in front of it


# Track Pluto directly so it's always perfectly centered
track_cam = cam.constraints.new(type='TRACK_TO')
track_cam.target = pluto
track_cam.track_axis = 'TRACK_NEGATIVE_Z'
track_cam.up_axis = 'UP_Y'

scene.camera = cam

print("✅ DONE: Pluto — Eevee, focused on Pluto, Cinematic sun lighting, LINEAR anim, lens=85mm")