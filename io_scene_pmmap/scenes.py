import os
import sys
import re
import bpy # type: ignore
import math
from . import __init__
from . import images
from . import effects
from . import materials
from . import animations
from . import streamLine


def extract_geo_ids(line):
    check = re.compile(r'geo="([^"]+)"')
    match = check.search(str(line))
    if match:
        return match.group(1)
    return None
def extract_mat_ids(line):
    check = re.compile(r'instance_material="([^"]+)"')
    match = check.search(str(line))
    if match:
        return match.group(1)
    return None
def extract_node_ids(line):
    check = re.compile(r'(\s*)node id="([^"]+)"')
    match = check.search(str(line))
    if match:
        return match.group(1) + match.group(2)
    return None
def extract_trans_data(line):
    check = re.compile(r'translate sid="([^"]+)"')
    match = check.search(str(line))
    if match:
        numbers = match.group(1).split()
        return numbers
    return None
def extract_rot_data(line):
    check = re.compile(r'rotate sid="([^"]+)"')
    match = check.search(str(line))
    if match:
        numbers = match.group(1).split()
        return numbers
    return None
def extract_scale_data(line):
    check = re.compile(r'scale sid="([^"]+)"')
    match = check.search(str(line))
    if match:
        numbers = match.group(1).split()
        return numbers
    return None
def extractInd(node):
    check = re.compile(r'^(\s*)(.+)$')
    match = check.search(node)
    if match:
        return match.group(1), match.group(2)
    return None

class Node:
    def __init__(self, node_id, geo_id=None, mat_id=None, trans=None, rot=None, scale=None):
        self.geo_id = geo_id
        self.node_id = node_id
        self.mat_id = mat_id
        self.trans = trans
        self.rot = rot
        self.scale = scale

        self.parent = None
        self.children = []

    def add_child(self, child_node):
        self.children.append(child_node)
        child_node.parent = self


def process(extracted_string):
    node_blocks = []
    current_block = []
    root_nodes = []
    
    cleaned_lines = re.sub(r'^\s*\n', '', extracted_string, flags=re.MULTILINE)

    lines = cleaned_lines.splitlines()
    for line in lines:
        if 'node id=' in line:
            if current_block:
                node_blocks.append(current_block)
                current_block = []
        current_block.append(line)
    if current_block:
        node_blocks.append(current_block)

    # ========================= Final Material Creation =========================
    if bpy.context.scene.t_import:
        materialList = materials.mat
        for idx in range(len(materials.mat)):
            mat_name = materials.mat[idx][1]
            effect_value = effects.eff[idx]
            if isinstance(effect_value, str):
                effect_value = f"{effect_value}.png"
                if effect_value in images.images:
                    match_index = images.images.index(effect_value)
                    effect_value = images.imagePaths[match_index]
            materials.makeMaterial(mat_name, effect_value, idx)

    # ========================= Final Geometry Creation =========================
    parent_stack = []
    for i, block in enumerate(node_blocks):
        node_id = extract_node_ids(block)
        if "    " not in node_id:
            node_id = "    " + node_id
        geo_id = extract_geo_ids(block)

        if bpy.context.scene.t_import:
            mat_id = extract_mat_ids(block)
            if mat_id is not None:
                for i, idx in materialList:
                    if mat_id == i:
                        mat_id = idx
                        break
        else:
            mat_id = None
        trans = extract_trans_data(block)
        rot = extract_rot_data(block)
        scale = extract_scale_data(block)

        ind, node_id = extractInd(node_id)
        ind = (len(ind) / 4)
        #print(f"{i}: {ind}{node_id}\n{geo_id}, {mat_id}, {trans}, {rot}, {scale}\n")
        createObj(ind, node_id, geo_id, mat_id, trans, rot, scale, parent_stack)
    root = bpy.context.scene.objects.get("world_root")
    root.rotation_euler = (math.radians(90), 0, 0)
    root.select_set(True)
    bpy.context.view_layer.objects.active = root
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    # ========================= Final Animation Creation =========================
    animDict = animations.anim
    for anim_id, data in animDict.items():
        animations.makeAnims(anim_id, data)
        animations.pushNLAs(anim_id, data)

    # ========================= Collection Creation =========================
    if bpy.context.scene.coll_creation:
        streamLine.main()

    # ========================= Scene Cleanup =========================
    if bpy.data.brushes:
        for brush in list(bpy.data.brushes):
            bpy.data.brushes.remove(brush)
    if "Render Result" in bpy.data.images:
        bpy.data.images.remove(bpy.data.images["Render Result"])
    if "LineStyle" in bpy.data.linestyles:
        bpy.data.linestyles.remove(bpy.data.linestyles["LineStyle"])
    if "Material" in bpy.data.materials:
        bpy.data.materials.remove(bpy.data.materials["Material"])

    allowed_screens = {"Animation", "Layout", "Scripting", "Shading", "Default.006", "Default.007", "Default.008", "UV Editing"}
    for scr in bpy.data.screens:
        if scr.name not in allowed_screens:
            bpy.data.batch_remove(ids=(scr.id_data,))

    allowed_workspaces = {"Layout", "UV Editing", "Shading", "Animation", "Scripting"}
    for ws in bpy.data.workspaces:
        if ws.name not in allowed_workspaces:
            bpy.data.batch_remove(ids=(ws.id_data,))
    if "World" in bpy.data.worlds:
        bpy.data.worlds.remove(bpy.data.worlds["World"])

    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'MATERIAL'
                        break

    update()

def update():
    bpy.ops.file.pack_all()
    for obj in bpy.context.scene.objects:
        if obj.type == 'MESH':
            obj.data.update()
    for mat in bpy.data.materials:
        mat.node_tree.update_tag()
    for area in bpy.context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()
    bpy.context.view_layer.update()
        
def createObj(ind, node, geo, mat, trans, rot, scale, parent_stack):    
    scene = bpy.context.scene
    if geo:
        new_obj = scene.objects.get(geo)
        if new_obj:
            if mat:
                material = bpy.data.materials.get(mat)
                new_obj.data.materials.append(material)
            if trans:
                new_obj.location = tuple(float(x) for x in trans)
            if rot:
                corrected_rot = (rot[2], rot[1], rot[0])
                new_obj.rotation_euler = tuple(math.radians(float(x)) for x in corrected_rot)
            if scale:
                new_obj.scale = tuple(float(x) for x in scale)
    else:
        new_obj = bpy.data.objects.new(name=node, object_data=None)
        if trans:
            new_obj.location = tuple(float(x) for x in trans)
        if rot:
            corrected_rot = (rot[2], rot[1], rot[0])
            new_obj.rotation_euler = tuple(math.radians(float(x)) for x in corrected_rot)
        if scale:
            new_obj.scale = tuple(float(x) for x in scale)
        if node not in scene.collection.objects:
            scene.collection.objects.link(new_obj)

    while len(parent_stack) >= ind:
        parent_stack.pop()

    if parent_stack:
        parent_obj = parent_stack[-1]
        new_obj.parent = parent_obj
    
    parent_stack.append(new_obj)
