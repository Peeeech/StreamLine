import bpy # type: ignore
import re

def process(extracted_string):
    geo_ids = []
    normals_dict = {}
    uvs_dict = {}
    colors_dict = {}
    coloruvs_dict = {}
    vertices_dict = {}
    p_dict = {}
    cleaned_lines = re.sub(r'^\s*\n', '', extracted_string, flags=re.MULTILINE)

    lines = cleaned_lines.splitlines()
    for i, line in enumerate(lines, start=0):
        if 'geometry id=' in line:
            geo_id = extract_geo_ids(line)
            geo_ids.append(geo_id)

        if f'points{geo_id}' in line:
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                normal_array = extract_normals_array(next_line)
                normals_dict[geo_id] = normal_array

        if f'reguvs{geo_id}' in line:           #changed from uvs to reguvs to distinguish
            if i + 1 < len(lines):              #between uvs and coloruvs; havent seen any 
                next_line = lines[i + 1]        #coloruvs yet but just in case
                uv_array = extract_uvs_array(next_line)
                uvs_dict[geo_id] = uv_array

        if f'colors{geo_id}' in line:
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                color_array = extract_colors_array(next_line)
                colors_dict[geo_id] = color_array

        if f'coloruvs{geo_id}' in line:
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                coloruv_array = extract_coloruvs_array(next_line)
                coloruvs_dict[geo_id] = coloruv_array
        
        if f'vertices{geo_id}' in line:
            if i + 2 < len(lines):
                vcount_line = lines[i + 1]
                p_line = lines[i + 2]
                vertex_array = extract_vertices_array(vcount_line)
                vertices_dict[geo_id] = vertex_array
                p_array = extract_p_array(p_line)
                p_dict[geo_id] = p_array

    flags = {}
    for geo_id in geo_ids:
        has_normals = geo_id in normals_dict
        has_uvs = geo_id in uvs_dict
        has_colors = geo_id in colors_dict
        has_coloruvs = geo_id in coloruvs_dict
        has_vertices = geo_id in vertices_dict
        has_p = geo_id in p_dict
        flags[geo_id] = {
            'has_normals': has_normals,
            'has_uvs': has_uvs,
            'has_colors': has_colors,
            'has_coloruvs': has_coloruvs,
            'has_vertices': has_vertices,
            'has_p': has_p,
        }
    
    for geo_id, flag in flags.items():
        step = 0
        if flag['has_normals']:
            step += 1
        if flag['has_uvs']:
            step += 1
        if flag['has_colors']:
            step += 1
        if flag['has_coloruvs']:
            print(f"[DEBUG] {geo_id} coloruvs not implemented, please contact peeeech if you see this")

        normals = normals_dict.get(geo_id)
        uvs = uvs_dict.get(geo_id)
        colors = colors_dict.get(geo_id)
        coloruvs = coloruvs_dict.get(geo_id)
        vertices = vertices_dict.get(geo_id)
        p = p_dict.get(geo_id)

        createObject(geo_id, step, normals=normals, uvs=uvs, colors=colors, coloruvs=coloruvs, vertices=vertices, p=p)
    
    global Geo
    Geo = geo_ids

def extract_geo_ids(line):
    geo_id = re.compile(r'geometry id="([^"]+)"')
    match = geo_id.search(line)
    if match:
        return match.group(1)
    return None

def extract_normals_array(line):
    normal_array = re.compile(r'points array= "([^"]+)"')
    match = normal_array.search(line)
    if match:
        return match.group(1)
    return None

def extract_uvs_array(line):
    normal_array = re.compile(r'reguvs array= "([^"]+)"')
    match = normal_array.search(line)
    if match:
        return match.group(1)
    return None

def extract_colors_array(line):
    normal_array = re.compile(r'colors array= "([^"]+)"')
    match = normal_array.search(line)
    if match:
        return match.group(1)
    return None

def extract_coloruvs_array(line):
    normal_array = re.compile(r'coloruv array= "([^"]+)"')
    match = normal_array.search(line)
    if match:
        return match.group(1)
    return None

def extract_vertices_array(line):
    normal_array = re.compile(r'vcount= "([^"]+)"')
    match = normal_array.search(line)
    if match:
        return match.group(1)
    return None

def extract_p_array(line):
    normal_array = re.compile(r'p= "([^"]+)"')
    match = normal_array.search(line)
    if match:
        return match.group(1)
    return None

def parse_floats(data_str):
    """Parse a space-separated string into a list of floats."""
    return [float(x) for x in data_str.strip().split()]

def parse_ints(data_str):
    """Parse a space-separated string into a list of integers."""
    return [int(x) for x in data_str.strip().split()]

def truncate_string(s, max_length):
    s = str(s)
    if len(s) > max_length:
        return s[:max_length] + "..."
    return s

