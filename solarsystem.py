import bpy
import math
import os
from mathutils import Vector, Matrix, Quaternion

# ============================================================
# CONFIGURATION
# ============================================================
TEXTURE_DIR = r"C:\solar_system"
RENDER_ENGINE = "BLENDER_EEVEE"
RESOLUTION_X = 1920
RESOLUTION_Y = 1080
FRAME_START = 1
FRAME_END = 1500
USE_BLOOM = True
USE_MOTION_BLUR = False


def tex(filename):
    """Return full path to a texture file."""
    return os.path.join(TEXTURE_DIR, filename)


# ============================================================
# SECTION 1 – SCENE SETUP
# ============================================================
def setup_scene():
    # Clear everything robustly
    for obj in bpy.data.objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    for mat in bpy.data.materials:
        bpy.data.materials.remove(mat, do_unlink=True)
    for col in list(bpy.data.collections):
        bpy.data.collections.remove(col)

    scene = bpy.context.scene
    scene.frame_start = FRAME_START
    scene.frame_end   = FRAME_END

    # Render engine
    scene.render.engine = RENDER_ENGINE
    scene.render.resolution_x = RESOLUTION_X
    scene.render.resolution_y = RESOLUTION_Y
    scene.render.film_transparent = False

    if RENDER_ENGINE == "BLENDER_EEVEE":
        eevee = scene.eevee
        eevee.use_bloom = USE_BLOOM
        eevee.bloom_intensity = 0.5    # Massive bloom for glowing sun and nebula
        eevee.bloom_threshold = 0.8    # Allow softer elements to glow
        eevee.bloom_radius = 6.0       # Spread the glow out wider
        eevee.use_ssr = True
        eevee.use_soft_shadows = True
        eevee.shadow_cube_size = '1024'
        eevee.taa_render_samples = 64
        if USE_MOTION_BLUR:
            eevee.use_motion_blur = True
    else:
        cycles = scene.cycles
        cycles.samples = 128
        if USE_MOTION_BLUR:
            scene.render.use_motion_blur = True
        
        # In Cycles, Bloom must be done via the Compositor using a Glare node
        if USE_BLOOM:
            scene.use_nodes = True
            tree = scene.node_tree
            tree.nodes.clear()
            
            rlayers = tree.nodes.new(type='CompositorNodeRLayers')
            rlayers.location = (0, 0)
            
            glare = tree.nodes.new(type='CompositorNodeGlare')
            glare.location = (300, 0)
            glare.glare_type = 'FOG_GLOW'
            glare.quality = 'HIGH'
            glare.threshold = 0.8
            glare.size = 9  # Max size for glow spread
            
            comp = tree.nodes.new(type='CompositorNodeComposite')
            comp.location = (600, 0)
            
            tree.links.new(rlayers.outputs['Image'], glare.inputs['Image'])
            tree.links.new(glare.outputs['Image'], comp.inputs['Image'])

    # World – starfield
    world = bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    wnt = world.node_tree
    wnt.nodes.clear()

    bg_node  = wnt.nodes.new("ShaderNodeBackground")
    out_node = wnt.nodes.new("ShaderNodeOutputWorld")
    out_node.location = (300, 0)

    # 1. Procedural Cosmic Nebula
    noise = wnt.nodes.new("ShaderNodeTexNoise")
    noise.location = (-600, 200)
    noise.inputs["Scale"].default_value = 1.2
    noise.inputs["Detail"].default_value = 15.0
    noise.inputs["Roughness"].default_value = 0.55
    
    ramp = wnt.nodes.new("ShaderNodeValToRGB")
    ramp.location = (-400, 200)
    ramp.color_ramp.elements[0].position = 0.4
    ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1.0)
    ramp.color_ramp.elements[1].position = 0.6
    ramp.color_ramp.elements[1].color = (0.05, 0.005, 0.01, 1.0) # Subtle lowkey purple space dust
    ramp.color_ramp.elements.new(0.85)
    ramp.color_ramp.elements[2].color = (0.15, 0.05, 0.01, 1.0) # Lowkey dark orange dust
    
    wnt.links.new(noise.outputs["Fac"], ramp.inputs["Fac"])
    
    # 2. Base Stars
    stars_path = tex("stars.jpg")
    mix_node = wnt.nodes.new("ShaderNodeMixRGB")
    mix_node.blend_type = 'ADD'
    mix_node.inputs[0].default_value = 1.0
    mix_node.location = (-150, 0)

    if os.path.exists(stars_path):
        tex_coord = wnt.nodes.new("ShaderNodeTexCoord")
        mapping    = wnt.nodes.new("ShaderNodeMapping")
        img_node   = wnt.nodes.new("ShaderNodeTexEnvironment")
        tex_coord.location  = (-800, -200)
        mapping.location    = (-600, -200)
        img_node.location   = (-400, -200)
        try:
            img_node.image = bpy.data.images.load(stars_path)
        except Exception:
            pass
        wnt.links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
        wnt.links.new(mapping.outputs["Vector"],      img_node.inputs["Vector"])
        wnt.links.new(img_node.outputs["Color"], mix_node.inputs[1])
    else:
        mix_node.inputs[1].default_value = (0.0, 0.0, 0.0, 1.0)

    wnt.links.new(ramp.outputs["Color"], mix_node.inputs[2])
    wnt.links.new(mix_node.outputs["Color"], bg_node.inputs["Color"])
    bg_node.inputs["Strength"].default_value = 0.5

    wnt.links.new(bg_node.outputs["Background"], out_node.inputs["Surface"])
    return scene


