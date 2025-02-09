import os
import sys
import re
import bpy #type: ignore
import math

def process(extracted_string):
    global anim
    anim = {}
    timeArray = []
    translationArray = []
    rotationArray = []
    scaleArray = []
    cleaned_lines = re.sub(r'^\s*\n', '', extracted_string, flags=re.MULTILINE)
    lines = cleaned_lines.splitlines()
    for i, line in enumerate(lines, start=0):
        if "mesh animation id" in line:
            animName = extractMatName(lines[i-1])
            animID = extractMeshAnimID(line)
            if "translation offset" in lines[i+1]:
                translationOff = extractTOff(lines[i+1])
            if "rotation offset" in lines[i+2]:
                rotationOff = extractROff(lines[i+2])
            if "scale divider" in lines[i+3]:
                scaleDiv = extractSDiv(lines[i+3])
            if "time" in lines[i+4]:
                if "count" in lines[i+5]:
                    timeArray = extractSingleArray(lines[i+6])
            if "mesh_translate" in lines[i+7]:
                if "count" in lines[i+8]:
                    translationArray = extractTripleArray(lines[i+9])
            if "mesh_rotate" in lines[i+10]:
                if "count" in lines[i+11]:
                    rotationArray = extractTripleArray(lines[i+12])
            if "mesh_scale" in lines[i+13]:
                if "count" in lines[i+14]:
                    scaleArray = extractTripleArray(lines[i+15])

                anim[animID] = {
                    "name": animName,
                    "type": "meshAnimation",
                    "translationOffset": translationOff,
                    "rotationOffset": rotationOff,
                    "scaleDivider": scaleDiv,
                    "timeArray": timeArray,
                    "translationArray": translationArray,
                    "rotationArray": rotationArray,
                    "scaleArray": scaleArray
                }
            
        if "material animation id" in line:
            animName = extractMatName(lines[i-1])
            animID = extractMatAnimID(line)
            if "centerS" in lines[i+1]:
                centerS = extractCS(lines[i+1])
            if "centerT" in lines[i+2]:
                centerT = extractCT(lines[i+2])
            if "time" in lines[i+3]:
                if "count" in lines[i+4]:
                    timeArray = extractSingleArray(lines[i+5])
            if "mat_translation" in lines[i+6]:
                if "count" in lines[i+7]:
                    translationArray = extractDoubleArray(lines[i+8])
            if "mat_rotation" in lines[i+9]:
                if "count" in lines[i+10]:
                    rotationArray = extractSingleArray(lines[i+11])
            if "mat_scale" in lines[i+12]:
                if "count" in lines[i+13]:
                    scaleArray = extractDoubleArray(lines[i+14])


                anim[animID] = {
                    "name": animName,
                    "type": "materialAnimation",
                    "centerS": centerS,
                    "centerT": centerT,
                    "timeArray": timeArray,
                    "translationArray": translationArray,
                    "rotationArray": rotationArray,
                    "scaleArray": scaleArray
                }


def makeAnims(anim_id, data):
    if data.get("type") == "meshAnimation":
        obj = bpy.data.objects.get(anim_id)
        if obj:
            name = data.get("name")
            translation_offset = data.get("translationOffset")
            rotation_offset = data.get("rotationOffset")
            scale_divider = data.get("scaleDivider") 
            time_array = data.get("timeArray")
            translation_array = data.get("translationArray")
            rotation_array = data.get("rotationArray")
            scale_array = data.get("scaleArray")
            base_loc = obj.location.copy()
            base_rot = obj.rotation_euler.copy()
            base_sca = obj.scale.copy()

            for i, t in enumerate(time_array):
                frame = int(float(t))

                traX, traY, traZ = translation_array[i]
                rotX, rotY, rotZ = rotation_array[i]
                scaX, scaY, scaZ = scale_array[i]

                traX -= translation_offset[0]
                traY -= translation_offset[1]
                traZ -= translation_offset[2]
                rotX = math.radians(rotX - rotation_offset[0])
                rotY = math.radians(rotY - rotation_offset[1])
                rotZ = math.radians(rotZ - rotation_offset[2])
                scaX /= scale_divider[0]
                scaY /= scale_divider[1]
                scaZ /= scale_divider[2]

                obj.location = (
                    base_loc.x + traX,
                    base_loc.y + traY,
                    base_loc.z + traZ
                )
                obj.rotation_euler = (
                    base_rot.x + rotX,
                    base_rot.y + rotY,
                    base_rot.z + rotZ
                )
                obj.scale = (
                    base_sca.x * scaX,
                    base_sca.y * scaY,
                    base_sca.z * scaZ
                )
                
                obj.keyframe_insert(data_path="location", frame=frame)
                obj.keyframe_insert(data_path="rotation_euler", frame=frame)  
                obj.keyframe_insert(data_path="scale", frame=frame)
        if not obj:
            print(f"Warning: No object named '{anim_id}' found in the scene.")
        

    if data.get("type") == "materialAnimation":
        mat_names = [anim_id, anim_id + "_v", anim_id + "_v_x", anim_id + "_v_x_uv2"]
        mat = None

        for possible_name in mat_names:
            mat = bpy.data.materials.get(possible_name)
            if mat:
                break
            
        if mat:
            #setup nodes:
            node_tree = mat.node_tree
            nodes = node_tree.nodes
            for node in node_tree.nodes:
                if node.name == "Mapping":
                    mapping_node = node

            #animation information
            name = data.get("name")
            centerS = data.get("centerS")
            centerT = data.get("centerT")
            time_array = data.get("timeArray")
            translation_array = data.get("translationArray")
            rotation_array = data.get("rotationArray")
            scale_array = data.get("scaleArray")

            for i, t in enumerate(time_array):
                frame = int(float(t))

                traS, traT = translation_array[i]
                rot = rotation_array[i]
                scaS, scaT = scale_array[i]

                if "Location" in mapping_node.inputs:
                    mapping_node.inputs["Location"].default_value = (traS, traT, 0.0)
                    mapping_node.inputs["Rotation"].default_value = (0.0, 0.0, rot)
                    mapping_node.inputs["Scale"].default_value = (scaS, scaT, 1.0)

                    mapping_node.inputs["Location"].keyframe_insert(data_path="default_value", frame=frame)
                    mapping_node.inputs["Rotation"].keyframe_insert(data_path="default_value", frame=frame)
                    mapping_node.inputs["Scale"].keyframe_insert(data_path="default_value", frame=frame)
                else:
                    mapping_node.translation = (traS, traT, 0.0)
                    mapping_node.rotation = (0.0, 0.0, rot)
                    mapping_node.scale = (scaS, scaT, 1.0)

                    mapping_node.keyframe_insert("translation", frame=frame)
                    mapping_node.keyframe_insert("rotation", frame=frame)
                    mapping_node.keyframe_insert("scale", frame=frame)

        if not mat:
            print(f"Warning: No material named '{anim_id}' found in the scene.")
                    