# ========================= Initial Geometry Creation =========================
def createObject(geo, step, normals=None, uvs=None, colors=None, coloruvs=None, vertices=None, p=None):
    #print(f"Creating object for Geo ID: {geo}")
    normals_list = parse_floats(normals) if normals else []
    uvs_list = parse_floats(uvs) if uvs else []
    colors_list = parse_floats(colors) if colors else []
    coloruvs_list = parse_floats(coloruvs) if coloruvs else []
    vertices_list = parse_ints(vertices) if vertices else []
    p_list = parse_ints(p) if p else []
    
    verts = []
    uv = []
    color = []
    coloruv = []
    vertex = []
    p2 = []
    p2b = [] #Not using these two, unsure if it'll be a problem
    p2c = [] #^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    if(normals != None):
        for i in range(0, len(normals_list), 3):
            if i + 2 < len(normals_list):
                x, y, z = normals_list[i], normals_list[i+1], normals_list[i+2]
                verts.append((x, y, z))

    if(uvs != None):
        for i in range(0, len(uvs_list), 2):
            if i + 1 < len(uvs_list):
                s, t = uvs_list[i], uvs_list[i+1]
                uv.append((s, t))

    if(colors != None):
        for i in range(0, len(colors_list), 4):
            if i + 3 < len(colors_list):
                r, g, b, a = colors_list[i], colors_list[i+1], colors_list[i+2], colors_list[i+3]
                color.append((r, g, b, a))
    
    if(coloruvs != None):
        for i in range(0, len(coloruvs_list), 1):
            if i < len(coloruvs_list):
                x = coloruvs_list[i]
                coloruv.append((x))

    if(vertices != None):
        for i in range(0, len(vertices_list), 1):
            if i < len(vertices_list):
                v = vertices_list[i]
                vertex.append((v))

    if(p != None):
        if (step == 3):
            for i in range(0, len(p_list), 3):
                if i + 2 < len(p_list):
                    a, b, c = p_list[i], p_list[i + 1], p_list[i + 2]
                    p2.append((a))
                    p2b.append((b))
                    p2c.append((c))
        elif (step == 2):
            for i in range(0, len(p_list), 2):
                if i + 1 < len(p_list):
                    a, b = p_list[i], p_list[i + 1]
                    p2.append((a))
                    p2b.append((b))
        else:
            print(f"stepped out, something broke", geo, verts, uv, color)

    p2 = assignFaces(p2)
    mesh = bpy.data.meshes.new(name=geo)
    obj = bpy.data.objects.new(name=geo, object_data=mesh)
    bpy.context.collection.objects.link(obj)
    mesh.from_pydata(verts, [], p2)
    mesh.update()

    if uvs:
        if ((len(uvs_list)) != (len(verts)*2)):
            print(f"{geo} doesnt't work")
        if(colors):
            if ((len(colors_list)) != (len(verts)*4)):
                print(f"{geo} doesnt't work")

        if ((len(uvs_list)) == (len(verts)*2)):
            uv_layer = mesh.uv_layers.new(name="UVMap")
            for poly in mesh.polygons:
                for i in poly.loop_indices:
                    loop = mesh.loops[i]
                    vertex_index = loop.vertex_index
                    uv_index = vertex_index * 2
                    if uv_index + 1 < len(uvs_list):
                        u = uvs_list[uv_index]
                        v = uvs_list[uv_index + 1]
                        uv_layer.data[i].uv = (u, v)
                    else:
                        uv_layer.data[i].uv = (0.0, 0.0)
            if ((len(colors_list)) == (len(verts)*4)):
                color_layer = mesh.vertex_colors.new(name="Col")
                for poly in mesh.polygons:
                    for i in poly.loop_indices:
                        loop = mesh.loops[i]
                        vertex_index = loop.vertex_index
                        color_index = vertex_index * 4
                        if color_index + 3 < len(colors_list):
                            r = colors_list[color_index]
                            g = colors_list[color_index + 1]
                            b = colors_list[color_index + 2]
                            a = colors_list[color_index + 3]
                            color_layer.data[i].color = (r, g, b, a)
                        else:
                            color_layer.data[i].color = (1.0, 1.0, 1.0, 1.0)
            else:
                color_layer = mesh.vertex_colors.new(name="Col")
                uv_layer = mesh.uv_layers.new(name="UVMap")
                for poly in mesh.polygons:
                    for i in poly.loop_indices:
                        color_layer.data[i].color = (1.0, 1.0, 1.0, 1.0)



#shorten strings for easy debug
    geo = truncate_string(geo, 50)
    verts = truncate_string(verts, 15)
    uv = truncate_string(uv, 15)
    color = truncate_string(color, 15)
    coloruv = truncate_string(coloruv, 15)
    vertex = truncate_string(vertex, 15)
    p2 = truncate_string(p2, 15)    

def assignFaces(p):
    faces = []
    for i in range(0, len(p), 3):
        if i + 2 < len(p):
            a, b, c = p[i], p[i+1], p[i + 2]
            faces.append((a, b, c))
    return faces
            