# ============================================================
# SECTION 2 – MATERIAL HELPERS
# ============================================================
def make_material_principled(name, texture_path, emission_color=None,
                              emission_strength=0.0, roughness=0.8,
                              metallic=0.0, alpha=1.0, blend_mode=None, bump_path=None):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out   = nodes.new("ShaderNodeOutputMaterial"); out.location   = (600, 0)
    bsdf  = nodes.new("ShaderNodeBsdfPrincipled");  bsdf.location  = (200, 0)
    bsdf.inputs["Roughness"].default_value  = roughness
    bsdf.inputs["Metallic"].default_value   = metallic

    if texture_path and os.path.exists(texture_path):
        coord = nodes.new("ShaderNodeTexCoord"); coord.location = (-600, 0)
        uvmap = nodes.new("ShaderNodeMapping");   uvmap.location  = (-400, 0)
        img   = nodes.new("ShaderNodeTexImage");  img.location    = (-150, 50)
        try:
            img.image = bpy.data.images.load(texture_path, check_existing=True)
        except Exception:
            pass
        links.new(coord.outputs["UV"],     uvmap.inputs["Vector"])
        links.new(uvmap.outputs["Vector"], img.inputs["Vector"])
        links.new(img.outputs["Color"],    bsdf.inputs["Base Color"])

        if alpha < 1.0:
            links.new(img.outputs["Alpha"], bsdf.inputs["Alpha"])
            mat.blend_method  = blend_mode or "BLEND"
            mat.shadow_method = "CLIP"

    if bump_path and os.path.exists(bump_path):
        if not ("coord" in locals() and "uvmap" in locals()):
            coord = nodes.new("ShaderNodeTexCoord"); coord.location = (-600, 0)
            uvmap = nodes.new("ShaderNodeMapping");   uvmap.location  = (-400, 0)
        bump_img = nodes.new("ShaderNodeTexImage"); bump_img.location = (-150, -250)
        bump_node = nodes.new("ShaderNodeBump"); bump_node.location = (50, -250)
        try:
            bump_img.image = bpy.data.images.load(bump_path, check_existing=True)
            bump_img.image.colorspace_settings.name = 'Non-Color'
        except Exception:
            pass
        links.new(uvmap.outputs["Vector"], bump_img.inputs["Vector"])
        links.new(bump_img.outputs["Color"], bump_node.inputs["Height"])
        links.new(bump_node.outputs["Normal"], bsdf.inputs["Normal"])
        bump_node.inputs["Distance"].default_value = 0.2

    if emission_color and emission_strength > 0:
        emit_color_key = "Emission Color" if "Emission Color" in bsdf.inputs else "Emission"
        bsdf.inputs[emit_color_key].default_value = (*emission_color, 1)
        bsdf.inputs["Emission Strength"].default_value = emission_strength

    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_sun_material():
    mat   = bpy.data.materials.new(name="Sun_Mat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out   = nodes.new("ShaderNodeOutputMaterial"); out.location   = (600, 0)
    emit  = nodes.new("ShaderNodeEmission");        emit.location  = (200, 0)
    emit.inputs["Strength"].default_value = 15.0 # Dramatic intensity
    emit.inputs["Color"].default_value    = (1.0, 0.35, 0.02, 1.0) # Deep fiery orange

    tex_path = tex("sun_surface.jpg")
    if os.path.exists(tex_path):
        coord = nodes.new("ShaderNodeTexCoord"); coord.location = (-600, 0)
        uvmap = nodes.new("ShaderNodeMapping");   uvmap.location  = (-400, 0)
        img   = nodes.new("ShaderNodeTexImage");  img.location    = (-150, 0)
        try:
            img.image = bpy.data.images.load(tex_path, check_existing=True)
        except Exception:
            pass
        mix = nodes.new("ShaderNodeMixRGB"); mix.location = (-10, 100)
        mix.blend_type = 'MULTIPLY'
        mix.inputs["Fac"].default_value = 0.6
        mix.inputs["Color2"].default_value = (1.0, 0.75, 0.2, 1.0)
        links.new(coord.outputs["UV"],     uvmap.inputs["Vector"])
        links.new(uvmap.outputs["Vector"], img.inputs["Vector"])
        links.new(img.outputs["Color"],    mix.inputs["Color1"])
        links.new(mix.outputs["Color"],    emit.inputs["Color"])

    links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


def make_earth_atmosphere():
    """Subtle atmospheric glow shell around Earth."""
    mat   = bpy.data.materials.new(name="Earth_Atmo")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out   = nodes.new("ShaderNodeOutputMaterial"); out.location = (600, 0)
    trans = nodes.new("ShaderNodeBsdfTransparent"); trans.location = (-100, 100)
    emit  = nodes.new("ShaderNodeEmission");         emit.location  = (-100, -50)
    emit.inputs["Color"].default_value    = (0.2, 0.5, 1.0, 1.0)
    emit.inputs["Strength"].default_value = 0.3

    fac = nodes.new("ShaderNodeLayerWeight"); fac.location = (-300, 0)
    fac.inputs["Blend"].default_value = 0.45
    mix = nodes.new("ShaderNodeMixShader"); mix.location = (400, 0)

    links.new(fac.outputs["Facing"],    mix.inputs["Fac"])
    links.new(trans.outputs["BSDF"],    mix.inputs[1])
    links.new(emit.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"],    out.inputs["Surface"])

    mat.blend_method  = "BLEND"
    mat.shadow_method = "NONE"
    return mat


def make_ring_material(ring_texture=None):
    mat   = bpy.data.materials.new(name="Ring_Mat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out  = nodes.new("ShaderNodeOutputMaterial"); out.location  = (600, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled");  bsdf.location = (200, 0)
    bsdf.inputs["Roughness"].default_value = 0.9
    bsdf.inputs["Alpha"].default_value     = 0.55

    mat.blend_method  = "BLEND"
    mat.shadow_method = "NONE"

    if ring_texture and os.path.exists(ring_texture):
        coord = nodes.new("ShaderNodeTexCoord"); coord.location = (-600, 0)
        img   = nodes.new("ShaderNodeTexImage");  img.location    = (-150, 50)
        bw    = nodes.new("ShaderNodeRGBToBW");   bw.location     = (50, -50)
        try:
            img.image = bpy.data.images.load(ring_texture, check_existing=True)
        except Exception:
            pass
        links.new(coord.outputs["UV"],   img.inputs["Vector"])
        links.new(img.outputs["Color"],  bsdf.inputs["Base Color"])
        links.new(img.outputs["Color"],  bw.inputs["Color"])
        links.new(bw.outputs["Val"],     bsdf.inputs["Alpha"])
    else:
        bsdf.inputs["Base Color"].default_value = (0.85, 0.78, 0.65, 1.0)

    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


# ============================================================
# SECTION 3 – OBJECT HELPERS
# ============================================================
def add_uv_sphere(name, radius, location=(0, 0, 0), segments=64, rings=32):
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius, location=location,
        segments=segments, ring_count=rings)
    obj = bpy.context.active_object
    obj.name = name
    bpy.ops.object.shade_smooth()
    return obj


def add_flat_ring(name, radius, location=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(
        vertices=128, radius=radius, depth=0.001,
        location=location, rotation=(0, 0, 0))
    obj = bpy.context.active_object
    obj.name = name
    bpy.ops.object.shade_smooth()
    return obj


def create_empty(name, location=(0, 0, 0)):
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=location)
    obj = bpy.context.active_object
    obj.name = name
    return obj


def add_point_light(name, location, energy, radius=0.5, color=(1, 0.9, 0.7)):
    bpy.ops.object.light_add(type='POINT', location=location)
    light = bpy.context.active_object
    light.name = name
    light.data.energy       = energy
    light.data.color        = color
    light.data.shadow_soft_size = radius
    return light


def assign_material(obj, mat):
    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


# ============================================================
# SECTION 4 – PLANET DEFINITIONS
# ============================================================
# (name, radius, orbit_radius, orbital_period_frames,
#  self_rot_period_frames, axial_tilt_deg,
#  base_color_rgba, texture_filename)
PLANET_DATA = [
    # True relative size (Earth = 0.3)
    # Name, radius, orbit_r, orb_period_days, rot_period, axial_tilt, base_color, tex_filename
    ("Mercury", 0.11,  12,     88,   58,  0.03,  (0.6, 0.5, 0.45, 1), "mercury_color.jpg"),
    ("Venus",   0.28,  18,    225,  243,  177.4, (0.9, 0.8, 0.5,  1), "venus_surface.jpg"),
    ("Earth",   0.30,  25,    365,    1,   23.4, (0.2, 0.5, 0.9,  1), "earth_daymap.jpg"),
    ("Mars",    0.16,  34,    687,   1.03, 25.2, (0.8, 0.4, 0.2,  1), "mars_surface.jpg"),
    ("Jupiter", 3.36,  55,   4333,   0.41, 3.1,  (0.8, 0.7, 0.55, 1), "jupiter_map.jpg"),
    ("Saturn",  2.83,  80,  10759,   0.45, 26.7, (0.9, 0.85, 0.6, 1), "saturn_color.jpg"),
    ("Uranus",  1.20, 105,  30688,   0.72, 97.8, (0.5, 0.85, 0.9, 1), "uranus.jpg"),
    ("Neptune", 1.16, 125,  60182,   0.67, 28.3, (0.2, 0.4, 0.9,  1), "neptune_surface.jpg"),
    ("Pluto",   0.05, 150,  90560,   6.39, 122.5, (0.6, 0.5, 0.4,  1), "pluto_map.jpg"),
]

SUN_RADIUS = 8.0

# Global orbital speed multiplier (keeps relative speeds mathematically perfectly accurate)
SPEED_SCALE = 1.5


# ============================================================
# SECTION 5 – BUILD SOLAR SYSTEM
# ============================================================
def build_solar_system():
    planets = {}

    # ----- SUN -----
    sun_obj = add_uv_sphere("Sun", SUN_RADIUS)
    sun_mat = make_sun_material()
    assign_material(sun_obj, sun_mat)

    # FIX 1: Sun mesh must NOT cast shadows.
    # Eevee's shadow cubemap sees the sphere enclosing the point light
    # and projects it as a huge shadow ball that blacks out all planets
    # every time the shadow map recalculates during playback.
    sun_obj.visible_shadow = False

    # Sun point light - extremely high intensity for high contrast realism
    sun_light = add_point_light("SunLight", (0, 0, 0), energy=150000,
                                radius=SUN_RADIUS, color=(1.0, 0.95, 0.9))

    # FIX 2: Disable shadows on the point light.
    sun_light.data.use_shadow = False

    # FIX 3: Extend light cutoff so outer planets (Pluto r=150) stay lit.
    sun_light.data.use_custom_distance = True
    sun_light.data.cutoff_distance     = 600.0

    # Ambient fill light (very weak, to maintain dark space but not pure black)
    bpy.ops.object.light_add(type='SUN', rotation=(math.radians(45), math.radians(45), 0))
    fill = bpy.context.active_object
    fill.name = "AmbientFill"
    fill.data.energy = 0.01  # Drastically reduced for deep cinematic shadows
    fill.data.color = (0.3, 0.35, 0.5)
    fill.data.use_shadow = False
    
    # Subtle rim light style fill
    bpy.ops.object.light_add(type='SUN', rotation=(math.radians(-45), math.radians(-135), 0))
    fill2 = bpy.context.active_object
    fill2.name = "AmbientFill2"
    fill2.data.energy = 0.03
    fill2.data.color = (0.7, 0.8, 1.0)
    fill2.data.use_shadow = False

    # ----- PLANETS -----
    for (pname, prad, orbit_r, orb_period, rot_period,
         axial_tilt, base_color, tex_file) in PLANET_DATA:

        # Pivot empty at origin
        pivot = create_empty(f"{pname}_Pivot")

        # Planet sphere
        planet = add_uv_sphere(pname, prad, location=(orbit_r, 0, 0))
        planet.parent = pivot

        # Axial tilt
        planet.rotation_euler.x = math.radians(axial_tilt)

        # Material
        tpath = tex(tex_file)
        bpath = tex(f"{pname.lower()}_bump.jpg") if pname == "Pluto" else None
        mat = make_material_principled(
            f"{pname}_Mat", tpath,
            roughness=0.85, metallic=0.0,
            bump_path=bpath)
        if not os.path.exists(tpath):
            mat.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = base_color
        assign_material(planet, mat)

        planets[pname] = {"pivot": pivot, "planet": planet,
                          "orbit_r": orbit_r, "radius": prad}

    # ----- SATURN RINGS -----
    saturn_info = planets["Saturn"]
    sat_obj     = saturn_info["planet"]
    sat_r       = saturn_info["radius"]

    ring_tex_path = tex("saturn_ring.jpg")

    ring = add_flat_ring("Saturn_Ring",
                         radius=sat_r * 2.2,
                         location=(0, 0, 0))
    ring.parent = sat_obj
    ring_mat = make_ring_material(ring_tex_path if os.path.exists(ring_tex_path) else None)
    assign_material(ring, ring_mat)

    # ----- MOON -----
    earth_info = planets["Earth"]
    earth_obj  = earth_info["planet"]
    earth_r    = earth_info["radius"]
    
    moon_radius = earth_r * 0.27
    moon_orbit_r = earth_r * 3.0
    moon_obj = add_uv_sphere("Moon", moon_radius, location=(moon_orbit_r, 0, 0))
    moon_obj.parent = earth_obj
    
    moon_tex_path = tex("moon.jpg")
    moon_mat = make_material_principled(
        "Moon_Mat", moon_tex_path,
        roughness=0.9, metallic=0.0)
    assign_material(moon_obj, moon_mat)

    # ----- JUPITER MOONS -----
    jup_info = planets["Jupiter"]
    jup_obj  = jup_info["planet"]
    jup_r    = jup_info["radius"]
    
    jup_moons = [
        ("Io", jup_r * 0.025, jup_r * 1.5, "moon_io.jpg"),
        ("Europa", jup_r * 0.02, jup_r * 2.0, "moon_europa.jpg"),
        ("Ganymede", jup_r * 0.035, jup_r * 2.6, "moon_ganymede.jpg"),
        ("Callisto", jup_r * 0.032, jup_r * 3.3, "moon_callisto.jpg")
    ]
    
    for i, (m_name, m_rad, m_dist, m_tex) in enumerate(jup_moons):
        angle = i * (math.pi / 2)
        lx = m_dist * math.cos(angle)
        ly = m_dist * math.sin(angle)
        m_obj = add_uv_sphere(m_name, m_rad, location=(lx, ly, 0))
        m_obj.parent = jup_obj
        
        m_tex_path = tex(m_tex)
        m_mat = make_material_principled(
            f"{m_name}_Mat", m_tex_path,
            roughness=0.9, metallic=0.0)
        assign_material(m_obj, m_mat)

    return planets



# ============================================================
# SECTION 5b – ORBIT LINES
# ============================================================
def add_orbit_lines():
    """Draw a faint emissive circle at each planet's orbital radius."""

    mat = bpy.data.materials.new("Orbit_Line_Mat")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out  = nodes.new("ShaderNodeOutputMaterial"); out.location  = (400, 0)
    emit = nodes.new("ShaderNodeEmission");        emit.location = (100, 0)
    emit.inputs["Color"].default_value    = (0.4, 0.6, 1.0, 1.0)
    emit.inputs["Strength"].default_value = 0.7  # Below bloom threshold to prevent bright glowing
    
    # We add a Mix Shader to animate opacity
    trans = nodes.new("ShaderNodeBsdfTransparent"); trans.location = (100, 100)
    mix = nodes.new("ShaderNodeMixShader"); mix.location = (250, 50)
    mix.name = "OrbitFadeMix"
    mix.inputs[0].default_value = 1.0 # 0 = transparent, 1 = emission
    
    links.new(trans.outputs["BSDF"], mix.inputs[1])
    links.new(emit.outputs["Emission"], mix.inputs[2])
    links.new(mix.outputs["Shader"], out.inputs["Surface"])

    mat.blend_method  = "BLEND"
    mat.shadow_method = "NONE"

    ORBIT_SEGMENTS = 256

    for (pname, prad, orbit_r, *_rest) in PLANET_DATA:
        curve_data = bpy.data.curves.new(name=f"Orbit_{pname}", type='CURVE')
        curve_data.dimensions          = '3D'
        curve_data.resolution_u        = 12
        curve_data.render_resolution_u = 24
        curve_data.bevel_depth         = 0.014  # Physically thicker so they don't vanish from afar without bloom
        curve_data.use_fill_caps       = True

        spline = curve_data.splines.new('POLY')
        spline.use_cyclic_u = True
        spline.points.add(ORBIT_SEGMENTS - 1)

        for i, pt in enumerate(spline.points):
            angle = (2 * math.pi * i) / ORBIT_SEGMENTS
            pt.co = (
                orbit_r * math.cos(angle),
                orbit_r * math.sin(angle),
                0.0,
                1.0
            )

        orbit_obj = bpy.data.objects.new(f"Orbit_{pname}", curve_data)
        bpy.context.collection.objects.link(orbit_obj)
        orbit_obj.data.materials.append(mat)


# ============================================================
# SECTION 6 – ANIMATION
# ============================================================
def animate_solar_system(planets):
    scene = bpy.context.scene
    scene.frame_set(1)

    for (pname, prad, orbit_r, orb_period, rot_period,
         axial_tilt, base_color, tex_file) in PLANET_DATA:

        pivot  = planets[pname]["pivot"]
        planet = planets[pname]["planet"]

        # ---- Orbital rotation (pivot Z-axis) ----
        # Degrees per frame = 360 / (orb_period / SPEED_SCALE)
        deg_per_frame = 360.0 / (orb_period / SPEED_SCALE)

        pivot.rotation_euler = (0, 0, 0)
        pivot.keyframe_insert(data_path="rotation_euler", frame=1)
        total_degrees = deg_per_frame * FRAME_END
        pivot.rotation_euler.z = math.radians(total_degrees)
        pivot.keyframe_insert(data_path="rotation_euler", frame=FRAME_END)

        # Linear interpolation for orbits
        for fcurve in pivot.animation_data.action.fcurves:
            for kf in fcurve.keyframe_points:
                kf.interpolation = 'LINEAR'

        # ---- Self-rotation (planet Y-axis, accounting for tilt) ----
        # Cinematic slow rotation instead of realistic strobe-effect speeds
        rot_deg_per_frame = 0.5
        planet.rotation_euler = (math.radians(axial_tilt), 0, 0)
        planet.keyframe_insert(data_path="rotation_euler", frame=1)
        planet.rotation_euler = (math.radians(axial_tilt), 0,
                                 math.radians(rot_deg_per_frame * FRAME_END))
        planet.keyframe_insert(data_path="rotation_euler", frame=FRAME_END)

        for fcurve in planet.animation_data.action.fcurves:
            for kf in fcurve.keyframe_points:
                kf.interpolation = 'LINEAR'

    # Sun slow self-rotation
    sun = bpy.data.objects.get("Sun")
    if sun:
        sun.rotation_euler.z = 0
        sun.keyframe_insert(data_path="rotation_euler", frame=1)
        sun.rotation_euler.z = math.radians(360 * 2)
        sun.keyframe_insert(data_path="rotation_euler", frame=FRAME_END)
        for fcurve in sun.animation_data.action.fcurves:
            for kf in fcurve.keyframe_points:
                kf.interpolation = 'LINEAR'


# ============================================================
# SECTION 7 – PLANET LABELS
# ============================================================
def add_planet_labels(planets, cam_obj, blocks):
    label_objects = {}

    for (pname, prad, orbit_r, orb_period, rot_period,
         axial_tilt, base_color, tex_file) in PLANET_DATA:

        planet = planets[pname]["planet"]
        pivot = planets[pname]["pivot"]
        
        # Adjust radius consideration for Saturn to account for its rings
        label_prad = prad * 2.5 if pname == "Saturn" else prad
        
        # 1. Create an Empty Rig to act as a billboard center
        billboard_rig = create_empty(f"LabelRig_{pname}", location=(orbit_r, 0, 0))
        
        # Parent to the pivot. It will follow the planet's orbit perfectly, 
        # but won't inherit the planet's spinning rotation!
        billboard_rig.parent = pivot
        
        # Rig always faces the camera (Z points to camera, Y points Up, X points Right)
        c_track = billboard_rig.constraints.new(type='TRACK_TO')
        c_track.target = cam_obj
        c_track.track_axis = 'TRACK_Z'
        c_track.up_axis = 'UP_Y'

        # 2. Create the Text Object
        bpy.ops.object.text_add(location=(0, 0, 0))
        txt_obj = bpy.context.active_object
        txt_obj.name = f"Label_{pname}"
        txt_obj.parent = billboard_rig

        # 3. Typography & Styling
        txt_obj.data.body = pname.upper()  # All caps
        txt_obj.data.size = label_prad * 0.35  # Strict proportional scale so all planets match visually
        txt_obj.data.align_x = 'LEFT'
        txt_obj.data.space_character = 1.4  # Cinematic letter spacing
        
        # Offset text strictly proportional to the planet's radius
        txt_obj.location = (label_prad * 1.3, label_prad * 0.2, 0)
        
        # Try to load a clean modern font (Windows standard)
        font_path = "C:\\Windows\\Fonts\\segoeuil.ttf"  # Segoe UI Light
        if not os.path.exists(font_path):
            font_path = "C:\\Windows\\Fonts\\arial.ttf"
            
        if os.path.exists(font_path):
            try:
                fnt = bpy.data.fonts.load(font_path)
                txt_obj.data.font = fnt
            except Exception:
                pass

        # 4. Material with subtle glow and animated transparency
        lmat = bpy.data.materials.new(f"Label_{pname}_Mat")
        lmat.use_nodes = True
        lmat.blend_method = 'BLEND'
        ln = lmat.node_tree.nodes
        ll = lmat.node_tree.links
        ln.clear()

        lout = ln.new("ShaderNodeOutputMaterial")
        lout.location = (400, 0)

        lemit = ln.new("ShaderNodeEmission")
        lemit.location = (0, 0)
        # Subtle bluish-white for space aesthetic
        lemit.inputs["Color"].default_value = (0.85, 0.92, 1.0, 1.0)
        lemit.inputs["Strength"].default_value = 1.5  # Subtle glow

        ltrans = ln.new("ShaderNodeBsdfTransparent")
        ltrans.location = (0, 100)

        lmix = ln.new("ShaderNodeMixShader")
        lmix.location = (200, 50)
        lmix.inputs[0].default_value = 0.0  # 0 = Transparent, 1 = Emission

        ll.new(ltrans.outputs["BSDF"], lmix.inputs[1])
        ll.new(lemit.outputs["Emission"], lmix.inputs[2])
        ll.new(lmix.outputs["Shader"], lout.inputs["Surface"])

        txt_obj.data.materials.append(lmat)

        # Store mix node to animate it later
        label_objects[pname] = {"obj": txt_obj, "mix_node": lmix}

    # 5. Animate visibility based on camera segments
    for idx, (pname, b_start, b_end) in enumerate(blocks):
        trans_end = b_start if idx == 0 else b_start + 40
        showcase_start = trans_end
        showcase_end = b_end

        fade_in_start = showcase_start
        fade_in_end = showcase_start + 20
        fade_out_start = showcase_end - 20
        fade_out_end = showcase_end

        mix_node = label_objects[pname]["mix_node"]

        # Keep transparent before fade in
        mix_node.inputs[0].default_value = 0.0
        mix_node.inputs[0].keyframe_insert(data_path="default_value", frame=1)
        mix_node.inputs[0].keyframe_insert(data_path="default_value", frame=fade_in_start)

        # Fade in
        mix_node.inputs[0].default_value = 1.0
        mix_node.inputs[0].keyframe_insert(data_path="default_value", frame=fade_in_end)

        # Hold
        mix_node.inputs[0].keyframe_insert(data_path="default_value", frame=fade_out_start)

        # Fade out
        mix_node.inputs[0].default_value = 0.0
        mix_node.inputs[0].keyframe_insert(data_path="default_value", frame=fade_out_end)

        # Apply bezier interpolation for smooth cinematic fade
        if mix_node.id_data.animation_data and mix_node.id_data.animation_data.action:
            for fcurve in mix_node.id_data.animation_data.action.fcurves:
                for kf in fcurve.keyframe_points:
                    kf.interpolation = 'BEZIER'

    return label_objects


# ============================================================
# SECTION 8 – CAMERA SYSTEM
# ============================================================
def build_camera_system(planets):
    # 1. Create Rig Objects
    cam_target = create_empty("CameraTarget")
    cam_pivot = create_empty("CameraPivot")

    # 2. Create Camera
    bpy.ops.object.camera_add(location=(0, -250, 100))
    cam_obj = bpy.context.active_object
    cam_obj.name = "MainCamera"
    bpy.context.scene.camera = cam_obj

    # Parent Camera to Pivot
    cam_obj.parent = cam_pivot

    # Constraint Camera to Target
    track = cam_obj.constraints.new(type='TRACK_TO')
    track.target = cam_target
    track.track_axis = 'TRACK_NEGATIVE_Z'
    track.up_axis = 'UP_Y'

    # Setup Cinematic Depth of Field
    cam_data = cam_obj.data
    cam_data.lens = 50  # Cinematic 50mm lens
    cam_data.clip_start = 0.01
    cam_data.clip_end = 2000
    cam_data.dof.use_dof = True
    cam_data.dof.focus_object = cam_target
    cam_data.dof.aperture_fstop = 1.8  # Strong subject focus
    
    # Offset camera slightly for rule-of-thirds framing
    cam_data.shift_x = 0.15

    # Slight camera tilt for realism
    cam_obj.rotation_euler.y = math.radians(2)

    # 3. Setup Target Constraints
    sun_obj = bpy.data.objects.get("Sun")

    c_sun_pivot = cam_pivot.constraints.new(type='COPY_LOCATION')
    c_sun_pivot.target = sun_obj
    c_sun_pivot.name = "Copy_Sun"

    c_sun_tgt = cam_target.constraints.new(type='COPY_LOCATION')
    c_sun_tgt.target = sun_obj
    c_sun_tgt.name = "Copy_Sun"

    for pname in PLANET_DATA:
        p_name = pname[0]
        planet_obj = planets[p_name]["planet"]

        cp = cam_pivot.constraints.new(type='COPY_LOCATION')
        cp.target = planet_obj
        cp.name = f"Copy_{p_name}"
        cp.influence = 0.0

        ct = cam_target.constraints.new(type='COPY_LOCATION')
        ct.target = planet_obj
        ct.name = f"Copy_{p_name}"
        ct.influence = 0.0

    def keyframe_influence(target_name, frame, influence):
        """Helper to animate the target influence of the camera rig."""
        for obj in [cam_pivot, cam_target]:
            c = obj.constraints.get(f"Copy_{target_name}")
            if c:
                c.influence = influence
                c.keyframe_insert(data_path="influence", frame=frame)

    # Setup Light Animation
    sun_light_obj = bpy.data.objects.get("SunLight")
    sun_light = sun_light_obj.data if sun_light_obj else None

    planet_light_energies = {
        "Sun": 80000.0,
        "Mercury": 15000.0,
        "Venus": 35000.0,
        "Earth": 75000.0,
        "Mars": 140000.0,
        "Jupiter": 360000.0,
        "Saturn": 750000.0,
        "Uranus": 1300000.0,
        "Neptune": 1850000.0,
        "Pluto": 2700000.0
    }

    if sun_light:
        sun_light.energy = 80000.0
        sun_light.keyframe_insert(data_path="energy", frame=1)
        sun_light.keyframe_insert(data_path="energy", frame=240)

    # 4. Animate Scene 1 – Overview
    keyframe_influence("Sun", 1, 1.0)
    for pname in PLANET_DATA:
        keyframe_influence(pname[0], 1, 0.0)

    # Overview Camera Motion (Arc/Orbit, slow easing)
    cam_obj.location = (-60, -140, 100)
    cam_obj.keyframe_insert(data_path="location", frame=1)

    cam_obj.location = (50, -80, 60)
    cam_obj.keyframe_insert(data_path="location", frame=240)

    # Set initial aperture f-stop keyframes for overview (Sun)
    cam_data.dof.aperture_fstop = 1.8
    cam_data.dof.keyframe_insert(data_path="aperture_fstop", frame=1)
    cam_data.dof.keyframe_insert(data_path="aperture_fstop", frame=240)

    # Animate orbit lines fading out after the overview
    orbit_mat = bpy.data.materials.get("Orbit_Line_Mat")
    orbit_mix = orbit_mat.node_tree.nodes["OrbitFadeMix"] if orbit_mat else None

    if orbit_mix:
        orbit_mix.inputs[0].default_value = 1.0
        orbit_mix.inputs[0].keyframe_insert(data_path="default_value", frame=1)
        orbit_mix.inputs[0].keyframe_insert(data_path="default_value", frame=240)
        orbit_mix.inputs[0].default_value = 0.0
        orbit_mix.inputs[0].keyframe_insert(data_path="default_value", frame=300)

    # Hold Sun target until transition ends
    keyframe_influence("Sun", 300, 1.0)
    keyframe_influence("Sun", 301, 0.0)

    # 5. Define Timings
    blocks = [
        ("Mercury", 300, 420),
        ("Venus", 420, 540),
        ("Earth", 540, 660),
        ("Mars", 660, 780),
        ("Jupiter", 780, 900),
        ("Saturn", 900, 1020),
        ("Uranus", 1020, 1140),
        ("Neptune", 1140, 1260),
        ("Pluto", 1260, 1380),
    ]

    prev_target = "Sun"
    prev_end_frame = 240
    prev_fstop = 1.8

    # 6. Animate Planet Showcases
    for idx, (pname, b_start, b_end) in enumerate(blocks):
        trans_start = prev_end_frame
        trans_end = b_start if idx == 0 else b_start + 40
        showcase_start = trans_end
        showcase_end = b_end

        # Keep previous target at 1.0 until transition ends
        keyframe_influence(prev_target, trans_end, 1.0)
        keyframe_influence(prev_target, trans_end + 1, 0.0)

        # Fade in new target
        keyframe_influence(pname, trans_start, 0.0)
        keyframe_influence(pname, trans_end, 1.0)
        keyframe_influence(pname, showcase_end, 1.0)

        prad = planets[pname]["radius"]
        
        # Calculate appropriate f-stop to prevent blurry text on small planets (Mercury, Venus, Earth, Mars, Pluto)
        # Inversely proportional to radius to expand the depth of field window on close-ups.
        fstop = max(1.8, 1.2 / prad)
        
        # Animate the f-stop transition
        cam_data.dof.aperture_fstop = prev_fstop
        cam_data.dof.keyframe_insert(data_path="aperture_fstop", frame=trans_start)
        cam_data.dof.aperture_fstop = fstop
        cam_data.dof.keyframe_insert(data_path="aperture_fstop", frame=trans_end)
        cam_data.dof.keyframe_insert(data_path="aperture_fstop", frame=showcase_end)

        # Animate dynamic lighting exposure
        if sun_light:
            prev_energy = planet_light_energies.get(prev_target, 80000.0)
            current_energy = planet_light_energies.get(pname, 80000.0)
            
            sun_light.energy = prev_energy
            sun_light.keyframe_insert(data_path="energy", frame=trans_start)
            
            sun_light.energy = current_energy
            sun_light.keyframe_insert(data_path="energy", frame=trans_end)
            sun_light.keyframe_insert(data_path="energy", frame=showcase_end)

        # Pull camera back further for Saturn so the rings fit perfectly
        cam_prad = prad * 2.5 if pname == "Saturn" else prad

        # Local camera position (arc/orbital movement around planet)
        start_loc = (-cam_prad * 5, -cam_prad * 8, cam_prad * 4)
        end_loc = (cam_prad * 4, -cam_prad * 6, cam_prad * 2)

        # Pause/Drift mid-animation focusing calculation
        dur = showcase_end - showcase_start
        hold_start = showcase_start + int(dur * 0.25)
        hold_end = showcase_end - int(dur * 0.25)

        start_v = Vector(start_loc)
        end_v = Vector(end_loc)
        mid_loc_1 = start_v + 0.46 * (end_v - start_v)
        mid_loc_2 = start_v + 0.54 * (end_v - start_v)

        # Keyframe camera positions with mid-animation pause/slow-drift
        cam_obj.location = start_loc
        cam_obj.keyframe_insert(data_path="location", frame=showcase_start)

        cam_obj.location = mid_loc_1
        cam_obj.keyframe_insert(data_path="location", frame=hold_start)

        cam_obj.location = mid_loc_2
        cam_obj.keyframe_insert(data_path="location", frame=hold_end)

        cam_obj.location = end_loc
        cam_obj.keyframe_insert(data_path="location", frame=showcase_end)

        prev_target = pname
        prev_end_frame = showcase_end
        prev_fstop = fstop

    # 6b. Animate Final Scene - Zoom out to entire Solar System
    final_start = 1380
    final_trans_end = 1420
    final_end = 1500

    # Switch target back to Sun
    keyframe_influence(prev_target, final_trans_end, 1.0)
    keyframe_influence(prev_target, final_trans_end + 1, 0.0)
    
    keyframe_influence("Sun", final_start, 0.0)
    keyframe_influence("Sun", final_trans_end, 1.0)
    keyframe_influence("Sun", final_end, 1.0)

    # Transition f-stop back to 1.8 for wide view
    cam_data.dof.aperture_fstop = prev_fstop
    cam_data.dof.keyframe_insert(data_path="aperture_fstop", frame=final_start)
    cam_data.dof.aperture_fstop = 1.8
    cam_data.dof.keyframe_insert(data_path="aperture_fstop", frame=final_trans_end)
    cam_data.dof.keyframe_insert(data_path="aperture_fstop", frame=final_end)

    # Final overview light energy transition
    if sun_light:
        prev_energy = planet_light_energies.get(prev_target, 80000.0)
        sun_light.energy = prev_energy
        sun_light.keyframe_insert(data_path="energy", frame=final_start)
        
        sun_light.energy = 150000.0  # Dynamic lighting overview energy
        sun_light.keyframe_insert(data_path="energy", frame=final_trans_end)
        sun_light.keyframe_insert(data_path="energy", frame=final_end)

    # Bring orbit lines back for the final overview
    if orbit_mix:
        orbit_mix.inputs[0].keyframe_insert(data_path="default_value", frame=final_start)
        orbit_mix.inputs[0].default_value = 1.0
        orbit_mix.inputs[0].keyframe_insert(data_path="default_value", frame=final_trans_end)
        
        # Smooth interpolation for orbit mix
        if orbit_mix.id_data.animation_data and orbit_mix.id_data.animation_data.action:
            for fcurve in orbit_mix.id_data.animation_data.action.fcurves:
                for kf in fcurve.keyframe_points:
                    kf.interpolation = 'BEZIER'

    # Move camera to a closer wide-angle overview (balances seeing outer planets with keeping inner planets visible)
    cam_obj.location = (0, -80, 50)
    cam_obj.keyframe_insert(data_path="location", frame=final_trans_end)
    
    # Slow cinematic pull-back
    cam_obj.location = (0, -120, 80)
    cam_obj.keyframe_insert(data_path="location", frame=final_end)

    # 7. Smoothing & Polish
    for obj in [cam_pivot, cam_target, cam_obj]:
        if obj.animation_data and obj.animation_data.action:
            for fcurve in obj.animation_data.action.fcurves:
                for kf in fcurve.keyframe_points:
                    kf.interpolation = 'BEZIER'

    # Smooth f-stop transition keyframes on camera data
    if cam_data.animation_data and cam_data.animation_data.action:
        for fcurve in cam_data.animation_data.action.fcurves:
            for kf in fcurve.keyframe_points:
                kf.interpolation = 'BEZIER'

    # Smooth light energy f-curve keyframes
    if sun_light and sun_light.animation_data and sun_light.animation_data.action:
        for fcurve in sun_light.animation_data.action.fcurves:
            for kf in fcurve.keyframe_points:
                kf.interpolation = 'BEZIER'

    # Add slight camera noise for realism
    if cam_obj.animation_data and cam_obj.animation_data.action:
        for fcurve in cam_obj.animation_data.action.fcurves:
            if fcurve.data_path == "location":
                mod = fcurve.modifiers.new(type='NOISE')
                mod.scale = 120.0
                mod.strength = 0.1  # Very subtle shake

    return cam_obj, blocks


# ============================================================
# MAIN
# ============================================================
def main():
    print("=== Solar System Generator – Blender 3.6 ===")

    # 1. Scene
    print("[1/6] Setting up scene...")
    setup_scene()

    # 2. Build solar system objects + materials
    print("[2/6] Building planets and materials...")
    planets = build_solar_system()

    # 2b. Orbit lines
    print("[2b/6] Drawing orbit lines...")
    add_orbit_lines()

    # 3. Animate orbits / rotations
    print("[3/6] Animating orbits and rotations...")
    animate_solar_system(planets)

    # 4. Camera
    print("[4/6] Building camera animation...")
    cam_obj, blocks = build_camera_system(planets)

    # 5. Labels
    print("[5/6] Adding planet labels...")
    add_planet_labels(planets, cam_obj, blocks)

    # 6. Final scene housekeeping
    print("[6/6] Finalising scene...")
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()

    print("=== Done! Press SPACE or render to see the animation. ===")


main()


# ============================================================
# SECTION 9 – EARTH SATELLITE  (ADDITION – does NOT modify above)
# ============================================================
from mathutils import Vector, Matrix


def create_spaceship_materials():
    """Create three textured materials for the spaceship:
    - Base Hull: textured with hull_normal.png
    - Hull Lights: textured with hull_normal.png, hull_lights_diffuse.png, hull_lights_emit.png
    - Engine Exhaust: bright blue emissive glow
    """
    # Load textures
    hull_norm = bpy.data.images.load(tex("hull_normal.png"), check_existing=True)
    lights_diff = bpy.data.images.load(tex("hull_lights_diffuse.png"), check_existing=True)
    lights_emit = bpy.data.images.load(tex("hull_lights_emit.png"), check_existing=True)
    
    # 1. Base Hull Material
    mat_hull = bpy.data.materials.new("Spaceship_Hull")
    mat_hull.use_nodes = True
    nodes = mat_hull.node_tree.nodes
    links = mat_hull.node_tree.links
    nodes.clear()
    
    out = nodes.new("ShaderNodeOutputMaterial")
    bsdf = nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Base Color"].default_value = (0.7, 0.72, 0.75, 1.0)
    bsdf.inputs["Metallic"].default_value = 0.9
    bsdf.inputs["Roughness"].default_value = 0.25
    
    # Texture coordinate & mapping
    coord = nodes.new("ShaderNodeTexCoord")
    
    # Normal Map node
    norm_tex = nodes.new("ShaderNodeTexImage")
    norm_tex.image = hull_norm
    norm_tex.image.colorspace_settings.name = 'Non-Color'
    norm_tex.projection = 'BOX'
    norm_tex.projection_blend = 0.1
    
    norm_map = nodes.new("ShaderNodeNormalMap")
    norm_map.inputs["Strength"].default_value = 1.0
    
    links.new(coord.outputs["Object"], norm_tex.inputs["Vector"])
    links.new(norm_tex.outputs["Color"], norm_map.inputs["Color"])
    links.new(norm_map.outputs["Normal"], bsdf.inputs["Normal"])
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    
    # 2. Hull Lights Material (plated hull with glowing windows)
    mat_lights = bpy.data.materials.new("Spaceship_HullLights")
    mat_lights.use_nodes = True
    nodes_l = mat_lights.node_tree.nodes
    links_l = mat_lights.node_tree.links
    nodes_l.clear()
    
    out_l = nodes_l.new("ShaderNodeOutputMaterial")
    bsdf_l = nodes_l.new("ShaderNodeBsdfPrincipled")
    bsdf_l.inputs["Metallic"].default_value = 0.9
    bsdf_l.inputs["Roughness"].default_value = 0.25
    
    coord_l = nodes_l.new("ShaderNodeTexCoord")
    
    # Normal Map (same as base hull)
    norm_tex_l = nodes_l.new("ShaderNodeTexImage")
    norm_tex_l.image = hull_norm
    norm_tex_l.image.colorspace_settings.name = 'Non-Color'
    norm_tex_l.projection = 'BOX'
    norm_tex_l.projection_blend = 0.1
    
    norm_map_l = nodes_l.new("ShaderNodeNormalMap")
    norm_map_l.inputs["Strength"].default_value = 1.0
    
    links_l.new(coord_l.outputs["Object"], norm_tex_l.inputs["Vector"])
    links_l.new(norm_tex_l.outputs["Color"], norm_map_l.inputs["Color"])
    links_l.new(norm_map_l.outputs["Normal"], bsdf_l.inputs["Normal"])
    
    # Windows diffuse overlay
    diff_tex = nodes_l.new("ShaderNodeTexImage")
    diff_tex.image = lights_diff
    diff_tex.projection = 'BOX'
    diff_tex.projection_blend = 0.1
    
    mix_color = nodes_l.new("ShaderNodeMixRGB")
    mix_color.blend_type = 'MULTIPLY'
    mix_color.inputs["Color1"].default_value = (0.7, 0.72, 0.75, 1.0)
    mix_color.inputs["Fac"].default_value = 0.8
    
    links_l.new(coord_l.outputs["Object"], diff_tex.inputs["Vector"])
    links_l.new(diff_tex.outputs["Color"], mix_color.inputs["Color2"])
    links_l.new(mix_color.outputs["Color"], bsdf_l.inputs["Base Color"])
    
    # Windows emissive map
    emit_tex = nodes_l.new("ShaderNodeTexImage")
    emit_tex.image = lights_emit
    emit_tex.projection = 'BOX'
    emit_tex.projection_blend = 0.1
    
    links_l.new(coord_l.outputs["Object"], emit_tex.inputs["Vector"])
    
    # Emit color & strength
    mix_emit = nodes_l.new("ShaderNodeMixRGB")
    mix_emit.blend_type = 'MULTIPLY'
    mix_emit.inputs["Color1"].default_value = (0.3, 0.8, 1.0, 1.0)
    links_l.new(emit_tex.outputs["Color"], mix_emit.inputs["Color2"])
    links_l.new(mix_emit.outputs["Color"], bsdf_l.inputs["Emission"])
    bsdf_l.inputs["Emission Strength"].default_value = 5.0
    
    links_l.new(bsdf_l.outputs["BSDF"], out_l.inputs["Surface"])
    
    # 3. Engine Glow Material
    mat_glow = bpy.data.materials.new("Spaceship_EngineGlow")
    mat_glow.use_nodes = True
    nodes_g = mat_glow.node_tree.nodes
    links_g = mat_glow.node_tree.links
    nodes_g.clear()
    out_g = nodes_g.new("ShaderNodeOutputMaterial")
    emit_g = nodes_g.new("ShaderNodeEmission")
    emit_g.inputs["Color"].default_value = (0.0, 0.6, 1.0, 1.0)
    emit_g.inputs["Strength"].default_value = 30.0
    links_g.new(emit_g.outputs["Emission"], out_g.inputs["Surface"])
    
    return mat_hull, mat_lights, mat_glow


def generate_procedural_spaceship(name, scale=0.08):
    """Generate a highly detailed procedural spaceship using bmesh,
    modeled with wings, cockpit, engine nozzles, and detailed greebles.
    Uses box-mapped hull texture normal map and light emission maps.
    """
    import bmesh
    import random
    from mathutils import Vector, Matrix

    mesh = bpy.data.meshes.new(name + "_Mesh")
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)

    bm = bmesh.new()

    # 1. Base sleeker rectangular core (longer in Y, wider in X, thin in Z)
    bmesh.ops.create_cube(bm, size=1.0)
    bmesh.ops.scale(bm, vec=Vector((0.6, 2.0, 0.4)) * scale, verts=bm.verts)

    # Base hull material
    for face in bm.faces:
        face.material_index = 0

    # 2. Cockpit / Nose (Extrude +Y forward face)
    for face in list(bm.faces):
        if face.normal.y > 0.9:
            # Extrude forward twice
            f1 = bmesh.ops.extrude_discrete_faces(bm, faces=[face])['faces'][0]
            bmesh.ops.translate(bm, vec=f1.normal * 0.8 * scale, verts=f1.verts)
            # scale down slightly
            pos = f1.calc_center_bounds()
            for v in f1.verts:
                v.co = pos + (v.co - pos) * Vector((0.7, 1.0, 0.5))
            f1.material_index = 1

            f2 = bmesh.ops.extrude_discrete_faces(bm, faces=[f1])['faces'][0]
            bmesh.ops.translate(bm, vec=f2.normal * 0.5 * scale, verts=f2.verts)
            # taper to a point
            pos2 = f2.calc_center_bounds()
            for v in f2.verts:
                v.co = pos2 + (v.co - pos2) * Vector((0.2, 1.0, 0.1))
            f2.material_index = 0

    # 3. Wings (Extrude sides along X axis)
    for face in list(bm.faces):
        # If it's a side face (X normal)
        if abs(face.normal.x) > 0.9 and abs(face.calc_center_bounds().y) < 0.5 * scale:
            side = 1.0 if face.normal.x > 0 else -1.0
            
            # Wing segment 1
            w1 = bmesh.ops.extrude_discrete_faces(bm, faces=[face])['faces'][0]
            bmesh.ops.translate(bm, vec=w1.normal * 1.5 * scale + Vector((0, -0.6 * scale, 0)), verts=w1.verts)
            # Scale thin in Z
            pos = w1.calc_center_bounds()
            for v in w1.verts:
                v.co = pos + (v.co - pos) * Vector((1.0, 0.8, 0.2))
            w1.material_index = 0

            # Wing tip / segment 2 (sweep back)
            w2 = bmesh.ops.extrude_discrete_faces(bm, faces=[w1])['faces'][0]
            bmesh.ops.translate(bm, vec=w2.normal * 0.8 * scale + Vector((0, -0.4 * scale, 0)), verts=w2.verts)
            pos2 = w2.calc_center_bounds()
            for v in w2.verts:
                v.co = pos2 + (v.co - pos2) * Vector((1.0, 0.4, 0.1))
            w2.material_index = 1

    # 4. Engine Mount and dual nozzle cones (rear face -Y)
    for face in list(bm.faces):
        if face.normal.y < -0.9:
            mount = bmesh.ops.extrude_discrete_faces(bm, faces=[face])['faces'][0]
            bmesh.ops.translate(bm, vec=mount.normal * 0.4 * scale, verts=mount.verts)
            pos = mount.calc_center_bounds()
            for v in mount.verts:
                v.co = pos + (v.co - pos) * 0.8
            mount.material_index = 0

            # Create two engines
            for offset in [-0.25, 0.25]:
                engine_pos = pos + Vector((offset * scale, -0.1 * scale, 0))
                engine_mat = Matrix.Translation(engine_pos) @ Matrix.Rotation(math.radians(-90), 4, 'X')
                
                # Outer metal cylinder
                outer_cyl = bmesh.ops.create_cone(
                    bm, cap_ends=True, cap_tris=False, segments=12,
                    radius1=0.18 * scale, radius2=0.22 * scale, depth=0.4 * scale,
                    matrix=engine_mat
                )
                for v in outer_cyl['verts']:
                    for f in v.link_faces:
                        f.material_index = 0

                # Inner glow disc
                glow_pos = engine_pos + Vector((0, -0.21 * scale, 0))
                glow_mat = Matrix.Translation(glow_pos) @ Matrix.Rotation(math.radians(-90), 4, 'X')
                inner_glow = bmesh.ops.create_cone(
                    bm, cap_ends=True, cap_tris=False, segments=10,
                    radius1=0.14 * scale, radius2=0.14 * scale, depth=0.02 * scale,
                    matrix=glow_mat
                )
                for v in inner_glow['verts']:
                    for f in v.link_faces:
                        f.material_index = 2

    # 5. Top fin (extruded along +Z)
    for face in list(bm.faces):
        if face.normal.z > 0.9 and abs(face.calc_center_bounds().y + 0.5 * scale) < 0.3 * scale:
            fin = bmesh.ops.extrude_discrete_faces(bm, faces=[face])['faces'][0]
            bmesh.ops.translate(bm, vec=fin.normal * 0.8 * scale + Vector((0, -0.4 * scale, 0)), verts=fin.verts)
            pos = fin.calc_center_bounds()
            for v in fin.verts:
                v.co = pos + (v.co - pos) * Vector((0.15, 0.6, 1.0))
            fin.material_index = 0

    # 6. Spires / Greebles
    # Add a thin spire on the cockpit
    spire_pos = Vector((0, 1.6 * scale, 0.25 * scale))
    spire_mat = Matrix.Translation(spire_pos) @ Matrix.Rotation(math.radians(15), 4, 'X')
    spire = bmesh.ops.create_cone(
        bm, cap_ends=True, cap_tris=False, segments=6,
        radius1=0.015 * scale, radius2=0.0, depth=0.6 * scale,
        matrix=spire_mat
    )
    for v in spire['verts']:
        for f in v.link_faces:
            f.material_index = 1

    bm.to_mesh(mesh)
    bm.free()

    # Recenter origin
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.origin_set(type='ORIGIN_CENTER_OF_MASS')

    # Bevel modifier for panel lines
    bevel = obj.modifiers.new(name="Bevel", type='BEVEL')
    bevel.width = 0.005 * scale
    bevel.segments = 2

    # Load and assign materials
    mat_hull, mat_lights, mat_glow = create_spaceship_materials()
    obj.data.materials.append(mat_hull)       # Index 0
    obj.data.materials.append(mat_lights)     # Index 1
    obj.data.materials.append(mat_glow)       # Index 2

    return obj


