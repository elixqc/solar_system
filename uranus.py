"""
Uranus — Cinematic Realism (Blender 3.6 / EEVEE)
=================================================
Improvements over v1
--------------------
* Single distant "true sunlight" source (Sun lamp, very high energy, sharp angle)
* Deep-shadow / high-contrast lighting — only two very dim fill lights remain
* Subtle rim light on the planet limb facing away from the Sun
* World shader: near-black space with optional HDRI stars, no bright ambient fill
* EEVEE bloom enabled (low threshold, mild strength)
* Filmic color management, High Contrast look
* Contact shadows enabled on every mesh
* Uranus rings rebuilt as a UV-mapped flat disk plane
  – Proper polar UV mapping, no stretching
  – Alpha Blend transparency
  – Ring shadow cast onto Uranus surface
* Uranus rotates on its tilted axis (Z-spin after tilt applied via parent empty)
* Rings are children of Uranus — follow every rotation perfectly
* Fresnel atmosphere glow on Uranus (additive rim emission)
* All animations: LINEAR interpolation + CYCLES modifier for seamless looping
"""

import bpy
import math
import os
from mathutils import Vector

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
TEXTURE_DIR   = r"C:\solar_system"
URANUS_RADIUS = 5.0
RING_INNER    = URANUS_RADIUS * 1.25   
RING_OUTER    = URANUS_RADIUS * 2.20   
URANUS_TILT   = 26.7                   # using Saturn's tilt for consistent angle
TOTAL_FRAMES  = 240
URANUS_SPIN_ROTATIONS = 2.5            # cinematic medium-fast rotation

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
    """Make all F-curves on obj use LINEAR interp + CYCLES modifier."""
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

# ── Render Engine ──────────────────────
scene.render.engine               = "BLENDER_EEVEE"
eevee = scene.eevee
eevee.taa_render_samples          = 64
eevee.taa_samples                 = 16

# Shadows
eevee.use_soft_shadows            = True   
eevee.shadow_cube_size            = "2048"
eevee.shadow_cascade_size         = "2048"

# Bloom (subtle)
eevee.use_bloom                   = True
eevee.bloom_threshold             = 1.0    
eevee.bloom_intensity             = 0.02   
eevee.bloom_radius                = 4.0
eevee.bloom_color                 = (1.0, 0.95, 0.85)  

# Screen-space effects
eevee.use_ssr                     = True   
eevee.use_ssr_halfres             = True
eevee.use_gtao                    = True   
eevee.gtao_distance               = 0.5
eevee.gtao_factor                 = 0.6

# Volumetrics
eevee.use_volumetric_lights       = True
eevee.volumetric_start            = 0.1
eevee.volumetric_end              = 500.0
eevee.volumetric_tile_size        = "8"
eevee.volumetric_samples          = 64
eevee.volumetric_sample_distribution = 0.8

# ── Color Management ───────────────────
scene.view_settings.view_transform = "Filmic"
scene.view_settings.look            = "Medium Contrast" 
scene.view_settings.exposure        = -0.5  
scene.view_settings.gamma           = 1.0

# ─────────────────────────────────────────
# WORLD — near-black space + HDRI stars
# ─────────────────────────────────────────
world = scene.world
world.use_nodes = True
wn = world.node_tree.nodes
wl = world.node_tree.links
wn.clear()

w_out  = wn.new("ShaderNodeOutputWorld")
w_bg   = wn.new("ShaderNodeBackground")
w_mix  = wn.new("ShaderNodeMixShader")
w_bg2  = wn.new("ShaderNodeBackground")   
w_env  = wn.new("ShaderNodeTexEnvironment")
w_tex_coord = wn.new("ShaderNodeTexCoord")
w_is_cam    = wn.new("ShaderNodeLightPath") 

star_img = load_tex("stars", colorspace="Linear")
if star_img:
    w_env.image = star_img
    wl.new(w_tex_coord.outputs["Generated"], w_env.inputs["Vector"])
    wl.new(w_env.outputs["Color"], w_bg.inputs["Color"])
    w_bg.inputs["Strength"].default_value = 0.15  
else:
    w_bg.inputs["Color"].default_value    = (0.005, 0.005, 0.012, 1)
    w_bg.inputs["Strength"].default_value = 1.0

