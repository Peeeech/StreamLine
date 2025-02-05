import bpy

# Function to check and rename vertex color for a given object
def rename_vertex_color(object):
    # Check if the object has data and is a mesh
    if object.data and object.type == 'MESH':
        # Check if 'Col' exists in vertex colors
        if 'Col' not in object.data.vertex_colors:
            # Create a new vertex color layer with the desired name
            new_vertex_color_layer = object.data.vertex_colors.new(name="Col")

            # Copy the values from the old layers to the new one
            for poly in object.data.polygons:
                for loop_index in poly.loop_indices:
                    # Check if the old layer exists and is not the new one
                    if object.data.vertex_colors.active and object.data.vertex_colors.active.name not in ['Col', 'NGon Face-Vertex']:
                        old_layer = object.data.vertex_colors.active
                        new_vertex_color_layer.data[loop_index].color = old_layer.data[loop_index].color

            # Remove the old vertex color layers
            for old_layer in object.data.vertex_colors:
                if old_layer.name != "Col" and old_layer.name not in ['NGon Face-Vertex']:
                    object.data.vertex_colors.remove(old_layer)

# Iterate through all objects in the scene collection
for obj in bpy.context.collection.all_objects:
    try:
        rename_vertex_color(obj)
    except RuntimeError as e:
        print(f"Error for object {obj.name}: {e}")

# Function to replace Principled BSDF with Diffuse BSDF
def replace_principled_with_diffuse(material):
    if material.use_nodes:
        nodes = material.node_tree.nodes
        principled_node = None

        # Find the Principled BSDF node
        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled_node = node
                break

        if principled_node:
            # Create a new Diffuse BSDF node
            diffuse_node = nodes.new(type='ShaderNodeBsdfDiffuse')
            diffuse_node.location = principled_node.location

            # Connect Base Color to Diffuse BSDF color
            base_color_socket = None
            for input_socket in principled_node.inputs:
                if input_socket.name == 'Base Color' and input_socket.links:
                    base_color_socket = input_socket.links[0].from_socket
                    break

            if base_color_socket:
                material.node_tree.links.new(base_color_socket, diffuse_node.inputs["Color"])

            # Connect Diffuse BSDF to Surface
            surface_socket = None
            for output_socket in principled_node.outputs:
                if output_socket.name == 'BSDF' and output_socket.links:
                    surface_socket = output_socket.links[0].to_socket
                    break

            if surface_socket:
                material.node_tree.links.new(diffuse_node.outputs["BSDF"], surface_socket)

            # Remove the Principled BSDF node
            material.node_tree.nodes.remove(principled_node)

            # Connect Diffuse BSDF to Material Output if not already connected
            material_output = None
            for node in nodes:
                if node.type == 'OUTPUT_MATERIAL':
                    material_output = node
                    break

            if material_output:
                output_socket = None
                for input_socket in material_output.inputs:
                    if input_socket.name == 'Surface' and not input_socket.links:
                        output_socket = input_socket
                        break

                if output_socket:
                    material.node_tree.links.new(diffuse_node.outputs["BSDF"], output_socket)

# Function to check if an image has transparency
def has_transparency(img):
    alpha_channel = img.split()[-1]
    alpha_values = alpha_channel.getdata()
    return any(alpha < 255 for alpha in alpha_values)