def add_earth_satellite():
    """Add a detailed satellite with solar panels orbiting Earth."""
    earth = bpy.data.objects.get("Earth")
    if not earth:
        print("  [!] Earth not found – skipping satellite")
        return

    earth_r = 0.30  # from PLANET_DATA

    # ---- Orbit pivot (inclined, parented to Earth) ----
    sat_orbit = create_empty("Satellite_Orbit")
    sat_orbit.parent = earth

    # ---- Generate Procedural Satellite ----
    body = generate_procedural_spaceship("Satellite", scale=0.03)

    # ---- Position & parent ----
    sat_orbit_r = earth_r * 2.5  # close enough to be clearly visible on camera
    body.location = (sat_orbit_r, 0, 0.05)
    body.parent = sat_orbit

    # ---- Animate inclined orbit (slower) ----
    sat_orbit.rotation_euler = (math.radians(40), math.radians(15), 0)
    sat_orbit.keyframe_insert(data_path="rotation_euler", frame=1)
    sat_orbit.rotation_euler = (math.radians(40), math.radians(15),
                                math.radians(360 * 5))
    sat_orbit.keyframe_insert(data_path="rotation_euler", frame=FRAME_END)
    for fc in sat_orbit.animation_data.action.fcurves:
        for kf in fc.keyframe_points:
            kf.interpolation = 'LINEAR'

    # ---- Blinking navigation light ----
    bpy.ops.object.light_add(type='POINT', location=(0, 0, 0.02))
    nav = bpy.context.active_object
    nav.name = "Sat_NavLight"
    nav.parent = body
    nav.data.color = (1.0, 0.15, 0.1)
    nav.data.shadow_soft_size = 0.005
    nav.data.use_shadow = False
    nav.data.energy = 3.0

    for f in range(FRAME_START, FRAME_END + 1, 20):
        nav.data.energy = 6.0
        nav.data.keyframe_insert(data_path="energy", frame=f)
        nav.data.energy = 0.0
        nav.data.keyframe_insert(data_path="energy", frame=f + 3)
        nav.data.keyframe_insert(data_path="energy", frame=f + 17)

    if nav.data.animation_data and nav.data.animation_data.action:
        for fc in nav.data.animation_data.action.fcurves:
            for kf in fc.keyframe_points:
                kf.interpolation = 'CONSTANT'

    print("  [+] Satellite added to Earth orbit")


