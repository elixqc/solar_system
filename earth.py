import bpy
import math
import os

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
TEXTURE_DIR   = r"C:\solar_system"
EARTH_RADIUS  = 2.0
EARTH_TILT    = 23.5
TOTAL_FRAMES  = 240
EARTH_SPIN    = 1.0  # Rotations

# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def load_tex(name, colorspace="sRGB"):
    for ext in (".jpg", ".png", ".jpeg", ".tif"):
        path = os.path.join(TEXTURE_DIR, name + ext)
        if os.path.exists(path):
            img = bpy.data.images.load(path)
            img.colorspace_settings.name = colorspace
            return img
    print(f"[WARNING] texture not found: {name}")
    return None

def set_linear_cycles(obj):
    if not (obj.animation_data and obj.animation_data.action):
        return
    for fc in obj.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
        if not fc.modifiers:
            fc.modifiers.new("CYCLES")

def add_keyframe_rotation_z(obj, frame, angle_deg):
    obj.rotation_euler[2] = math.radians(angle_deg)
    obj.keyframe_insert("rotation_euler", frame=frame)

# ─────────────────────────────────────────
# SCENE SETUP
# ─────────────────────────────────────────
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)

scene = bpy.context.scene
scene.frame_start = 1
scene.frame_end   = TOTAL_FRAMES

scene.render.engine               = "BLENDER_EEVEE"
eevee = scene.eevee
eevee.taa_render_samples          = 64
eevee.taa_samples                 = 16
eevee.use_soft_shadows            = True   
eevee.shadow_cube_size            = "2048"
eevee.shadow_cascade_size         = "2048"
eevee.use_bloom                   = True
eevee.bloom_threshold             = 1.0    
eevee.bloom_intensity             = 0.02   
eevee.bloom_radius                = 4.0
eevee.use_ssr                     = True   
eevee.use_gtao                    = True   

scene.view_settings.view_transform = "Filmic"
scene.view_settings.look            = "Medium Contrast" 

# ─────────────────────────────────────────
# WORLD
# ─────────────────────────────────────────
world = scene.world
world.use_nodes = True
wn = world.node_tree.nodes
wl = world.node_tree.links
wn.clear()

w_out  = wn.new("ShaderNodeOutputWorld")
w_bg   = wn.new("ShaderNodeBackground")
w_env  = wn.new("ShaderNodeTexEnvironment")

star_img = load_tex("stars", colorspace="Linear")
if star_img:
    w_env.image = star_img
    wl.new(w_env.outputs["Color"], w_bg.inputs["Color"])
    w_bg.inputs["Strength"].default_value = 0.5  
else:
    w_bg.inputs["Color"].default_value    = (0.005, 0.005, 0.012, 1)

wl.new(w_bg.outputs["Background"], w_out.inputs["Surface"])

# ─────────────────────────────────────────
# SUN TRACK EMPTY (For Day/Night Masking)
# ─────────────────────────────────────────
bpy.ops.object.empty_add(type="PLAIN_AXES", location=(100, -100, 20))
sun_target = bpy.context.object
sun_target.name = "Sun_Target"

# ─────────────────────────────────────────
# EARTH TILT EMPTY
# ─────────────────────────────────────────
bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
tilt_empty = bpy.context.object
tilt_empty.name = "Earth_TiltPivot"
tilt_empty.rotation_euler[0] = math.radians(EARTH_TILT)

# ─────────────────────────────────────────
# EARTH PLANET
# ─────────────────────────────────────────
bpy.ops.mesh.primitive_uv_sphere_add(
    radius=EARTH_RADIUS,
    segments=128, ring_count=64,
    location=(0, 0, 0)
)
earth = bpy.context.object
earth.name = "Earth"
earth.parent = tilt_empty
bpy.ops.object.shade_smooth()

# Material
em = bpy.data.materials.new("Earth_Mat")
em.use_nodes = True
en = em.node_tree.nodes
el = em.node_tree.links
en.clear()