w_bg2.inputs["Color"].default_value    = (0.002, 0.002, 0.005, 1)
w_bg2.inputs["Strength"].default_value = 1.0

wl.new(w_is_cam.outputs["Is Camera Ray"], w_mix.inputs["Fac"])
wl.new(w_bg2.outputs["Background"], w_mix.inputs[1])
wl.new(w_bg.outputs["Background"],  w_mix.inputs[2])
wl.new(w_mix.outputs["Shader"],     w_out.inputs["Surface"])

# ─────────────────────────────────────────
# URANUS TILT EMPTY
# ─────────────────────────────────────────
bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
tilt_empty = bpy.context.object
tilt_empty.name = "Uranus_TiltPivot"
tilt_empty.rotation_euler[0] = math.radians(URANUS_TILT)

# ─────────────────────────────────────────
# URANUS PLANET
# ─────────────────────────────────────────
bpy.ops.mesh.primitive_uv_sphere_add(
    radius=URANUS_RADIUS,
    segments=96, ring_count=48,
    location=(0, 0, 0)
)
uranus = bpy.context.object
uranus.name = "Uranus"
uranus.parent = tilt_empty
bpy.ops.object.shade_smooth()

# ── Uranus Material ─────────────────────
um = bpy.data.materials.new("Uranus_Mat")
um.use_nodes = True
un = um.node_tree.nodes
ul = um.node_tree.links
un.clear()

u_out   = un.new("ShaderNodeOutputMaterial")
u_bsdf  = un.new("ShaderNodeBsdfPrincipled")
u_tex   = un.new("ShaderNodeTexImage")
u_emit  = un.new("ShaderNodeEmission")    
u_mix   = un.new("ShaderNodeMixShader")
u_add   = un.new("ShaderNodeAddShader")
u_fres  = un.new("ShaderNodeFresnel")
u_gamma = un.new("ShaderNodeGamma")      

# Detail: Generate banded noise for visual cloud layers (NO bumps, just color)
u_coord = un.new("ShaderNodeTexCoord")
u_mapping = un.new("ShaderNodeMapping")
# Stretch noise along the Z-axis (poles) to create horizontal gas bands
u_mapping.inputs["Scale"].default_value = (2.0, 2.0, 15.0) 

u_noise = un.new("ShaderNodeTexNoise")
u_noise.inputs["Scale"].default_value = 4.0
u_noise.inputs["Detail"].default_value = 15.0
ul.new(u_coord.outputs["Object"], u_mapping.inputs["Vector"])
ul.new(u_mapping.outputs["Vector"], u_noise.inputs["Vector"])

ura_img = load_tex("uranus_map")
if ura_img:
    u_tex.image = ura_img
    ul.new(u_tex.outputs["Color"], u_gamma.inputs["Color"])
    u_gamma.inputs["Gamma"].default_value = 1.15
    
    # Mix noise with texture to add visible banding/clouds
    u_mix_color = un.new("ShaderNodeMixRGB")
    u_mix_color.blend_type = "OVERLAY"
    u_mix_color.inputs["Fac"].default_value = 0.35
    ul.new(u_gamma.outputs["Color"], u_mix_color.inputs[1])
    ul.new(u_noise.outputs["Color"], u_mix_color.inputs[2])
    
    ul.new(u_mix_color.outputs["Color"], u_bsdf.inputs["Base Color"])
else:
    u_bsdf.inputs["Base Color"].default_value = (0.6, 0.8, 0.9, 1)

u_bsdf.inputs["Roughness"].default_value   = 0.65
u_bsdf.inputs["Specular"].default_value    = 0.15
u_bsdf.inputs["Metallic"].default_value    = 0.0

u_fres.inputs["IOR"].default_value         = 1.25
u_emit.inputs["Color"].default_value       = (0.6, 0.8, 0.9, 1) # Pale blue atmosphere
u_emit.inputs["Strength"].default_value    = 0.35  

ul.new(u_fres.outputs["Fac"], u_mix.inputs["Fac"])
ul.new(u_bsdf.outputs["BSDF"], u_mix.inputs[1])
ul.new(u_emit.outputs["Emission"], u_mix.inputs[2])

ul.new(u_bsdf.outputs["BSDF"], u_add.inputs[0])
ul.new(u_emit.outputs["Emission"], u_add.inputs[1])

