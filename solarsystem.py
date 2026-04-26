import bpy
import math
import os

# ============================================================
# CONFIGURATION
# ============================================================
TEXTURE_DIR = r"C:\solar_system"
RENDER_ENGINE = "BLENDER_EEVEE"   # or "CYCLES"
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
        bsdf.inputs["Emission Color"].default_value    = (*emission_color, 1)
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
    ("Mercury", 0.11,  12,   88,   58,  0.03,  (0.6, 0.5, 0.45, 1), "mercury_color.jpg"),
    ("Venus",   0.28,  18,  225,  243,  177.4, (0.9, 0.8, 0.5,  1), "venus_surface.jpg"),
    ("Earth",   0.30,  25,  365,    1,   23.4, (0.2, 0.5, 0.9,  1), "earth_daymap.jpg"),
    ("Mars",    0.16,  34,  687,   1.03, 25.2, (0.8, 0.4, 0.2,  1), "mars_surface.jpg"),
    ("Jupiter", 3.36,  55,  433,   0.41, 3.1,  (0.8, 0.7, 0.55, 1), "jupiter_map.jpg"),
    ("Saturn",  2.83,  80,  107,   0.45, 26.7, (0.9, 0.85, 0.6, 1), "saturn_color.jpg"),
    ("Uranus",  1.20, 105,  840,   0.72, 97.8, (0.5, 0.85, 0.9, 1), "uranus.jpg"),
    ("Neptune", 1.16, 125, 1640,   0.67, 28.3, (0.2, 0.4, 0.9,  1), "neptune_surface.jpg"),
    ("Pluto",   0.05, 150, 2480,   6.39, 122.5, (0.6, 0.5, 0.4,  1), "pluto_map.jpg"),
]

SUN_RADIUS = 8.0

# Map frame period → animation speed factor (so orbits fit in 1500 frames nicely)
SPEED_SCALE = 0.025   # multiply real periods by this to get animation degrees/frame


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

    # Sun point light - reduced energy to avoid washing out planets
    sun_light = add_point_light("SunLight", (0, 0, 0), energy=80000,
                                radius=SUN_RADIUS, color=(1.0, 0.95, 0.8))

    # FIX 2: Disable shadows on the point light.
    sun_light.data.use_shadow = False

    # FIX 3: Extend light cutoff so outer planets (Pluto r=150) stay lit.
    sun_light.data.use_custom_distance = True
    sun_light.data.cutoff_distance     = 600.0

    # Ambient fill light using a SUN lamp to evenly light the dark sides of all planets everywhere
    bpy.ops.object.light_add(type='SUN', rotation=(math.radians(45), math.radians(45), 0))
    fill = bpy.context.active_object
    fill.name = "AmbientFill"
    fill.data.energy = 0.2  # Sun lamps use low energy values
    fill.data.color = (0.3, 0.35, 0.5)
    fill.data.use_shadow = False
    
    bpy.ops.object.light_add(type='SUN', rotation=(math.radians(-45), math.radians(-135), 0))
    fill2 = bpy.context.active_object
    fill2.name = "AmbientFill2"
    fill2.data.energy = 0.1
    fill2.data.color = (0.25, 0.3, 0.45)
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
    links.new(emit.outputs["Emission"], out.inputs["Surface"])

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
        orbit_r = planets[pname]["orbit_r"]

        # Position at the planet's orbit radius plus an offset
        bpy.ops.object.text_add(location=(orbit_r + prad * 1.5, 0, prad * 1.2))
        txt_obj = bpy.context.active_object
        txt_obj.name = f"Label_{pname}"
        txt_obj.data.body = pname
        txt_obj.data.size = max(0.2, prad * 0.4)
        txt_obj.data.align_x = 'CENTER'

        # Parent to the pivot instead of the planet
        # This makes it follow the orbit but NOT spin wildly with the planet's day/night cycle!
        txt_obj.parent = pivot

        # Track To constraint so it faces camera
        c = txt_obj.constraints.new(type='TRACK_TO')
        c.target = cam_obj
        c.track_axis = 'TRACK_Z'
        c.up_axis = 'UP_Y'

        # Material with animated transparency
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
        lemit.inputs["Color"].default_value = (1, 1, 1, 1)
        lemit.inputs["Strength"].default_value = 2.0

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

    # Animate visibility based on camera segments
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

        # Apply bezier interpolation for smooth fade
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
    cam_data.lens = 24  # Wider lens so we can get physically closer
    cam_data.clip_start = 0.01
    cam_data.clip_end = 2000
    cam_data.dof.use_dof = True
    cam_data.dof.focus_object = cam_target
    cam_data.dof.aperture_fstop = 2.8

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

    # 4. Animate Scene 1 – Overview
    keyframe_influence("Sun", 1, 1.0)
    for pname in PLANET_DATA:
        keyframe_influence(pname[0], 1, 0.0)

    # Overview Camera Motion (start extremely close but with wide lens, slight zoom/orbit)
    cam_obj.location = (0, -140, 100)
    cam_obj.keyframe_insert(data_path="location", frame=1)

    cam_obj.location = (50, -80, 60)
    cam_obj.keyframe_insert(data_path="location", frame=240)

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

        # Local camera position (offset from planet)
        start_loc = (0, -prad * 8, prad * 3)
        cam_obj.location = start_loc
        cam_obj.keyframe_insert(data_path="location", frame=showcase_start)

        # Slight orbit and push-in during showcase
        end_loc = (prad * 5, -prad * 6, prad * 4)
        cam_obj.location = end_loc
        cam_obj.keyframe_insert(data_path="location", frame=showcase_end)

        prev_target = pname
        prev_end_frame = showcase_end

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

    # Add slight camera noise for realism
    if cam_obj.animation_data and cam_obj.animation_data.action:
        for fcurve in cam_obj.animation_data.action.fcurves:
            if fcurve.data_path == "location":
                mod = fcurve.modifiers.new(type='NOISE')
                mod.scale = 80.0
                mod.strength = 0.2

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