def pushNLAs(anim_id, data):
    obj = bpy.data.objects.get(anim_id)
    name = data.get("name")
    mat_names = [anim_id, anim_id + "_v", anim_id + "_v_x", anim_id + "_v_x_uv2"]
    mat = None

    if obj:
        nla_track = obj.animation_data.nla_tracks.new()
        nla_track.name = name

        start_frame, end_frame = None, None
        action = obj.animation_data.action
        for fcurve in action.fcurves:
            for key in fcurve.keyframe_points:
                frame = key.co.x
                if start_frame is None or frame < start_frame:
                    start_frame = frame
                if end_frame is None or frame > end_frame:
                    end_frame = frame

        nla_strip = nla_track.strips.new(name, start_frame, action)
        nla_strip.frame_start = start_frame
        nla_strip.frame_end = end_frame
        obj.animation_data.action = None


        if start_frame is None or end_frame is None:
            print("Action has no keyframes.")


    for possible_name in mat_names:
        mat = bpy.data.materials.get(possible_name)
        if mat:
                break
    if mat:        
        action = mat.node_tree.animation_data.action
        nla_track = mat.node_tree.animation_data.nla_tracks.new()
        nla_track.name = name

        start_frame, end_frame = None, None

        for fcurve in action.fcurves:
            for key in fcurve.keyframe_points:
                frame = key.co.x
                if start_frame is None or frame < start_frame:
                    start_frame = frame
                if end_frame is None or frame > end_frame:
                    end_frame = frame

        nla_strip = nla_track.strips.new(name, start_frame, action)
        nla_strip.frame_start = start_frame
        nla_strip.frame_end = end_frame
        mat.node_tree.animation_data.action = None


        if start_frame is None or end_frame is None:
            print("Action has no keyframes.")
        
def extractMatName(line):
    animid = re.compile(r'"([^"]+)"')
    match = animid.search(line)
    if match:
        return match.group(1)
    return None

def extractMeshAnimID(line):
    animid = re.compile(r'mesh animation id= "([^"]+)"')
    match = animid.search(line)
    if match:
        return match.group(1)
    return None

def extractMatAnimID(line):
    animid = re.compile(r'material animation id= "([^"]+)"')
    match = animid.search(line)
    if match:
        return match.group(1)
    return None

def extractTOff(line):
    tOffset = re.compile(r'translation offset= "([^"]+)"')
    match = tOffset.search(line)
    if match:
        numbers = tuple(map(float, match.group(1).split()))
        return numbers
    return None

def extractROff(line):
    rOffset = re.compile(r'rotation offset= "([^"]+)"')
    match = rOffset.search(line)
    if match:
        numbers = tuple(map(float, match.group(1).split()))
        return numbers
    return None

def extractSDiv(line):
    sDivision = re.compile(r'scale divider= "([^"]+)"')
    match = sDivision.search(line)
    if match:
        numbers = tuple(map(float, match.group(1).split()))
        return numbers
    return None

def extractCnt(line):
    count = re.compile(r'count= "([^"]+)"')
    match = count.search(line)
    if match:
        return match.group(1)
    return None

def extractSingleArray(line):
    array = re.compile(r'"([^"]+)"')
    match = array.search(line)
    if match:
        numbers = list(map(float, match.group(1).split()))
        return numbers
    return None

def extractDoubleArray(line):
    array = re.compile(r'"([^"]+)"')
    match = array.search(line)
    if match:
        numbers = list(map(float, match.group(1).split()))
        numberArray = []
        for i in range(0, len(numbers), 2):
            numberArray.append(tuple(numbers[i:i+2]))
        return numberArray
    return None

def extractTripleArray(line):
    array = re.compile(r'"([^"]+)"')
    match = array.search(line)
    if match:
        numbers = list(map(float, match.group(1).split()))
        numberArray = []
        for i in range(0, len(numbers), 3):
            numberArray.append(tuple(numbers[i:i+3]))
        return numberArray
    return None

def extractCS(line):
    centerS = re.compile(r'centerS= "([^"]+)"')
    match = centerS.search(line)
    if match:
        return match.group(1)
    return None

def extractCT(line):
    centerT = re.compile(r'centerT= "([^"]+)"')
    match = centerT.search(line)
    if match:
        return match.group(1)
    return None