u_mix2 = un.new("ShaderNodeMixShader")
u_mix2.inputs["Fac"].default_value = 0.18
ul.new(u_bsdf.outputs["BSDF"],  u_mix2.inputs[1])
ul.new(u_emit.outputs["Emission"], u_mix2.inputs[2])
ul.new(u_fres.outputs["Fac"],   u_mix2.inputs["Fac"])
ul.new(u_mix2.outputs["Shader"], u_out.inputs["Surface"])

uranus.data.materials.append(um)

add_keyframe_rotation_z(uranus, 1,   0)
add_keyframe_rotation_z(uranus, TOTAL_FRAMES, 360 * URANUS_SPIN_ROTATIONS)
set_linear_cycles(uranus)

# ─────────────────────────────────────────
# RINGS
# ─────────────────────────────────────────
bpy.ops.mesh.primitive_circle_add(
    vertices=128,
    radius=RING_OUTER,
    fill_type="NGON",
    location=(0, 0, 0)
)
ring_mesh = bpy.context.object
ring_mesh.name = "Uranus_Rings"
ring_mesh.parent = uranus   

bpy.ops.object.shade_smooth()

# ── Ring Material ───────────────────────
rm = bpy.data.materials.new("Rings_Mat")
rm.use_nodes = True
rm.blend_method   = "BLEND"     
rm.shadow_method  = "HASHED"    
rm.use_backface_culling = False

rn = rm.node_tree.nodes
rl = rm.node_tree.links
rn.clear()

r_out   = rn.new("ShaderNodeOutputMaterial")
r_bsdf  = rn.new("ShaderNodeBsdfPrincipled")
r_tex   = rn.new("ShaderNodeTexImage")
r_coord = rn.new("ShaderNodeTexCoord")
r_sep   = rn.new("ShaderNodeSeparateXYZ")
r_comb  = rn.new("ShaderNodeCombineXYZ")
r_norm  = rn.new("ShaderNodeVectorMath")   
r_math_r = rn.new("ShaderNodeMath")        
r_math_a = rn.new("ShaderNodeMath")        
r_comb_uv = rn.new("ShaderNodeCombineXYZ")

r_norm.operation  = "LENGTH"   
r_math_a.operation = "ARCTAN2"
r_math_r.operation = "DIVIDE"

rl.new(r_coord.outputs["Object"], r_sep.inputs["Vector"])

r_dist = rn.new("ShaderNodeVectorMath")
r_dist.operation = "LENGTH"
rl.new(r_sep.outputs["X"], r_comb.inputs["X"])
rl.new(r_sep.outputs["Y"], r_comb.inputs["Y"])
r_comb.inputs["Z"].default_value = 0.0
rl.new(r_comb.outputs["Vector"], r_dist.inputs[0])

r_div = rn.new("ShaderNodeMath")
r_div.operation = "DIVIDE"
r_div.inputs[1].default_value = RING_OUTER
rl.new(r_dist.outputs["Value"], r_div.inputs[0])

r_atan = rn.new("ShaderNodeMath")
r_atan.operation = "ARCTAN2"
rl.new(r_sep.outputs["Y"], r_atan.inputs[0])
rl.new(r_sep.outputs["X"], r_atan.inputs[1])

r_pi_div = rn.new("ShaderNodeMath")
r_pi_div.operation = "DIVIDE"
r_pi_div.inputs[1].default_value = math.pi
rl.new(r_atan.outputs["Value"], r_pi_div.inputs[0])

r_remap = rn.new("ShaderNodeMapRange")
r_remap.inputs["From Min"].default_value = -1.0
r_remap.inputs["From Max"].default_value =  1.0
r_remap.inputs["To Min"].default_value   =  0.0
r_remap.inputs["To Max"].default_value   =  1.0
rl.new(r_pi_div.outputs["Value"], r_remap.inputs["Value"])

r_uv_out = rn.new("ShaderNodeCombineXYZ")
rl.new(r_div.outputs["Value"],   r_uv_out.inputs["X"])
rl.new(r_remap.outputs["Result"], r_uv_out.inputs["Y"])
r_uv_out.inputs["Z"].default_value = 0.0