# Function to modify material nodes for transparency
def modify_material_for_transparency(material):
    if material.use_nodes and material.node_tree:
        node_tree = material.node_tree
        nodes = node_tree.nodes
        links = node_tree.links

        # Create or find necessary nodes
        diffuse_bsdf_node = None
        image_texture_node = None
        material_output_node = None

        for node in nodes:
            if node.type == 'BSDF_DIFFUSE':
                diffuse_bsdf_node = node
            elif node.type == 'TEX_IMAGE':
                image_texture_node = node
            elif node.type == 'OUTPUT_MATERIAL':
                material_output_node = node

        # Create a Diffuse BSDF node if it doesn't exist
        if not diffuse_bsdf_node:
            diffuse_bsdf_node = nodes.new(type='ShaderNodeBsdfDiffuse')
            diffuse_bsdf_node.location = (0, 0)  # Adjust location as needed

        # Check if the Image Texture node exists
        if not image_texture_node:
            print(f"Material '{material.name}' has no Image Texture node.")
            return

        # Check if the Material Output node exists
        if not material_output_node:
            print(f"Material '{material.name}' has no Material Output node.")
            return

        # Add Transparent Shader and Mix Shader nodes
        transparent_shader = nodes.new(type='ShaderNodeBsdfTransparent')
        mix_shader = nodes.new(type='ShaderNodeMixShader')

        # Connect nodes safely
        links.new(image_texture_node.outputs['Color'], diffuse_bsdf_node.inputs['Color'])
        links.new(image_texture_node.outputs['Alpha'], mix_shader.inputs['Fac'])
        links.new(transparent_shader.outputs['BSDF'], mix_shader.inputs[1])
        links.new(diffuse_bsdf_node.outputs['BSDF'], mix_shader.inputs[2])
        links.new(mix_shader.outputs['Shader'], material_output_node.inputs['Surface'])

        # Adjust node locations
        mix_shader.location = (diffuse_bsdf_node.location.x + 200, diffuse_bsdf_node.location.y - 150)
        transparent_shader.location = (mix_shader.location.x, mix_shader.location.y + 200)
        material_output_node.location = (material_output_node.location.x + 100, material_output_node.location.y)

        # Enable transparency
        material.blend_method = 'BLEND'
        print(f"Material '{material.name}' has been updated for transparency.")


# Create a set to track processed materials
processed_materials = set()

# Iterate through all materials in the current scene
for material in bpy.data.materials:
    if material.users > 0 and material not in processed_materials:
        replace_principled_with_diffuse(material)

# Check if PIL is installed
try:
    from PIL import Image
except ImportError:
    print("PIL (Pillow) is not installed. Attempting to install...")
    try:
        import subprocess
        subprocess.Popen([bpy.app.binary_path_python, "-m", "ensurepip"]).communicate()
        subprocess.Popen([bpy.app.binary_path_python, "-m", "pip", "install", "Pillow"]).communicate()
        from PIL import Image
        print("PIL (Pillow) has been successfully installed.")
    except Exception as e:
        print(f"Error installing PIL (Pillow): {e}")
        quit()

# Iterate through all materials in the scene
for material in bpy.data.materials:
    if material.use_nodes and material.node_tree and material not in processed_materials:
        has_transparent_texture = False
        for node in material.node_tree.nodes:
            if node.type == 'TEX_IMAGE':
                image_texture = node.image
                if image_texture:
                    image_path = bpy.path.abspath(image_texture.filepath)
                    try:
                        img = Image.open(image_path)
                        if has_transparency(img):
                            has_transparent_texture = True
                            break
                    except Exception as e:
                        print(f"Error opening image '{image_path}': {e}")

        if has_transparent_texture:
            modify_material_for_transparency(material)
            processed_materials.add(material)

# Print a message if no materials with transparent textures are found
if not any(has_transparent_texture for material in bpy.data.materials if material.use_nodes and material.node_tree):
    print("No materials with transparent textures found for the affected objects.")

def process_material(material):
    if material and material.use_nodes:
        nodes = material.node_tree.nodes

        # Check if Attribute node with the name "Col" already exists
        col_attribute_node = nodes.get("Col", None)
        if not col_attribute_node:
            # Create Attribute node with the name "Col" if it doesn't exist
            col_attribute_node = nodes.new(type='ShaderNodeAttribute')
            col_attribute_node.attribute_name = "Col"
            col_attribute_node.name = "Col"  # Ensure a unique name

        image_texture_node = None
        diffuse_bsdf_node = None

        for node in nodes:
            if node.type == 'TEX_IMAGE':
                image_texture_node = node
            elif node.type == 'BSDF_DIFFUSE':
                diffuse_bsdf_node = node

        if image_texture_node and diffuse_bsdf_node:
            # Disconnect Image Texture node from Diffuse BSDF node
            if image_texture_node.outputs["Color"].links:
                material.node_tree.links.remove(image_texture_node.outputs["Color"].links[0])

            # Add MixRGB node if it doesn't exist
            mix_node = nodes.get("Mix", None)
            if not mix_node:
                mix_node = nodes.new(type='ShaderNodeMixRGB')
                mix_node.name = "Mix"  # Ensure a unique name
                mix_node.blend_type = 'MULTIPLY'
                mix_node.inputs["Fac"].default_value = 1.0
                mix_node.location = (diffuse_bsdf_node.location.x, diffuse_bsdf_node.location.y - 200)
                col_attribute_node.location = (diffuse_bsdf_node.location.x - 200, diffuse_bsdf_node.location.y - 275)

            # Connect nodes as described
            material.node_tree.links.new(image_texture_node.outputs["Color"], mix_node.inputs["Color1"])
            material.node_tree.links.new(col_attribute_node.outputs["Color"], mix_node.inputs["Color2"])
            material.node_tree.links.new(mix_node.outputs["Color"], diffuse_bsdf_node.inputs["Color"])

        elif diffuse_bsdf_node:
            # If there is only Diffuse BSDF, replace it with "Col" attribute
            if diffuse_bsdf_node.outputs["BSDF"].links:
                material.node_tree.links.remove(diffuse_bsdf_node.outputs["BSDF"].links[0])

            # Connect Attribute node to Material Output
            material_output_node = nodes.get("Material Output")
            diffuse_bsdf_node = nodes.get("Diffuse BSDF")

            col_attribute_node.location = (diffuse_bsdf_node.location.x - 300, diffuse_bsdf_node.location.y)

            material.node_tree.links.new(col_attribute_node.outputs["Color"], diffuse_bsdf_node.inputs["Color"])
            material.node_tree.links.new(diffuse_bsdf_node.outputs["BSDF"], material_output_node.inputs["Surface"])