e_out   = en.new("ShaderNodeOutputMaterial")
e_bsdf  = en.new("ShaderNodeBsdfPrincipled")

# Textures
t_day   = en.new("ShaderNodeTexImage")
t_night = en.new("ShaderNodeTexImage")
t_spec  = en.new("ShaderNodeTexImage")
t_bump  = en.new("ShaderNodeTexImage")

day_img   = load_tex("earth_daymap")
night_img = load_tex("earth_nightmap")
spec_img  = load_tex("earth_specular", "Non-Color")
bump_img  = load_tex("earth_bump", "Non-Color")

if day_img: t_day.image = day_img
if night_img: t_night.image = night_img
if spec_img: t_spec.image = spec_img
if bump_img: t_bump.image = bump_img

# Specular/Roughness
if spec_img:
    # Ocean is white in specular map, land is black.
    # High spec = low roughness.
    e_invert = en.new("ShaderNodeInvert")
    el.new(t_spec.outputs["Color"], e_invert.inputs["Color"])
    
    # Map range to make oceans shiny (roughness 0.1) and land rough (roughness 0.8)
    e_map = en.new("ShaderNodeMapRange")
    e_map.inputs["From Min"].default_value = 0.0
    e_map.inputs["From Max"].default_value = 1.0
    e_map.inputs["To Min"].default_value = 0.2
    e_map.inputs["To Max"].default_value = 0.85
    el.new(e_invert.outputs["Color"], e_map.inputs["Value"])
    el.new(e_map.outputs["Result"], e_bsdf.inputs["Roughness"])
    el.new(t_spec.outputs["Color"], e_bsdf.inputs["Specular"])
else:
    e_bsdf.inputs["Roughness"].default_value = 0.6

# Bump
if bump_img:
    e_bump_node = en.new("ShaderNodeBump")
    e_bump_node.inputs["Strength"].default_value = 0.3
    e_bump_node.inputs["Distance"].default_value = 0.1
    el.new(t_bump.outputs["Color"], e_bump_node.inputs["Height"])
    el.new(e_bump_node.outputs["Normal"], e_bsdf.inputs["Normal"])

# Day/Night Mix using Normal and Sun Vector
# In Eevee, Shader to RGB is better, but this math approach is robust for animation
tex_coord = en.new("ShaderNodeTexCoord")
sun_pos = en.new("ShaderNodeValue") 
# We'll calculate dot product of normal and light direction
geom = en.new("ShaderNodeNewGeometry")
vector_math = en.new("ShaderNodeVectorMath")
vector_math.operation = 'DOT_PRODUCT'

# Add a driver or just link a constant vector for the sun direction
# For simplicity, since sun is at (100, -100, 20), normalized dir is approx (0.7, -0.7, 0.14)
sun_dir = en.new("ShaderNodeCombineXYZ")
sun_dir.inputs[0].default_value = 1.0
sun_dir.inputs[1].default_value = -1.0
sun_dir.inputs[2].default_value = 0.2

norm_sun = en.new("ShaderNodeVectorMath")
norm_sun.operation = 'NORMALIZE'
el.new(sun_dir.outputs["Vector"], norm_sun.inputs[0])

el.new(geom.outputs["Normal"], vector_math.inputs[0])
el.new(norm_sun.outputs["Vector"], vector_math.inputs[1])

# ColorRamp to sharpen the transition
ramp = en.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].position = 0.0
ramp.color_ramp.elements[0].color = (1,1,1,1) # Night side
ramp.color_ramp.elements[1].position = 0.1
ramp.color_ramp.elements[1].color = (0,0,0,1) # Day side
el.new(vector_math.outputs["Value"], ramp.inputs["Fac"])

# Mix Day and Night
e_mix = en.new("ShaderNodeMixRGB")
el.new(ramp.outputs["Color"], e_mix.inputs["Fac"])
el.new(t_day.outputs["Color"], e_mix.inputs[1])