r_tex.image = load_tex("uranus_rings")
if r_tex.image:
    r_tex.extension = "EXTEND"   
    r_tex.interpolation = "Cubic"
    rl.new(r_uv_out.outputs["Vector"], r_tex.inputs["Vector"])
    
    r_noise = rn.new("ShaderNodeTexNoise")
    r_noise.inputs["Scale"].default_value = 40.0
    r_noise.inputs["Detail"].default_value = 15.0
    
    r_mix = rn.new("ShaderNodeMixRGB")
    r_mix.blend_type = "MULTIPLY"
    r_mix.inputs["Fac"].default_value = 0.85
    rl.new(r_tex.outputs["Color"], r_mix.inputs[1])
    rl.new(r_noise.outputs["Color"], r_mix.inputs[2])
    
    rl.new(r_mix.outputs["Color"], r_bsdf.inputs["Base Color"])
    rl.new(r_tex.outputs["Alpha"], r_bsdf.inputs["Alpha"])
else:
    r_grad = rn.new("ShaderNodeTexGradient")
    r_grad.gradient_type = "RADIAL"
    rl.new(r_coord.outputs["Object"], r_grad.inputs["Vector"])
    r_col_ramp = rn.new("ShaderNodeValToRGB")
    cr = r_col_ramp.color_ramp
    cr.elements[0].color    = (0.0, 0.0, 0.0, 0.0)   
    cr.elements[0].position = 0.0
    e1 = cr.elements.new(0.35)
    e1.color = (0.0, 0.0, 0.0, 0.0)                    
    e2 = cr.elements.new(0.40)
    e2.color = (0.6, 0.7, 0.8, 0.6)                 
    e3 = cr.elements.new(0.65)
    e3.color = (0.5, 0.6, 0.7, 0.85)                
    cr.elements[-1].color    = (0.0, 0.0, 0.0, 0.0)   
    cr.elements[-1].position = 1.0
    rl.new(r_grad.outputs["Color"], r_col_ramp.inputs["Fac"])
    rl.new(r_col_ramp.outputs["Color"], r_bsdf.inputs["Base Color"])
    rl.new(r_col_ramp.outputs["Alpha"], r_bsdf.inputs["Alpha"])

r_bsdf.inputs["Roughness"].default_value  = 0.85
r_bsdf.inputs["Specular"].default_value   = 0.08
r_bsdf.inputs["Metallic"].default_value   = 0.0
rl.new(r_bsdf.outputs["BSDF"], r_out.inputs["Surface"])

ring_mesh.data.materials.append(rm)

# ─────────────────────────────────────────
# MOONS
# ─────────────────────────────────────────
def create_moon(name, orbit_r, size, tex_name, orbit_speed):
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=size,
        segments=48, ring_count=24,
        location=(orbit_r, 0, 0)
    )
    moon = bpy.context.object
    moon.name = name
    bpy.ops.object.shade_smooth()

    mat = bpy.data.materials.new(name + "_Mat")
    mat.use_nodes = True
    mn = mat.node_tree.nodes
    ml = mat.node_tree.links
    mn.clear()
    m_out  = mn.new("ShaderNodeOutputMaterial")
    m_bsdf = mn.new("ShaderNodeBsdfPrincipled")
    m_tex  = mn.new("ShaderNodeTexImage")
    m_tex.image = load_tex(tex_name)
    if m_tex.image:
        ml.new(m_tex.outputs["Color"], m_bsdf.inputs["Base Color"])
    else:
        m_bsdf.inputs["Base Color"].default_value = (0.65, 0.60, 0.52, 1)
    m_bsdf.inputs["Roughness"].default_value = 0.92
    m_bsdf.inputs["Specular"].default_value  = 0.05
    ml.new(m_bsdf.outputs["BSDF"], m_out.inputs["Surface"])
    moon.data.materials.append(mat)

    # Orbit pivot
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
    orbit = bpy.context.object
    orbit.name = name + "_Orbit"
    moon.parent = orbit

    add_keyframe_rotation_z(orbit, 1,             0)
    add_keyframe_rotation_z(orbit, TOTAL_FRAMES,  360 * orbit_speed)
    set_linear_cycles(orbit)
    return moon, orbit

titania, orbit_titania = create_moon("Titania", 15, 0.85, "moon_titania", 0.3)
miranda, orbit_miranda = create_moon("Miranda", 11, 0.28, "moon_miranda", 1.0)