# ============================================================
# SECTION 10 – COMETS  (ADDITION)
# ============================================================
def create_comet(name, parent_obj, start_pos, end_pos,
                 start_frame, end_frame,
                 head_radius=0.3, tail_length=4.0,
                 color=(0.5, 0.7, 1.0, 1)):
    """Create an improved comet with:
    - Irregular asteroid nucleus (deformed icosphere)
    - Glowing fresnel gas coma halo
    - Double tails (thin blue ion tail, wider warm dust tail)
    - Debris particles trailing along the tail
    - Point light for local illumination
    """
    import random
    from mathutils import Vector, Quaternion

    travel_dir = Vector(end_pos) - Vector(start_pos)
    tail_dir = -travel_dir.normalized()  # tail points opposite travel

    # 1. Nucleus (deformed icosphere)
    bpy.ops.mesh.primitive_ico_sphere_add(
        radius=head_radius, subdivisions=3, location=(0, 0, 0))
    head = bpy.context.active_object
    head.name = f"Comet_{name}"
    
    # Deform vertices of the nucleus to make it look like a craggy rock
    mesh = head.data
    for vert in mesh.vertices:
        noise = 1.0 + random.uniform(-0.16, 0.16)
        vert.co *= noise
    bpy.ops.object.shade_smooth()
    
    if parent_obj:
        head.parent = parent_obj

    # Nucleus material - dark rock
    n_mat = bpy.data.materials.new(f"Comet_{name}_Nucleus_Mat")
    n_mat.use_nodes = True
    nn = n_mat.node_tree.nodes
    nl = n_mat.node_tree.links
    nn.clear()
    n_out = nn.new("ShaderNodeOutputMaterial")
    n_bsdf = nn.new("ShaderNodeBsdfPrincipled")
    n_bsdf.inputs["Base Color"].default_value = (0.15, 0.15, 0.15, 1)
    n_bsdf.inputs["Roughness"].default_value = 0.95
    n_bsdf.inputs["Metallic"].default_value = 0.0
    nl.new(n_bsdf.outputs["BSDF"], n_out.inputs["Surface"])
    assign_material(head, n_mat)

    # 2. Coma (surrounding gas halo)
    bpy.ops.mesh.primitive_ico_sphere_add(
        radius=head_radius * 1.6, subdivisions=2, location=(0, 0, 0))
    coma = bpy.context.active_object
    coma.name = f"CometComa_{name}"
    coma.parent = head
    bpy.ops.object.shade_smooth()

    # Coma material - fresnel transparent soft glow
    coma_mat = bpy.data.materials.new(f"CometComa_{name}_Mat")
    coma_mat.use_nodes = True
    coma_mat.blend_method = "BLEND"
    coma_mat.shadow_method = "NONE"
    cn = coma_mat.node_tree.nodes; cl = coma_mat.node_tree.links
    cn.clear()
    c_out = cn.new("ShaderNodeOutputMaterial")
    c_trans = cn.new("ShaderNodeBsdfTransparent")
    c_emit = cn.new("ShaderNodeEmission")
    c_emit.inputs["Color"].default_value = color
    c_emit.inputs["Strength"].default_value = 6.0
    c_mix = cn.new("ShaderNodeMixShader")
    c_lw = cn.new("ShaderNodeLayerWeight")
    c_lw.inputs["Blend"].default_value = 0.25
    cl.new(c_lw.outputs["Facing"], c_mix.inputs["Fac"])
    cl.new(c_trans.outputs["BSDF"], c_mix.inputs[1])
    cl.new(c_emit.outputs["Emission"], c_mix.inputs[2])
    cl.new(c_mix.outputs["Shader"], c_out.inputs["Surface"])
    assign_material(coma, coma_mat)

    # 3. Point light on head for volumetric glow
    bpy.ops.object.light_add(type='POINT', location=(0, 0, 0))
    c_light = bpy.context.active_object
    c_light.name = f"Comet_{name}_Light"
    c_light.parent = head
    c_light.data.energy = 800
    c_light.data.color = color[:3]
    c_light.data.shadow_soft_size = head_radius * 2
    c_light.data.use_shadow = False
    c_light.data.use_custom_distance = True
    c_light.data.cutoff_distance = tail_length * 4

    # 4. Ion Tail (thin, straight blue cone)
    bpy.ops.mesh.primitive_cone_add(
        radius1=head_radius * 0.6, radius2=0.0,
        depth=tail_length, vertices=32, location=(0, 0, 0))
    ion_tail = bpy.context.active_object
    ion_tail.name = f"CometIonTail_{name}"
    bpy.ops.object.shade_smooth()
    ion_tail.parent = head

    # Orient ion tail
    rot_quat = tail_dir.to_track_quat('Z', 'Y')
    ion_tail.rotation_euler = rot_quat.to_euler()
    ion_offset = rot_quat @ Vector((0, 0, tail_length / 2))
    ion_tail.location = ion_offset

    # Ion Tail Material - blue glow gradient
    ion_mat = bpy.data.materials.new(f"CometIonTail_{name}_Mat")
    ion_mat.use_nodes = True
    ion_mat.blend_method = "BLEND"
    ion_mat.shadow_method = "NONE"
    in_nodes = ion_mat.node_tree.nodes; in_links = ion_mat.node_tree.links
    in_nodes.clear()
    
    i_out = in_nodes.new("ShaderNodeOutputMaterial")
    i_emit = in_nodes.new("ShaderNodeEmission")
    i_emit.inputs["Color"].default_value = (0.2, 0.65, 1.0, 1.0)
    i_emit.inputs["Strength"].default_value = 25.0
    
    i_trans = in_nodes.new("ShaderNodeBsdfTransparent")
    i_mix = in_nodes.new("ShaderNodeMixShader")
    i_coord = in_nodes.new("ShaderNodeTexCoord")
    i_sep = in_nodes.new("ShaderNodeSeparateXYZ")
    
    in_links.new(i_coord.outputs["Generated"], i_sep.inputs["Vector"])
    in_links.new(i_sep.outputs["Z"], i_mix.inputs["Fac"])
    in_links.new(i_emit.outputs["Emission"], i_mix.inputs[1])
    in_links.new(i_trans.outputs["BSDF"], i_mix.inputs[2])
    in_links.new(i_mix.outputs["Shader"], i_out.inputs["Surface"])
    assign_material(ion_tail, ion_mat)

    # 5. Dust Tail (wider, slightly curved yellow-white cone)
    dust_len = tail_length * 0.85
    bpy.ops.mesh.primitive_cone_add(
        radius1=head_radius * 1.0, radius2=0.0,
        depth=dust_len, vertices=32, location=(0, 0, 0))
    dust_tail = bpy.context.active_object
    dust_tail.name = f"CometDustTail_{name}"
    bpy.ops.object.shade_smooth()
    dust_tail.parent = head

    # Orient dust tail offset by ~10 degrees
    perp = tail_dir.cross(Vector((0, 0, 1)))
    if perp.length < 0.1:
        perp = tail_dir.cross(Vector((0, 1, 0)))
    perp.normalize()
    
    dust_rot_quat = rot_quat @ Quaternion(perp, math.radians(10))
    dust_tail.rotation_euler = dust_rot_quat.to_euler()
    dust_offset = dust_rot_quat @ Vector((0, 0, dust_len / 2))
    dust_tail.location = dust_offset

    # Dust Tail Material - warm yellow-white gradient
    dust_mat = bpy.data.materials.new(f"CometDustTail_{name}_Mat")
    dust_mat.use_nodes = True
    dust_mat.blend_method = "BLEND"
    dust_mat.shadow_method = "NONE"
    dn_nodes = dust_mat.node_tree.nodes; dn_links = dust_mat.node_tree.links
    dn_nodes.clear()
    
    d_out = dn_nodes.new("ShaderNodeOutputMaterial")
    d_emit = dn_nodes.new("ShaderNodeEmission")
    d_emit.inputs["Color"].default_value = (1.0, 0.88, 0.65, 1.0)
    d_emit.inputs["Strength"].default_value = 15.0
    
    d_trans = dn_nodes.new("ShaderNodeBsdfTransparent")
    d_mix = dn_nodes.new("ShaderNodeMixShader")
    d_coord = dn_nodes.new("ShaderNodeTexCoord")
    d_sep = dn_nodes.new("ShaderNodeSeparateXYZ")
    
    dn_links.new(d_coord.outputs["Generated"], d_sep.inputs["Vector"])
    dn_links.new(d_sep.outputs["Z"], d_mix.inputs["Fac"])
    dn_links.new(d_emit.outputs["Emission"], d_mix.inputs[1])
    dn_links.new(d_trans.outputs["BSDF"], d_mix.inputs[2])
    dn_links.new(d_mix.outputs["Shader"], d_out.inputs["Surface"])
    assign_material(dust_tail, dust_mat)

    # 6. Debris particles trailing along dust tail
    debris_list = []
    for p_idx in range(5):
        p_radius = head_radius * random.uniform(0.08, 0.22)
        dist = dust_len * random.uniform(0.1, 0.7)
        disp = Vector((random.uniform(-0.15, 0.15), random.uniform(-0.15, 0.15), random.uniform(-0.15, 0.15))) * dist * 0.2
        p_pos = dust_offset + (dust_rot_quat @ Vector((0, 0, dist - dust_len / 2))) + disp
        
        bpy.ops.mesh.primitive_ico_sphere_add(
            radius=p_radius, subdivisions=1, location=p_pos)
        part = bpy.context.active_object
        part.name = f"Comet_{name}_Part_{p_idx}"
        part.parent = head
        
        for pv in part.data.vertices:
            pv.co *= random.uniform(0.7, 1.3)
        bpy.ops.object.shade_smooth()
        assign_material(part, n_mat)
        debris_list.append(part)

    # Collect all sub-objects for keyframing
    comet_parts = [head, coma, ion_tail, dust_tail, c_light] + debris_list

    # ---- Visibility keyframes ----
    for obj in comet_parts:
        obj.hide_render = True;  obj.hide_viewport = True
        obj.keyframe_insert(data_path="hide_render",   frame=1)
        obj.keyframe_insert(data_path="hide_viewport",  frame=1)
        if start_frame > 2:
            obj.keyframe_insert(data_path="hide_render",  frame=start_frame - 1)
            obj.keyframe_insert(data_path="hide_viewport", frame=start_frame - 1)

        obj.hide_render = False; obj.hide_viewport = False
        obj.keyframe_insert(data_path="hide_render",   frame=start_frame)
        obj.keyframe_insert(data_path="hide_viewport",  frame=start_frame)

    # Position
    head.location = start_pos
    head.keyframe_insert(data_path="location", frame=start_frame)
    head.location = end_pos
    head.keyframe_insert(data_path="location", frame=end_frame)

    for obj in comet_parts:
        obj.hide_render = True;  obj.hide_viewport = True
        obj.keyframe_insert(data_path="hide_render",   frame=end_frame + 1)
        obj.keyframe_insert(data_path="hide_viewport",  frame=end_frame + 1)

    # Interpolation
    for obj in comet_parts:
        if obj.animation_data and obj.animation_data.action:
            for fc in obj.animation_data.action.fcurves:
                if fc.data_path in ("hide_render", "hide_viewport"):
                    for kf in fc.keyframe_points:
                        kf.interpolation = 'CONSTANT'
                elif fc.data_path == "location":
                    for kf in fc.keyframe_points:
                        kf.interpolation = 'LINEAR'

    print(f"  [+] Comet '{name}' added (frames {start_frame}–{end_frame})")
    return head