# Night needs emission
e_night_emit = en.new("ShaderNodeMixRGB")
e_night_emit.blend_type = 'MULTIPLY'
e_night_emit.inputs[0].default_value = 1.0
el.new(ramp.outputs["Color"], e_night_emit.inputs[1])
el.new(t_night.outputs["Color"], e_night_emit.inputs[2])

# Add city lights as emission
if day_img:
    el.new(t_day.outputs["Color"], e_bsdf.inputs["Base Color"])
if night_img:
    el.new(e_night_emit.outputs["Color"], e_bsdf.inputs["Emission"])
    e_bsdf.inputs["Emission Strength"].default_value = 2.0

el.new(e_bsdf.outputs["BSDF"], e_out.inputs["Surface"])
earth.data.materials.append(em)

# Animation
add_keyframe_rotation_z(earth, 1, 0)
add_keyframe_rotation_z(earth, TOTAL_FRAMES, 360 * EARTH_SPIN)
set_linear_cycles(earth)

# ─────────────────────────────────────────
# CLOUDS
# ─────────────────────────────────────────
bpy.ops.mesh.primitive_uv_sphere_add(
    radius=EARTH_RADIUS + 0.02,
    segments=128, ring_count=64,
    location=(0, 0, 0)
)
clouds = bpy.context.object
clouds.name = "Earth_Clouds"
clouds.parent = tilt_empty
bpy.ops.object.shade_smooth()

cm = bpy.data.materials.new("Clouds_Mat")
cm.use_nodes = True
cm.blend_method = 'BLEND'
cm.shadow_method = 'HASHED'

cn = cm.node_tree.nodes
cl = cm.node_tree.links
cn.clear()

c_out = cn.new("ShaderNodeOutputMaterial")
c_bsdf = cn.new("ShaderNodeBsdfPrincipled")
c_tex = cn.new("ShaderNodeTexImage")

cloud_img = load_tex("earth_clouds", "Non-Color")
if cloud_img:
    c_tex.image = cloud_img
    
    # Use a math node to reduce cloud opacity
    c_math = cn.new("ShaderNodeMath")
    c_math.operation = 'MULTIPLY'
    c_math.inputs[1].default_value = 0.45  # 45% opacity
    cl.new(c_tex.outputs["Color"], c_math.inputs[0])
    cl.new(c_math.outputs["Value"], c_bsdf.inputs["Alpha"])
    
    # Optional bump for clouds
    c_bump = cn.new("ShaderNodeBump")
    c_bump.inputs["Strength"].default_value = 0.1
    cl.new(c_tex.outputs["Color"], c_bump.inputs["Height"])
    cl.new(c_bump.outputs["Normal"], c_bsdf.inputs["Normal"])

c_bsdf.inputs["Base Color"].default_value = (1.0, 1.0, 1.0, 1.0)
c_bsdf.inputs["Roughness"].default_value = 0.9

cl.new(c_bsdf.outputs["BSDF"], c_out.inputs["Surface"])
clouds.data.materials.append(cm)

# Clouds rotate slightly faster
add_keyframe_rotation_z(clouds, 1, 0)
add_keyframe_rotation_z(clouds, TOTAL_FRAMES, 360 * (EARTH_SPIN + 0.05))
set_linear_cycles(clouds)



# ─────────────────────────────────────────
# MOON
# ─────────────────────────────────────────
MOON_RADIUS = EARTH_RADIUS * 0.27
MOON_DIST = EARTH_RADIUS * 12.0

bpy.ops.mesh.primitive_uv_sphere_add(
    radius=MOON_RADIUS,
    segments=64, ring_count=32,
    location=(MOON_DIST, 0, 0)
)
moon = bpy.context.object
moon.name = "Moon"
bpy.ops.object.shade_smooth()

mm = bpy.data.materials.new("Moon_Mat")
mm.use_nodes = True
mn = mm.node_tree.nodes
ml = mm.node_tree.links
mn.clear()

