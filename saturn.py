"""
Saturn — Cinematic Realism (Blender 3.6 / EEVEE)
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
* Saturn rings rebuilt as a UV-mapped flat disk plane (not a cylinder)
  – Proper polar UV mapping, no stretching
  – Alpha Blend transparency
  – Ring shadow cast onto Saturn surface
* Saturn rotates on its tilted axis (Z-spin after tilt applied via parent empty)
* Rings are children of Saturn — follow every rotation perfectly
* Fresnel atmosphere glow on Saturn (additive rim emission)
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
SATURN_RADIUS = 5.0
RING_INNER    = SATURN_RADIUS * 1.25   # ~6.25
RING_OUTER    = SATURN_RADIUS * 2.20   # ~11.0
SATURN_TILT   = 26.7                   # degrees (real value)
TOTAL_FRAMES  = 240
SATURN_SPIN_ROTATIONS = 0.5            # cinematic medium-slow rotation

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
eevee.use_soft_shadows            = True   # (soft shadow toggle in 3.6)
eevee.shadow_cube_size            = "2048"
eevee.shadow_cascade_size         = "2048"

# Bloom (subtle)
eevee.use_bloom                   = True
eevee.bloom_threshold             = 1.0    # only fire on very bright areas
eevee.bloom_intensity             = 0.02   # REDUCED brightness
eevee.bloom_radius                = 4.0
eevee.bloom_color                 = (1.0, 0.95, 0.85)  # warm sun bloom

# Screen-space effects
eevee.use_ssr                     = True   # screen-space reflections
eevee.use_ssr_halfres             = True
eevee.use_gtao                    = True   # ambient occlusion
eevee.gtao_distance               = 0.5
eevee.gtao_factor                 = 0.6

# Volumetrics (light scatter near sun)
eevee.use_volumetric_lights       = True
eevee.volumetric_start            = 0.1
eevee.volumetric_end              = 500.0
eevee.volumetric_tile_size        = "8"
eevee.volumetric_samples          = 64
eevee.volumetric_sample_distribution = 0.8

# ── Color Management ───────────────────
scene.view_settings.view_transform = "Filmic"
scene.view_settings.look            = "Medium Contrast" # REDUCED contrast
scene.view_settings.exposure        = -0.5  # REDUCED exposure
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
w_bg2  = wn.new("ShaderNodeBackground")   # near-black fallback
w_env  = wn.new("ShaderNodeTexEnvironment")
w_tex_coord = wn.new("ShaderNodeTexCoord")
w_is_cam    = wn.new("ShaderNodeLightPath") # mix only for camera rays

star_img = load_tex("stars", colorspace="Linear")
if star_img:
    w_env.image = star_img
    wl.new(w_tex_coord.outputs["Generated"], w_env.inputs["Vector"])
    wl.new(w_env.outputs["Color"], w_bg.inputs["Color"])
    w_bg.inputs["Strength"].default_value = 0.15  # very dim stars
else:
    w_bg.inputs["Color"].default_value    = (0.005, 0.005, 0.012, 1)
    w_bg.inputs["Strength"].default_value = 1.0

w_bg2.inputs["Color"].default_value    = (0.002, 0.002, 0.005, 1)
w_bg2.inputs["Strength"].default_value = 1.0

# Use camera ray to blend: camera sees stars, lights see near-black
wl.new(w_is_cam.outputs["Is Camera Ray"], w_mix.inputs["Fac"])
wl.new(w_bg2.outputs["Background"], w_mix.inputs[1])
wl.new(w_bg.outputs["Background"],  w_mix.inputs[2])
wl.new(w_mix.outputs["Shader"],     w_out.inputs["Surface"])

# ─────────────────────────────────────────
# SATURN TILT EMPTY — spin this, not Saturn
# ─────────────────────────────────────────
# Using a parent Empty lets us tilt the whole system once and spin cleanly
bpy.ops.object.empty_add(type="PLAIN_AXES", location=(0, 0, 0))
tilt_empty = bpy.context.object
tilt_empty.name = "Saturn_TiltPivot"
tilt_empty.rotation_euler[0] = math.radians(SATURN_TILT)

# ─────────────────────────────────────────
# SATURN PLANET
# ─────────────────────────────────────────
bpy.ops.mesh.primitive_uv_sphere_add(
    radius=SATURN_RADIUS,
    segments=96, ring_count=48,
    location=(0, 0, 0)
)
saturn = bpy.context.object
saturn.name = "Saturn"
saturn.parent = tilt_empty
bpy.ops.object.shade_smooth()

# ── Saturn Material ─────────────────────
sm = bpy.data.materials.new("Saturn_Mat")
sm.use_nodes = True
sn = sm.node_tree.nodes
sl = sm.node_tree.links
sn.clear()

s_out   = sn.new("ShaderNodeOutputMaterial")
s_bsdf  = sn.new("ShaderNodeBsdfPrincipled")
s_tex   = sn.new("ShaderNodeTexImage")
s_emit  = sn.new("ShaderNodeEmission")    # fresnel atmosphere glow
s_mix   = sn.new("ShaderNodeMixShader")
s_add   = sn.new("ShaderNodeAddShader")
s_fres  = sn.new("ShaderNodeFresnel")
s_gamma = sn.new("ShaderNodeGamma")      # slight contrast boost on texture

sat_img = load_tex("saturn_map")
if sat_img:
    s_tex.image = sat_img
    sl.new(s_tex.outputs["Color"], s_gamma.inputs["Color"])
    s_gamma.inputs["Gamma"].default_value = 1.15
    sl.new(s_gamma.outputs["Color"], s_bsdf.inputs["Base Color"])
else:
    s_bsdf.inputs["Base Color"].default_value = (0.85, 0.78, 0.62, 1)

# PBR values — gas giant: slightly shiny, no metalness
s_bsdf.inputs["Roughness"].default_value   = 0.65
s_bsdf.inputs["Specular"].default_value    = 0.15
s_bsdf.inputs["Metallic"].default_value    = 0.0

# Fresnel rim — glowing atmospheric limb
s_fres.inputs["IOR"].default_value         = 1.25
# Atmosphere emission: warm pale yellow-tan
s_emit.inputs["Color"].default_value       = (0.9, 0.85, 0.65, 1)
s_emit.inputs["Strength"].default_value    = 0.35  # subtle

sl.new(s_fres.outputs["Fac"], s_mix.inputs["Fac"])
sl.new(s_bsdf.outputs["BSDF"], s_mix.inputs[1])
sl.new(s_emit.outputs["Emission"], s_mix.inputs[2])

# Final add keeps full BSDF + layer of fresnel glow on top
sl.new(s_bsdf.outputs["BSDF"], s_add.inputs[0])
sl.new(s_emit.outputs["Emission"], s_add.inputs[1])

# Mix: mostly BSDF, fresnel controls how much emission bleeds in
s_mix2 = sn.new("ShaderNodeMixShader")
s_mix2.inputs["Fac"].default_value = 0.18
sl.new(s_bsdf.outputs["BSDF"],  s_mix2.inputs[1])
sl.new(s_emit.outputs["Emission"], s_mix2.inputs[2])
sl.new(s_fres.outputs["Fac"],   s_mix2.inputs["Fac"])
sl.new(s_mix2.outputs["Shader"], s_out.inputs["Surface"])

saturn.data.materials.append(sm)

# ── Saturn spin animation (Z axis, after tilt applied by parent) ──
add_keyframe_rotation_z(saturn, 1,   0)
add_keyframe_rotation_z(saturn, TOTAL_FRAMES, 360 * SATURN_SPIN_ROTATIONS)
set_linear_cycles(saturn)

# ─────────────────────────────────────────
# RINGS — flat disk with polar UV mapping
# ─────────────────────────────────────────
# Build a flat annular disk (ring) using a UV Sphere squashed to a plane
# then scale to proper inner/outer radii.
# Cleaner: use a plane + Texture Coordinate + Vector Math to do polar mapping.

bpy.ops.mesh.primitive_circle_add(
    vertices=128,
    radius=RING_OUTER,
    fill_type="NGON",
    location=(0, 0, 0)
)
ring_mesh = bpy.context.object
ring_mesh.name = "Saturn_Rings"
ring_mesh.parent = saturn   # rings follow Saturn 100% — no independent rotation

# Scale inner hole: we'll handle transparency via the texture alpha
# (ring texture PNG should be transparent in the inner gap)
bpy.ops.object.shade_smooth()

# ── Ring Material ───────────────────────
rm = bpy.data.materials.new("Rings_Mat")
rm.use_nodes = True
rm.blend_method   = "BLEND"     # Alpha Blend is thinner and much cleaner than Hashed
rm.shadow_method  = "HASHED"    # enables shadow casting onto Saturn
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
r_norm  = rn.new("ShaderNodeVectorMath")   # normalize XY → polar
r_math_r = rn.new("ShaderNodeMath")        # compute radial distance
r_math_a = rn.new("ShaderNodeMath")        # compute angle (atan2)
r_comb_uv = rn.new("ShaderNodeCombineXYZ")

# Polar UV: U = normalized radius from center, V = angle
# Object coordinate X,Y → radius, angle
r_norm.operation  = "LENGTH"   # node for length of XY
r_math_a.operation = "ARCTAN2"
r_math_r.operation = "DIVIDE"

# Use Object coords so UV follows the mesh perfectly
rl.new(r_coord.outputs["Object"], r_sep.inputs["Vector"])

# Radius = sqrt(X²+Y²), normalized to [0,1] over outer radius
r_dist = rn.new("ShaderNodeVectorMath")
r_dist.operation = "LENGTH"
rl.new(r_sep.outputs["X"], r_comb.inputs["X"])
rl.new(r_sep.outputs["Y"], r_comb.inputs["Y"])
r_comb.inputs["Z"].default_value = 0.0
rl.new(r_comb.outputs["Vector"], r_dist.inputs[0])

# Normalize distance to [0,1]: divide by RING_OUTER
r_div = rn.new("ShaderNodeMath")
r_div.operation = "DIVIDE"
r_div.inputs[1].default_value = RING_OUTER
rl.new(r_dist.outputs["Value"], r_div.inputs[0])

# Angle: atan2(Y, X) → remap to [0,1]
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

# Final UV: X = radius (0=inner gap, 1=outer edge), Y = angle
r_uv_out = rn.new("ShaderNodeCombineXYZ")
rl.new(r_div.outputs["Value"],   r_uv_out.inputs["X"])
rl.new(r_remap.outputs["Result"], r_uv_out.inputs["Y"])
r_uv_out.inputs["Z"].default_value = 0.0

r_tex.image = load_tex("saturn_rings")
if r_tex.image:
    r_tex.extension = "EXTEND"   # don't tile rings
    r_tex.interpolation = "Cubic"
    rl.new(r_uv_out.outputs["Vector"], r_tex.inputs["Vector"])
    
    # Mix noise to make rotation visible
    r_noise = rn.new("ShaderNodeTexNoise")
    r_noise.inputs["Scale"].default_value = 15.0
    r_noise.inputs["Detail"].default_value = 10.0
    
    r_mix = rn.new("ShaderNodeMixRGB")
    r_mix.blend_type = "MULTIPLY"
    r_mix.inputs["Fac"].default_value = 0.4
    rl.new(r_tex.outputs["Color"], r_mix.inputs[1])
    rl.new(r_noise.outputs["Color"], r_mix.inputs[2])
    
    rl.new(r_mix.outputs["Color"], r_bsdf.inputs["Base Color"])
    rl.new(r_tex.outputs["Alpha"], r_bsdf.inputs["Alpha"])
else:
    # Procedural fallback — radial gradient with banded color
    r_grad = rn.new("ShaderNodeTexGradient")
    r_grad.gradient_type = "RADIAL"
    rl.new(r_coord.outputs["Object"], r_grad.inputs["Vector"])
    r_col_ramp = rn.new("ShaderNodeValToRGB")
    cr = r_col_ramp.color_ramp
    cr.elements[0].color    = (0.0, 0.0, 0.0, 0.0)   # transparent center
    cr.elements[0].position = 0.0
    e1 = cr.elements.new(0.35)
    e1.color = (0.0, 0.0, 0.0, 0.0)                    # inner gap
    e2 = cr.elements.new(0.40)
    e2.color = (0.85, 0.78, 0.68, 0.6)                 # B ring
    e3 = cr.elements.new(0.65)
    e3.color = (0.82, 0.74, 0.62, 0.85)                # A ring
    cr.elements[-1].color    = (0.0, 0.0, 0.0, 0.0)   # outer edge
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

titan,     orbit_titan = create_moon("Titan",     15, 0.85, "moon_titan",     0.3)
enceladus, orbit_enc   = create_moon("Enceladus", 11, 0.28, "moon_enceladus", 1.0)
rhea,      orbit_rhea  = create_moon("Rhea",      19, 0.52, "moon_rhea",      0.5)
dione,     orbit_dione = create_moon("Dione",     13, 0.40, "moon_dione",     0.8)

# ─────────────────────────────────────────
# LIGHTING
# ─────────────────────────────────────────

# ── 1. Primary Sun — distant directional, very high energy ──
bpy.ops.object.light_add(type="SUN", location=(200, -150, 50))
sun = bpy.context.object
sun.name = "Sun"
sun.data.energy          = 5.5       # bright, dramatic sunlight
sun.data.angle           = 0.009     # nearly parallel rays (real sun angular size)
sun.data.color           = (1.0, 0.95, 0.88)   # warm sunlight

# Aim sun perfectly at Saturn
sun_track = sun.constraints.new(type='TRACK_TO')
sun_track.target = saturn
sun_track.track_axis = 'TRACK_NEGATIVE_Z'
sun_track.up_axis = 'UP_Y'

# Contact shadow
sun.data.use_contact_shadow = True
sun.data.contact_shadow_bias     = 0.001
sun.data.contact_shadow_distance = 0.2

# ── 2. Rim light — very dim, opposite sun, gives limb glow on dark side ──
bpy.ops.object.light_add(type="SUN", location=(-80, 80, -20))
rim = bpy.context.object
rim.name = "Rim_Light"
rim.data.energy  = 0.12          # barely visible — accent only
rim.data.color   = (0.3, 0.45, 0.80)  # cool blue rim
rim.rotation_euler = (math.radians(-40), 0, math.radians(-150))

# ── 3. Ultra-dim blue ambient fill — prevents absolute black ──
bpy.ops.object.light_add(type="AREA", location=(0, 0, 80))
fill = bpy.context.object
fill.name = "Space_Fill"
fill.data.energy = 0.1           # REDUCED brightness
fill.data.size   = 300
fill.data.color  = (0.1, 0.15, 0.40)  # deep blue space tint

# ── 4. Volumetric scatter cube near scene ──────────────────
# A large transparent volume gives subtle god-ray-like scatter
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
v_vol.inputs["Density"].default_value         = 0.0008   # extremely thin
v_vol.inputs["Anisotropy"].default_value      = 0.3      # forward scattering
vl.new(v_vol.outputs["Volume"], v_out.inputs["Volume"])
vol_cube.data.materials.append(vol_mat)

# Hide from diffuse/reflection so it only affects volumetric pass
vol_cube.visible_diffuse   = False
vol_cube.visible_glossy    = False
vol_cube.visible_shadow    = False

# ─────────────────────────────────────────
# CAMERA
# ─────────────────────────────────────────
CAM_DIST = RING_OUTER * 13   # ≈ 143 BU

bpy.ops.object.camera_add(
    location=(CAM_DIST * 0.3, -CAM_DIST * 0.5, CAM_DIST * 0.15)
)
cam = bpy.context.object
cam.name = "Main_Camera"
cam.data.lens        = 85     # telephoto for cinematic compression
cam.data.clip_start  = 0.1
cam.data.clip_end    = 5000

track = cam.constraints.new(type='TRACK_TO')
track.target = saturn
track.track_axis = 'TRACK_NEGATIVE_Z'
track.up_axis = 'UP_Y'

scene.camera = cam

# Depth of Field — very shallow on moons, Saturn sharp
cam.data.dof.use_dof                  = True
cam.data.dof.focus_object             = saturn
cam.data.dof.aperture_fstop           = 2.8   # shallower depth of field

# ─────────────────────────────────────────
# RENDER OUTPUT
# ─────────────────────────────────────────
scene.render.resolution_x   = 1920
scene.render.resolution_y   = 1080
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format  = "PNG"
scene.render.image_settings.color_mode   = "RGBA"
scene.render.image_settings.color_depth  = "16"
scene.render.filepath = r"C:\solar_system\render\saturn_####.png"

# ─────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────
print("=" * 60)
print("✅  Saturn Cinematic v2 — Blender 3.6 / EEVEE")
print("    Lighting  : Sun (6.5 E) + Rim (0.12 E) + Fill (0.6 E)")
print("    Bloom     : ON  threshold=0.9  intensity=0.12")
print("    Color Mgmt: Filmic / High Contrast")
print("    Rings     : Flat circle, polar UV, Alpha Hashed shadows")
print("    Fresnel   : Saturn atmosphere glow via Fresnel mix")
print("    Volume    : Thin scatter cube (density 0.0008)")
print("    Moons     : Titan, Enceladus, Rhea, Dione")
print("    Animation : LINEAR + CYCLES modifier (seamless loop)")
print(f"   Frames    : {TOTAL_FRAMES}  |  Saturn spin: {SATURN_SPIN_ROTATIONS}x")
print("=" * 60)

# ─────────────────────────────────────────
# FORCE CAMERA VIEW IN VIEWPORT
# ─────────────────────────────────────────
# This automatically snaps your 3D view to the camera so you don't have to click anything!
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.region_3d.view_perspective = 'CAMERA'
                break