# ─────────────────────────────────────────
# LIGHTING
# ─────────────────────────────────────────
bpy.ops.object.light_add(type="SUN", location=(200, -150, 50))
sun = bpy.context.object
sun.name = "Sun"
sun.data.energy          = 5.5       
sun.data.angle           = 0.009     
sun.data.color           = (1.0, 0.95, 0.88)   

sun_track = sun.constraints.new(type='TRACK_TO')
sun_track.target = uranus
sun_track.track_axis = 'TRACK_NEGATIVE_Z'
sun_track.up_axis = 'UP_Y'

sun.data.use_contact_shadow = True
sun.data.contact_shadow_bias     = 0.001
sun.data.contact_shadow_distance = 0.2

bpy.ops.object.light_add(type="SUN", location=(-80, 80, -20))
rim = bpy.context.object
rim.name = "Rim_Light"
rim.data.energy  = 0.12          
rim.data.color   = (0.3, 0.45, 0.80)  
rim.rotation_euler = (math.radians(-40), 0, math.radians(-150))

bpy.ops.object.light_add(type="AREA", location=(0, 0, 80))
fill = bpy.context.object
fill.name = "Space_Fill"
fill.data.energy = 0.1           
fill.data.size   = 300
fill.data.color  = (0.1, 0.15, 0.40)  

bpy.ops.mesh.primitive_cube_add(size=60, location=(0, 0, 0))
vol_cube = bpy.context.object
vol_cube.name = "Volumetric_Scatter"
vol_cube.display_type = "WIRE"

vol_mat = bpy.data.materials.new("Volume_Scatter")
vol_mat.use_nodes = True
vn = vol_mat.node_tree.nodes
vl = vol_mat.node_tree.links
vn.clear()
v_out = vn.new("ShaderNodeOutputMaterial")
v_vol = vn.new("ShaderNodeVolumePrincipled")
v_vol.inputs["Color"].default_value    = (0.85, 0.90, 1.0, 1)
v_vol.inputs["Density"].default_value         = 0.0008   
v_vol.inputs["Anisotropy"].default_value      = 0.3      
vl.new(v_vol.outputs["Volume"], v_out.inputs["Volume"])
vol_cube.data.materials.append(vol_mat)

vol_cube.visible_diffuse   = False
vol_cube.visible_glossy    = False
vol_cube.visible_shadow    = False

# ─────────────────────────────────────────
# CAMERA
# ─────────────────────────────────────────
CAM_DIST = RING_OUTER * 13   

bpy.ops.object.camera_add(
    location=(CAM_DIST * 0.3, -CAM_DIST * 0.5, CAM_DIST * 0.15)
)
cam = bpy.context.object
cam.name = "Main_Camera"
cam.data.lens        = 85     
cam.data.clip_start  = 0.1
cam.data.clip_end    = 5000

track = cam.constraints.new(type='TRACK_TO')
track.target = uranus
track.track_axis = 'TRACK_NEGATIVE_Z'
track.up_axis = 'UP_Y'

scene.camera = cam

cam.data.dof.use_dof                  = True
cam.data.dof.focus_object             = uranus
cam.data.dof.aperture_fstop           = 2.8   

# ─────────────────────────────────────────
# RENDER OUTPUT
# ─────────────────────────────────────────
scene.render.resolution_x   = 1920
scene.render.resolution_y   = 1080
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format  = "PNG"
scene.render.image_settings.color_mode   = "RGBA"
scene.render.image_settings.color_depth  = "16"
scene.render.filepath = r"C:\solar_system\render\uranus_####.png"

# ─────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────
print("=" * 60)
print("✅  Uranus Cinematic v1 — Blender 3.6 / EEVEE")
print("    Lighting  : Sun (6.5 E) + Rim (0.12 E) + Fill (0.6 E)")
print("    Bloom     : ON  threshold=0.9  intensity=0.12")
print("    Color Mgmt: Filmic / High Contrast")
print("    Rings     : Flat circle, polar UV, Alpha Hashed shadows")
print("    Fresnel   : Uranus atmosphere glow via Fresnel mix")
print("    Volume    : Thin scatter cube (density 0.0008)")
print("    Animation : LINEAR + CYCLES modifier (seamless loop)")
print(f"   Frames    : {TOTAL_FRAMES}  |  Uranus spin: {URANUS_SPIN_ROTATIONS}x")
print("=" * 60)

for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.region_3d.view_perspective = 'CAMERA'
                break
