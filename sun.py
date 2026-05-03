import bpy
import os
import math
from mathutils import Vector

# ==============================================================================
# GLOBAL CONFIGURATION
# ==============================================================================

# Directory containing all the planet textures
TEXTURE_DIR = r"C:\solar_system"

# Scale factor for physical sizing (1 Blender Unit = 100,000 km)
# For the Sun, radius is approx 696,000 km -> we use 6.96 units
SUN_RADIUS = 6.96

# Animation timeline configuration
TOTAL_FRAMES = 720
ROTATION_RATIO = 1.0 # 1 rotation over 720 frames

# Future scalability: Texture map dictionary for all 9 planets & moons
PLANET_TEXTURES = {
    "Sun": {"surface": "sun_surface.jpg", "map": "sunmap.jpg"},
    "Mercury": {"color": "mercury_color.jpg", "surface": "mercury_surface.jpg", "bump": "mercury_bump.jpg"},
    "Venus": {"surface": "venus_surface.jpg", "clouds": "venus_clouds.jpg"},
    "Earth": {"day": "earth_daymap.jpg", "night": "earth_nightmap.jpg", "normal": "earth_normal.jpg", "bump": "earth_bump.jpg", "specular": "earth_specular.jpg"},
    "Mars": {"surface": "mars_surface.jpg", "normal": "mars_normal.jpg", "bump": "mars_bump.jpg"},
    "Jupiter": {"map": "jupiter_map.jpg"},
    "Saturn": {"map": "saturn_map.jpg", "rings": "saturn_rings.png"},
    "Uranus": {"map": "uranus_map.jpg", "rings": "uranus_rings.png"},
    "Neptune": {"map": "neptune_map.jpg"},
    "Pluto": {"map": "pluto_map.jpg", "bump": "pluto_bump.jpg"},
    "Moon": {"surface": "moon_surface.jpg", "bump": "moon_bump.jpg"}
}

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def get_texture_path(filename):
    """Returns the absolute path to a texture file."""
    path = os.path.join(TEXTURE_DIR, filename)
    if not os.path.exists(path):
        print(f"Warning: Texture '{filename}' not found in {TEXTURE_DIR}.")
    return path