# ============================================================
# SECTION 11 – SHOOTING STARS  (ADDITION)
# ============================================================
def create_shooting_star(name, parent_obj, start_pos, end_pos,
                         start_frame, end_frame,
                         streak_length=1.5, streak_radius=0.015,
                         color=(1.0, 0.95, 0.8, 1)):
    """Fast bright streak with a fading trail cone."""
    travel_dir = Vector(end_pos) - Vector(start_pos)
    travel_norm = travel_dir.normalized()

    # ---- Streak body (cylinder) ----
    bpy.ops.mesh.primitive_cylinder_add(
        radius=streak_radius, depth=streak_length,
        vertices=12, location=(0, 0, 0))
    streak = bpy.context.active_object
    streak.name = f"ShootingStar_{name}"
    bpy.ops.object.shade_smooth()
    if parent_obj:
        streak.parent = parent_obj

    # Orient cylinder +Z along travel direction
    rot_quat = travel_norm.to_track_quat('Z', 'Y')
    streak.rotation_euler = rot_quat.to_euler()

    # Streak material – very bright emission
    s_mat = bpy.data.materials.new(f"ShootingStar_{name}_Mat")
    s_mat.use_nodes = True
    sn = s_mat.node_tree.nodes; sl = s_mat.node_tree.links
    sn.clear()
    s_out  = sn.new("ShaderNodeOutputMaterial"); s_out.location  = (400, 0)
    s_emit = sn.new("ShaderNodeEmission");       s_emit.location = (100, 0)
    s_emit.inputs["Color"].default_value    = color
    s_emit.inputs["Strength"].default_value = 50.0
    sl.new(s_emit.outputs["Emission"], s_out.inputs["Surface"])
    assign_material(streak, s_mat)

    # ---- Trail cone (fades behind the streak) ----
    trail_len = streak_length * 2.5
    bpy.ops.mesh.primitive_cone_add(
        radius1=streak_radius * 3, radius2=0.0,
        depth=trail_len, vertices=16, location=(0, 0, 0))
    trail = bpy.context.active_object
    trail.name = f"ShootingStarTrail_{name}"
    bpy.ops.object.shade_smooth()
    trail.parent = streak

    # In streak local space +Z = forward (travel).
    # Flip cone 180° so fat base is at streak rear, pointy tip trails behind.
    trail.rotation_euler = (math.radians(180), 0, 0)
    trail.location = (0, 0, -(streak_length / 2 + trail_len / 2))

    # Trail material – gradient fade (Generated Z: 0=base→emit, 1=tip→transparent)
    tr_mat = bpy.data.materials.new(f"ShootingStarTrail_{name}_Mat")
    tr_mat.use_nodes = True
    tr_mat.blend_method = "BLEND"
    tr_mat.shadow_method = "NONE"
    trn = tr_mat.node_tree.nodes; trl = tr_mat.node_tree.links
    trn.clear()

    tr_out   = trn.new("ShaderNodeOutputMaterial"); tr_out.location   = (600, 0)
    tr_emit  = trn.new("ShaderNodeEmission");       tr_emit.location  = (200, -80)
    tr_emit.inputs["Color"].default_value    = color
    tr_emit.inputs["Strength"].default_value = 25.0

    tr_trans = trn.new("ShaderNodeBsdfTransparent"); tr_trans.location = (200, 80)
    tr_mix   = trn.new("ShaderNodeMixShader");       tr_mix.location   = (400, 0)

    tr_coord = trn.new("ShaderNodeTexCoord");    tr_coord.location = (-100, -80)
    tr_sep   = trn.new("ShaderNodeSeparateXYZ"); tr_sep.location   = (50, -80)

    trl.new(tr_coord.outputs["Generated"], tr_sep.inputs["Vector"])
    trl.new(tr_sep.outputs["Z"],           tr_mix.inputs["Fac"])
    trl.new(tr_emit.outputs["Emission"],   tr_mix.inputs[1])
    trl.new(tr_trans.outputs["BSDF"],      tr_mix.inputs[2])
    trl.new(tr_mix.outputs["Shader"],      tr_out.inputs["Surface"])
    assign_material(trail, tr_mat)

    # ---- Visibility & position keyframes ----
    streak.hide_render = True;  streak.hide_viewport = True
    streak.keyframe_insert(data_path="hide_render",   frame=1)
    streak.keyframe_insert(data_path="hide_viewport",  frame=1)
    if start_frame > 2:
        streak.keyframe_insert(data_path="hide_render",  frame=start_frame - 1)
        streak.keyframe_insert(data_path="hide_viewport", frame=start_frame - 1)

    streak.hide_render = False; streak.hide_viewport = False
    streak.keyframe_insert(data_path="hide_render",   frame=start_frame)
    streak.keyframe_insert(data_path="hide_viewport",  frame=start_frame)

    streak.location = start_pos
    streak.keyframe_insert(data_path="location", frame=start_frame)
    streak.location = end_pos
    streak.keyframe_insert(data_path="location", frame=end_frame)

    streak.hide_render = True;  streak.hide_viewport = True
    streak.keyframe_insert(data_path="hide_render",   frame=end_frame + 1)
    streak.keyframe_insert(data_path="hide_viewport",  frame=end_frame + 1)

    if streak.animation_data and streak.animation_data.action:
        for fc in streak.animation_data.action.fcurves:
            if fc.data_path in ("hide_render", "hide_viewport"):
                for kf in fc.keyframe_points:
                    kf.interpolation = 'CONSTANT'
            elif fc.data_path == "location":
                for kf in fc.keyframe_points:
                    kf.interpolation = 'LINEAR'

    print(f"  [+] Shooting star '{name}' added (frames {start_frame}–{end_frame})")
    return streak


