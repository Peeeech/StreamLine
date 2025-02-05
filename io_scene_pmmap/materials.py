import os
import sys
import re
import bpy # type: ignore

from . import effects
from . import images



def process(extracted_string):
    materials = []
    cleaned_lines = re.sub(r'^\s*\n', '', extracted_string, flags=re.MULTILINE)
    lines = cleaned_lines.splitlines()
    for i, line in enumerate(lines, start=0):
        if 'name=' in line:
            mat_id = extract_mat_id(line)
            mat_name = extract_mat_name(line)
            materials.append((mat_id, mat_name))
    global mat
    mat = materials

def extract_mat_name(line):
    mat = re.compile(r'name="([^"]+)"')
    match = mat.search(line)
    if match:
        return match.group(1)
    return None

def extract_mat_id(line):
    mat = re.compile(r'material id= "([^"]+)"')
    match = mat.search(line)
    if match:
        return match.group(1)
    return None

def has_transparency(img):
    alpha_channel = img.split()[-1]
    alpha_values = alpha_channel.getdata()
    return any(alpha < 255 for alpha in alpha_values)

# Function to create material
def makeMaterial(matName, tex_p, step):
    if matName in bpy.data.materials:
        return
    
    try:
        from PIL import Image # type: ignore
    except ImportError:
        print("PIL (Pillow) is not installed. Attempting to install...")
        try:
            import subprocess
            subprocess.Popen([bpy.app.binary_path_python, "-m", "ensurepip"]).communicate()
            subprocess.Popen([bpy.app.binary_path_python, "-m", "pip", "install", "Pillow"]).communicate()
            from PIL import Image # type: ignore
            print("PIL (Pillow) has been successfully installed.")
        except Exception as e:
            print(f"Error installing PIL (Pillow): {e}")
            quit()        
    
    number_list = [] 
    text_list = []

    material = bpy.data.materials.new(name=matName)
    material.use_nodes = True
    
    if isinstance(tex_p, str):
        if os.path.exists(tex_p):
            try:
                img = Image.open(tex_p)
                if has_transparency(img):
                    transparent = "true"
                else:
                    transparent = "false"
            except Exception as e:
                print(f"Error opening image '{tex_p}': {e}")
        else:
            print(f"Texture file '{tex_p}' does not exist after renaming!")

    node_tree = material.node_tree
    nodes = node_tree.nodes
    if isinstance(tex_p, str):
        diffuse_bsdf_node = nodes.new(type='ShaderNodeBsdfDiffuse')
        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled_bsdf_node = node
            elif node.type == 'OUTPUT_MATERIAL':
                material_output_node = node
        diffuse_bsdf_node.location = principled_bsdf_node.location
        nodes.remove(principled_bsdf_node)

        texture_node = material.node_tree.nodes.new('ShaderNodeTexImage')
        img = bpy.data.images.get(os.path.basename(tex_p))
        if not img:
            img = bpy.data.images.load(tex_p)
        texture_node.image = img

        col_attribute_node = nodes.new(type='ShaderNodeAttribute')
        col_attribute_node.attribute_name = "Col"
        col_attribute_node.name = "Col"
        mix_node = nodes.new(type='ShaderNodeMixRGB')
        mix_node.name = "Mix"  
        mix_node.blend_type = 'MULTIPLY'
        mix_node.inputs["Fac"].default_value = 1

        node_tree.links.new(texture_node.outputs['Color'], mix_node.inputs['Color1'])
        node_tree.links.new(col_attribute_node.outputs['Color'], mix_node.inputs['Color2'])
        node_tree.links.new(mix_node.outputs['Color'], diffuse_bsdf_node.inputs['Color'])

        texture_node.location = (texture_node.location.x - 300, texture_node.location.y + 300)
        col_attribute_node.location = (diffuse_bsdf_node.location.x - 200, diffuse_bsdf_node.location.y - 275)
        mix_node.location = (diffuse_bsdf_node.location.x, diffuse_bsdf_node.location.y - 200)
        material_output_node.location = (material_output_node.location.x + 100, material_output_node.location.y)

        if transparent == "false":
            node_tree.links.new(diffuse_bsdf_node.outputs['BSDF'], material_output_node.inputs['Surface'])

        if transparent == "true":
            material.blend_method = 'BLEND'
            
            transparent_shader = material.node_tree.nodes.new(type='ShaderNodeBsdfTransparent')
            mix_shader = material.node_tree.nodes.new(type='ShaderNodeMixShader')

            mix_shader.location = (diffuse_bsdf_node.location.x + 200, diffuse_bsdf_node.location.y - 150)
            transparent_shader.location = (mix_shader.location.x, mix_shader.location.y + 200)

            node_tree.links.new(texture_node.outputs['Alpha'], mix_shader.inputs['Fac'])
            node_tree.links.new(transparent_shader.outputs['BSDF'], mix_shader.inputs[1])
            node_tree.links.new(diffuse_bsdf_node.outputs['BSDF'], mix_shader.inputs[2])
            node_tree.links.new(mix_shader.outputs['Shader'], material_output_node.inputs['Surface'])
    
    elif isinstance(tex_p, list):
        r, g, b, a = tex_p
        for node in nodes:
            if node.type == 'BSDF_PRINCIPLED':
                principled_bsdf_node = node
                nodes.remove(principled_bsdf_node)
            elif node.type == 'OUTPUT_MATERIAL':
                material_output_node = node
        mix_node = nodes.new(type='ShaderNodeMixRGB')
        mix_node.name = "Mix"  
        mix_node.blend_type = 'MULTIPLY'
        mix_node.inputs["Fac"].default_value = 1
        col_attribute_node = nodes.new(type='ShaderNodeAttribute')
        col_attribute_node.attribute_name = "Col"
        col_attribute_node.name = "Col"
        rgb_node = nodes.new(type='ShaderNodeRGB')
        rgb_node.outputs["Color"].default_value = (r, g, b, a)
        
        rgb_node.location = (rgb_node.location.x - 200, rgb_node.location.y + 400)
        col_attribute_node.location = (col_attribute_node.location.x - 200, col_attribute_node.location.y + 200)
        mix_node.location = (mix_node.location.x, mix_node.location.y + 350)

        node_tree.links.new(rgb_node.outputs['Color'], mix_node.inputs['Color1'])
        node_tree.links.new(col_attribute_node.outputs['Color'], mix_node.inputs['Color2'])
        node_tree.links.new(mix_node.outputs['Color'], material_output_node.inputs['Surface'])