# Iterate through all objects in the scene
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        # Iterate through all material slots of the object
        for material_slot in obj.material_slots:
            process_material(material_slot.material)

#UVRemap
def rename_first_uv_map(object):
    if object.type == 'MESH' and object.data.uv_layers:
        # Rename the first UV Map to "UVMap"
        object.data.uv_layers[0].name = "UVMap"
        
        # Print the name of the second UV Map if it exists
        if len(object.data.uv_layers) > 1:
            print("Second UV Map in", object.name, ":", object.data.uv_layers[1].name)

def process_objects():
    for obj in bpy.context.scene.objects:
        rename_first_uv_map(obj)

# Run the script
process_objects()

def get_node_attributes(node):
    # Customize this function based on the attributes you want to consider
    return (node.type, node.location.x, node.location.y)

def remove_duplicate_nodes(material):
    nodes_to_remove = set()
    nodes_seen = set()

    # Iterate through all nodes in the material
    for node in material.node_tree.nodes:
        node_attributes = get_node_attributes(node)

        # Check if this type of node with these attributes has already been seen
        if node_attributes in nodes_seen:
            nodes_to_remove.add(node_attributes)
        else:
            nodes_seen.add(node_attributes)

    # Remove duplicate nodes, keeping one version
    for node_attributes in nodes_to_remove:
        first_occurrence = True
        for node in material.node_tree.nodes:
            if get_node_attributes(node) == node_attributes:
                if first_occurrence:
                    first_occurrence = False
                else:
                    material.node_tree.nodes.remove(node)

def process_all_materials():
    for material in bpy.data.materials:
        remove_duplicate_nodes(material)

# Run the script
process_all_materials()

def connect_mix_shader_to_output(material):
    print(f"Processing material: {material.name}")
    
    # Check if the material has a node tree
    if material.use_nodes:
        # Find the 'Mix Shader' and 'Material Output' nodes in the material
        mix_shader_node = material.node_tree.nodes.get('Mix Shader')
        material_output_node = material.node_tree.nodes.get('Material Output')
        
        # Check if both nodes exist
        if mix_shader_node and material_output_node:
            # Connect the 'Shader' output of the Mix Shader node to the 'Surface' input of the Material Output node
            material.node_tree.links.new(mix_shader_node.outputs['Shader'], material_output_node.inputs['Surface'])
            print("Connected Mix Shader to Material Output.")
            return

    print("Mix Shader or Material Output node not found or it's already connected.")

# Iterate through all materials in the project
for material in bpy.data.materials:
    connect_mix_shader_to_output(material)

def remove_unlinked_nodes(material):
    # Get the material nodes
    nodes = material.node_tree.nodes

    # Create a set to store linked nodes
    linked_nodes = set()

    # Iterate through links and add linked nodes to the set
    for link in material.node_tree.links:
        linked_nodes.add(link.from_node)
        linked_nodes.add(link.to_node)

    # Remove nodes that are not in the set of linked nodes
    for node in nodes:
        if node not in linked_nodes:
            nodes.remove(node)

# Get all materials in the scene
materials = bpy.data.materials

# Iterate through each material and remove unlinked nodes
for material in materials:
    remove_unlinked_nodes(material)