# ============================================================
# SECTION 12 – EXECUTE SPACE EFFECTS  (ADDITION)
# ============================================================
def add_space_effects():
    """Wire up satellite, comets, and shooting stars across the animation."""

    print("\n=== Adding Space Effects ===")

    # -----------------------------------------------------------
    # 1.  EARTH SATELLITE
    # -----------------------------------------------------------
    add_earth_satellite()

    # -----------------------------------------------------------
    # 2.  COMETS
    #     Each comet is parented to an "anchor" empty that sits at
    #     the planet's orbital position inside its pivot, so it
    #     tracks correctly with the camera system.
    # -----------------------------------------------------------

    # Comet A – sweeps across during the OVERVIEW (frames 80-200)
    #   No parent (world-space). Camera is at ~(-60,-140,100)→(50,-80,60)
    #   looking at the Sun. Comet flies through middle ground.
    create_comet(
        "Overview", None,
        start_pos=(35, -55, 35),
        end_pos=(-28, 22, 5),
        start_frame=80, end_frame=200,
        head_radius=0.2, tail_length=3.0,
        color=(0.65, 0.82, 1.0, 1))

    # Comet B – near Jupiter (showcase 780-900)
    jup_pivot = bpy.data.objects.get("Jupiter_Pivot")
    if jup_pivot:
        jup_orbit_r = 55
        jup_r = 3.36
        jup_anchor = create_empty("CometAnchor_Jupiter")
        jup_anchor.parent = jup_pivot
        jup_anchor.location = (jup_orbit_r, 0, 0)

        create_comet(
            "Halley", jup_anchor,
            start_pos=(-jup_r * 4, jup_r * 5, jup_r * 4),
            end_pos=(jup_r * 6, -jup_r * 3, -jup_r * 2),
            start_frame=790, end_frame=890,
            head_radius=max(jup_r * 0.05, 0.06),
            tail_length=max(jup_r * 1.2, 1.5),
            color=(0.5, 0.75, 1.0, 1))

    # Comet C – near Neptune (showcase 1140-1260)
    nep_pivot = bpy.data.objects.get("Neptune_Pivot")
    if nep_pivot:
        nep_orbit_r = 125
        nep_r = 1.16
        nep_anchor_c = create_empty("CometAnchor_Neptune")
        nep_anchor_c.parent = nep_pivot
        nep_anchor_c.location = (nep_orbit_r, 0, 0)

        create_comet(
            "Hale_Bopp", nep_anchor_c,
            start_pos=(-nep_r * 4, nep_r * 5, nep_r * 4),
            end_pos=(nep_r * 6, -nep_r * 3, -nep_r * 2),
            start_frame=1155, end_frame=1250,
            head_radius=max(nep_r * 0.05, 0.06),
            tail_length=max(nep_r * 1.2, 1.5),
            color=(0.6, 0.8, 0.95, 1))

    # -----------------------------------------------------------
    # 3.  PLANET COMETS
    #     Unified comets replace basic shooting stars across
    #     all other planet showcases.
    # -----------------------------------------------------------

    # Helper: create an anchor at a planet's orbital position
    def planet_anchor(planet_name, orbit_r, suffix="Comet"):
        pivot = bpy.data.objects.get(f"{planet_name}_Pivot")
        if not pivot:
            return None
        a = create_empty(f"{suffix}Anchor_{planet_name}")
        a.parent = pivot
        a.location = (orbit_r, 0, 0)
        return a

    # Mercury (showcase 300-420, prad 0.11, orbit 12)
    merc_a = planet_anchor("Mercury", 12)
    if merc_a:
        s = 0.11
        create_comet(
            "Mercury_1", merc_a,
            start_pos=(-s * 18, s * 20, s * 15),
            end_pos=(s * 22, -s * 18, -s * 12),
            start_frame=340, end_frame=415,
            head_radius=s * 0.4,
            tail_length=s * 3.0,
            color=(1.0, 0.9, 0.65, 1))

    # Venus (showcase 420-540, prad 0.28, orbit 18)
    ven_a = planet_anchor("Venus", 18)
    if ven_a:
        s = 0.28
        create_comet(
            "Venus_1", ven_a,
            start_pos=(s * 18, -s * 20, -s * 15),
            end_pos=(-s * 22, s * 18, s * 12),
            start_frame=450, end_frame=530,
            head_radius=s * 0.4,
            tail_length=s * 3.0,
            color=(1.0, 0.85, 0.6, 1))

    # Mars (showcase 660-780, prad 0.16, orbit 34)
    mars_a = planet_anchor("Mars", 34)
    if mars_a:
        s = 0.16
        create_comet(
            "Mars_1", mars_a,
            start_pos=(-s * 18, -s * 20, s * 15),
            end_pos=(s * 22, s * 18, -s * 12),
            start_frame=680, end_frame=755,
            head_radius=s * 0.4,
            tail_length=s * 3.0,
            color=(1.0, 0.75, 0.45, 1))

        create_comet(
            "Mars_2", mars_a,
            start_pos=(s * 20, s * 18, -s * 15),
            end_pos=(-s * 22, -s * 16, s * 12),
            start_frame=758, end_frame=775,
            head_radius=s * 0.4,
            tail_length=s * 3.0,
            color=(1.0, 0.92, 0.75, 1))

    # Saturn (showcase 900-1020, prad 2.83, orbit 80)
    sat_a = planet_anchor("Saturn", 80)
    if sat_a:
        s = 2.83
        create_comet(
            "Saturn_1", sat_a,
            start_pos=(s * 14, -s * 16, -s * 12),
            end_pos=(-s * 16, s * 14, s * 10),
            start_frame=920, end_frame=1010,
            head_radius=s * 0.4,
            tail_length=s * 3.0,
            color=(1.0, 0.9, 0.7, 1))

    # Uranus (showcase 1020-1140, prad 1.20, orbit 105)
    ura_a = planet_anchor("Uranus", 105)
    if ura_a:
        s = 1.20
        create_comet(
            "Uranus_1", ura_a,
            start_pos=(-s * 14, -s * 16, s * 12),
            end_pos=(s * 16, s * 14, -s * 10),
            start_frame=1040, end_frame=1120,
            head_radius=s * 0.4,
            tail_length=s * 3.0,
            color=(0.7, 0.95, 1.0, 1))

        create_comet(
            "Uranus_2", ura_a,
            start_pos=(s * 16, s * 14, -s * 12),
            end_pos=(-s * 18, -s * 12, s * 10),
            start_frame=1123, end_frame=1135,
            head_radius=s * 0.4,
            tail_length=s * 3.0,
            color=(0.8, 0.9, 1.0, 1))

    # Pluto (showcase 1260-1380, prad 0.05, orbit 150)
    plu_a = planet_anchor("Pluto", 150)
    if plu_a:
        s = 0.05
        create_comet(
            "Pluto_1", plu_a,
            start_pos=(s * 18, -s * 20, s * 15),
            end_pos=(-s * 22, s * 18, -s * 12),
            start_frame=1280, end_frame=1370,
            head_radius=s * 0.4,
            tail_length=s * 3.0,
            color=(0.85, 0.8, 0.95, 1))

    # Reset frame
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()

    print("=== Space Effects Complete ===\n")


# Run!
add_space_effects()