def clear_scene():
    """Removes all objects, meshes, materials, and worlds from the current scene."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    
    # Purge orphaned data
    for block in [bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.lights, bpy.data.cameras]:
        for item in block:
            block.remove(item)

def setup_collections():
    """Sets up the required collections for organization."""
    collections = ["Sun", "Planets", "Environment"]
    
    # Ensure scene collection is active
    scene_collection = bpy.context.scene.collection
    
    for name in collections:
        if name not in bpy.data.collections:
            new_col = bpy.data.collections.new(name)
            scene_collection.children.link(new_col)

def link_to_collection(obj, collection_name):
    """Links an object to a specific collection and unlinks from the master scene collection."""
    if collection_name in bpy.data.collections:
        bpy.data.collections[collection_name].objects.link(obj)
        if obj.name in bpy.context.scene.collection.objects:
            bpy.context.scene.collection.objects.unlink(obj)

# ==============================================================================
# RENDERING & WORLD
# ==============================================================================

def setup_rendering():
    """Configures the render engine to Eevee for lightning-fast real-time rendering."""
    scene = bpy.context.scene
    
    # Use Eevee for fast rendering
    scene.render.engine = 'BLENDER_EEVEE'
    scene.eevee.taa_render_samples = 64
    
    # Native Eevee Bloom (no compositor needed)
    scene.eevee.use_bloom = True
    scene.eevee.bloom_threshold = 1.0  # Adjust so only the hot spots glow
    scene.eevee.bloom_intensity = 0.05 # Realistic, subtle glow
    scene.eevee.bloom_radius = 6.0
    
    # High contrast look (NASA VTAD style)
    scene.view_settings.look = 'High Contrast'
    scene.view_settings.view_transform = 'Filmic' # Blender 3.6 uses Filmic instead of AgX
    
    # Disable compositor since Eevee handles Bloom natively
    scene.use_nodes = False

def setup_world():
    """Sets up the environment background with high-res stars."""
    world = bpy.data.worlds.new("Space_World")
    bpy.context.scene.world = world
    world.use_nodes = True
    
    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()
    
    tex_coord = nodes.new('ShaderNodeTexCoord')
    mapping = nodes.new('ShaderNodeMapping')
    env_tex = nodes.new('ShaderNodeTexEnvironment')
    bg = nodes.new('ShaderNodeBackground')
    out = nodes.new('ShaderNodeOutputWorld')
    
    stars_path = get_texture_path("stars.jpg")
    try:
        env_img = bpy.data.images.load(stars_path)
        env_tex.image = env_img
    except Exception as e:
        print(f"Could not load stars texture: {e}")
    
    # Keep the background slightly dim so the Sun's contrast pops
    bg.inputs['Strength'].default_value = 1.0
    
    links.new(tex_coord.outputs['Generated'], mapping.inputs['Vector'])
    links.new(mapping.outputs['Vector'], env_tex.inputs['Vector'])
    links.new(env_tex.outputs['Color'], bg.inputs['Color'])
    links.new(bg.outputs['Background'], out.inputs['Surface'])

def setup_camera():
    """Sets up a cinematic camera perfectly framing the Sun."""
    cam_data = bpy.data.cameras.new("MainCamera")
    cam_data.lens = 50.0  # 50mm focal length
    cam_data.clip_start = 0.1
    cam_data.clip_end = 10000.0
    
    cam_obj = bpy.data.objects.new("Camera", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    link_to_collection(cam_obj, "Environment")
    
    # Calculate perfect distance to frame the Sun with comfortable margins
    distance = SUN_RADIUS * 6.5
    
    # Place camera almost straight on, with a very slight angle
    cam_obj.location = (0, -distance, distance * 0.05)
    
    # Track the camera to the origin (Sun)
    direction = Vector((0, 0, 0)) - cam_obj.location
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    
    bpy.context.scene.camera = cam_obj

# ==============================================================================
# CELESTIAL BODIES (MODULAR)
# ==============================================================================

def create_celestial_body(name, radius, location, segments=128, ring_count=64):
    """Reusable function to spawn a high-quality spherical mesh."""
    bpy.ops.mesh.primitive_uv_sphere_add(
        radius=radius,
        segments=segments,
        ring_count=ring_count,
        location=location,
        calc_uvs=True
    )
    obj = bpy.context.object
    obj.name = name
    
    # Smooth shading
    bpy.ops.object.shade_smooth()
        
    return obj

def apply_material_sun(sun_obj):
    """Builds a complex, physically plausible emission shader for the Sun."""
    mat = bpy.data.materials.new(name="Sun_Material")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()
    
    # Create Nodes
    tex_coord = nodes.new("ShaderNodeTexCoord")
    mapping = nodes.new("ShaderNodeMapping")
    
    # Surface Texture
    tex_image1 = nodes.new("ShaderNodeTexImage")
    tex_path1 = get_texture_path(PLANET_TEXTURES["Sun"]["surface"])
    try:
        img1 = bpy.data.images.load(tex_path1)
        tex_image1.image = img1
    except Exception as e:
        print(f"Error loading {tex_path1}: {e}")
        
    # Sunmap Texture
    tex_image2 = nodes.new("ShaderNodeTexImage")
    tex_path2 = get_texture_path(PLANET_TEXTURES["Sun"]["map"])
    try:
        img2 = bpy.data.images.load(tex_path2)
        try:
            img2.colorspace_settings.name = 'Non-Color'
        except:
            pass
        tex_image2.image = img2
    except Exception as e:
        print(f"Error loading {tex_path2}: {e}")
        
    # Emission Node
    emission = nodes.new("ShaderNodeEmission")
    
    # Multiply node to control strength
    math_strength = nodes.new("ShaderNodeMath")
    math_strength.operation = 'MULTIPLY'
    math_strength.inputs[1].default_value = 5.0 # Lower strength preserves color
    
    # Output Node
    output = nodes.new("ShaderNodeOutputMaterial")
    
    # Links - CRITICAL: Use UV coordinates instead of Generated
    links.new(tex_coord.outputs['UV'], mapping.inputs['Vector'])
    links.new(mapping.outputs['Vector'], tex_image1.inputs['Vector'])
    links.new(mapping.outputs['Vector'], tex_image2.inputs['Vector'])
    
    # Feed color directly into emission to preserve the deep oranges
    links.new(tex_image1.outputs['Color'], emission.inputs['Color'])
    
    # Feed map into strength
    links.new(tex_image2.outputs['Color'], math_strength.inputs[0])
    links.new(math_strength.outputs['Value'], emission.inputs['Strength'])
    
    links.new(emission.outputs['Emission'], output.inputs['Surface'])
    
    # Assign material
    if len(sun_obj.data.materials) == 0:
        sun_obj.data.materials.append(mat)
    else:
        sun_obj.data.materials[0] = mat

def create_sun():
    """Creates the Sun and applies materials and lighting."""
    sun_obj = create_celestial_body("Sun", SUN_RADIUS, (0, 0, 0), segments=256, ring_count=128)
    link_to_collection(sun_obj, "Sun")
    
    apply_material_sun(sun_obj)
    
    # Add a point light at the center of the Sun to cast actual shadows onto future planets
    light_data = bpy.data.lights.new(name="Sun_Light", type='POINT')
    light_data.energy = 100000.0  # Extremely bright for Cycles
    light_data.color = (1.0, 0.9, 0.7)  # Warm sunlight
    light_data.shadow_soft_size = SUN_RADIUS # Physically accurate soft shadows
    
    light_obj = bpy.data.objects.new(name="Sun_Point_Light", object_data=light_data)
    bpy.context.scene.collection.objects.link(light_obj)
    light_obj.location = (0, 0, 0)
    link_to_collection(light_obj, "Sun")
    
    return sun_obj

# ==============================================================================
# ANIMATION
# ==============================================================================

def setup_animation(sun_obj):
    """Sets up the seamless looping rotation."""
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = TOTAL_FRAMES
    
    # Rotate the Sun on its Z-axis (equatorial rotation)
    # The animation should cover exactly 360 degrees (2 * pi radians)
    
    # Insert keyframe at frame 1 (0 degrees)
    sun_obj.rotation_euler[2] = 0.0
    sun_obj.keyframe_insert(data_path="rotation_euler", index=2, frame=1)
    
    # Insert keyframe one frame AFTER the end to ensure seamless looping
    # If frame_end is 240, frame 241 should be exactly target degrees.
    target_rotation_degrees = 360.0 * ROTATION_RATIO
    sun_obj.rotation_euler[2] = math.radians(target_rotation_degrees)
    sun_obj.keyframe_insert(data_path="rotation_euler", index=2, frame=TOTAL_FRAMES + 1)
    
    # Set interpolation to LINEAR
    if sun_obj.animation_data and sun_obj.animation_data.action:
        for fcurve in sun_obj.animation_data.action.fcurves:
            for keyframe in fcurve.keyframe_points:
                keyframe.interpolation = 'LINEAR'

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

def main():
    clear_scene()
    setup_collections()
    setup_rendering()
    setup_world()
    setup_camera()
    
    sun_obj = create_sun()
    setup_animation(sun_obj)
    
    print("✅ Solar System sequence successfully generated.")

if __name__ == "__main__":
    main()