m_out = mn.new("ShaderNodeOutputMaterial")
m_bsdf = mn.new("ShaderNodeBsdfPrincipled")
m_tex = mn.new("ShaderNodeTexImage")
m_bump = mn.new("ShaderNodeTexImage")

moon_img = load_tex("moon")
mbump_img = load_tex("moon_bump", "Non-Color")

if moon_img:
    m_tex.image = moon_img
    ml.new(m_tex.outputs["Color"], m_bsdf.inputs["Base Color"])
else:
    m_bsdf.inputs["Base Color"].default_value = (0.5, 0.5, 0.5, 1)
    
if mbump_img:
    m_bump.image = mbump_img
    bump_node = mn.new("ShaderNodeBump")
    bump_node.inputs["Strength"].default_value = 0.5
    bump_node.inputs["Distance"].default_value = 0.1
    ml.new(m_bump.outputs["Color"], bump_node.inputs["Height"])
    ml.new(bump_node.outputs["Normal"], m_bsdf.inputs["Normal"])

m_bsdf.inputs["Roughness"].default_value = 0.95
m_bsdf.inputs["Specular"].default_value = 0.05

ml.new(m_bsdf.outputs["BSDF"], m_out.inputs["Surface"])
moon.data.materials.append(mm)

# Moon orbit empty
bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
moon_orbit = bpy.context.object
moon_orbit.name = "Moon_Orbit"
moon.parent = moon_orbit

# Moon orbit animation
add_keyframe_rotation_z(moon_orbit, 1, 0)
add_keyframe_rotation_z(moon_orbit, TOTAL_FRAMES, 360 * 0.5)
set_linear_cycles(moon_orbit)

# ─────────────────────────────────────────
# LIGHTING
# ─────────────────────────────────────────
# Realistic stark sunlight
bpy.ops.object.light_add(type="SUN", location=(150, -150, 20))
sun = bpy.context.object
sun.name = "Sun"
sun.data.energy = 8.0
sun.data.angle = 0.005 # Extremely sharp shadows like in real space
sun.data.color = (1.0, 0.98, 0.95)

sun_track = sun.constraints.new(type='TRACK_TO')
sun_track.target = earth
sun_track.track_axis = 'TRACK_NEGATIVE_Z'
sun_track.up_axis = 'UP_Y'

sun.data.use_contact_shadow = True
sun.data.contact_shadow_bias = 0.001
sun.data.contact_shadow_distance = 0.2

# Remove almost all ambient fill for high contrast cinematic look
bpy.ops.object.light_add(type="AREA", location=(-50, 50, -10))
fill = bpy.context.object
fill.name = "Space_Fill"
fill.data.energy = 0.01
fill.data.size = 200
fill.data.color = (0.05, 0.1, 0.2)

track_fill = fill.constraints.new(type='TRACK_TO')
track_fill.target = earth
track_fill.track_axis = 'TRACK_NEGATIVE_Z'
track_fill.up_axis = 'UP_Y'

# ─────────────────────────────────────────
# CAMERA
# ─────────────────────────────────────────
CAM_DIST = EARTH_RADIUS * 4.5

bpy.ops.object.camera_add(
    location=(-CAM_DIST * 0.26, -CAM_DIST * 0.96, 0),
    rotation=(math.radians(90), 0, math.radians(-15))
)
cam = bpy.context.object
cam.name = "Main_Camera"
cam.data.lens = 85
cam.data.clip_start = 0.1
cam.data.clip_end = 1000

track_cam = cam.constraints.new(type='TRACK_TO')
track_cam.target = earth
track_cam.track_axis = 'TRACK_NEGATIVE_Z'
track_cam.up_axis = 'UP_Y'

scene.camera = cam

cam.data.dof.use_dof = True
cam.data.dof.focus_object = earth
cam.data.dof.aperture_fstop = 2.8

# ─────────────────────────────────────────
# RENDER OUTPUT
# ─────────────────────────────────────────
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080
scene.render.filepath = r"C:\solar_system\render\earth_####.png"

print("✅ DONE: Earth — Cinematic EEVEE scene generated.")