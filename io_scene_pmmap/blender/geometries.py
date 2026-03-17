# geometries.py
from __future__ import annotations
from mathutils import Matrix, Euler, Vector #type: ignore
import math
from typing import Any, Iterable, List, Tuple

try:
    import bpy  # type: ignore
except ImportError:
    print("geometry: no blenda")

ColorTest = False  # Set to True to disable vertex color extraction (for debugging)

# -------------------------
# Tiny debug helpers
# -------------------------

def _dbg(enabled: bool, msg: str) -> None:
    if enabled:
        print(msg)

def _indent(depth: int) -> str:
    return "  " * depth

def _get(x: Any, name: str, default: Any = None) -> Any:
    if isinstance(x, dict):
        return x.get(name, default)
    return getattr(x, name, default)

def _vec3_to_tuple(v: Any) -> Tuple[float, float, float]:
    if v is None:
        return (0.0, 0.0, 0.0)
    if hasattr(v, "x") and hasattr(v, "y") and hasattr(v, "z"):
        return (float(v.x), float(v.y), float(v.z))
    return (float(v[0]), float(v[1]), float(v[2]))

def _vec2_to_tuple(v: Any) -> Tuple[float, float]:
    if v is None:
        return (0.0, 0.0)
    if hasattr(v, "x") and hasattr(v, "y"):
        return (float(v.x), float(v.y))
    return (float(v[0]), float(v[1]))

def srgb_to_linear(c: float) -> float:
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4

def _color_to_rgba01(c: Any) -> Tuple[float, float, float, float]:
    if c is None:
        return (1.0, 1.0, 1.0, 1.0)
    if hasattr(c, "r") and hasattr(c, "g") and hasattr(c, "b"):
        a = getattr(c, "a", 255)
        r, g, b, a = float(c.r), float(c.g), float(c.b), float(a)
    else:
        if len(c) == 3:
            r, g, b = c
            a = 255
        else:
            r, g, b, a = c
        r, g, b, a = float(r), float(g), float(b), float(a)

    # normalize if it looks like bytes
    if r > 1.0 or g > 1.0 or b > 1.0 or a > 1.0:
        r /= 255.0
        g /= 255.0
        b /= 255.0
        a /= 255.0

    r = srgb_to_linear(r)
    g = srgb_to_linear(g)
    b = srgb_to_linear(b)

    return (r, g, b, a)

#region: variable i/o helpers
def hit_attributes_to_enum(hit: int) -> str:
    # Priority matters if multiple bits are set
    if hit & 0x20:
        return 'PLANE'
    if hit & 0x200:
        return 'WATER'
    if hit & 0x800:
        return 'SPIKE'
    if hit & 0x8000:  
        return 'BOAT'
    return 'NONE'

def cull_attributes_to_enum(cull: int) -> str:
    if cull == 0:
        return 'FRONT'
    if cull == 1:
        return 'BACK'
    if cull == 2:
        return 'ALL'
    if cull == 3:
        return 'NONE'
    return 'NONE'  # safe default

# -------------------------
# Geometry extraction / coercion
# -------------------------

def _faces_from_polys(polys: Iterable[Tuple[int, int]]) -> List[Tuple[int, int, int]]:
    faces: List[Tuple[int, int, int]] = []
    for a, b in polys:
        # (start, end) where end-start==3  OR (start, count==3)
        if b - a == 3 or b == 3:
            faces.append((a, a + 2, a + 1))
        else:
            # fallback fan
            span = (b - a) if b > a else b
            if span >= 3:
                for i in range(1, span - 1):
                    faces.append((a, a + i + 1, a + i))
    return faces

def _extract_geom(mesh_entry: Any, debug: bool, prefix: str):
    geom = mesh_entry.polygons

    if geom is None:
        _dbg(debug, f"{prefix}  [WARN] no geometry on mesh entry")
        return None

    # minimal sanity check
    if not geom.positions or not geom.polys:
        _dbg(debug, f"{prefix}  [SKIP] empty positions/polys")
        return None

    return geom

# -------------------------
# Blender build
# -------------------------

def _create_mesh_object(name: str, geom: Any, mesh_entry: Any, debug: bool, prefix: str, context=None):
    positions = geom.positions
    polys     = geom.polys
    matprefix = context.scene.mat_prefix

    if not positions or not polys:
        _dbg(debug, f"{prefix}  [SKIP] empty positions/polys")
        return None, None, None

    verts = [_vec3_to_tuple(p) for p in positions]
    faces = _faces_from_polys(polys)

    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update(calc_edges=True)

    # -----------------
    # UVs (per CORNER)
    # -----------------
    uvs = geom.uvs0

    if uvs and len(uvs) == len(verts) and len(me.loops) > 0:
        uv_layer = me.uv_layers.new(name="UVMap")
        flat_uv = [0.0] * (2 * len(me.loops))

        for li, loop in enumerate(me.loops):
            uv = uvs[loop.vertex_index]
            if uv is None:
                u = v = 0.0
            else:
                u, v = _vec2_to_tuple(uv)

            flat_uv[2 * li + 0] = u
            flat_uv[2 * li + 1] = 1.0 - v

        uv_layer.data.foreach_set("uv", flat_uv)

    uvs1 = geom.uvs1
    if uvs1 is not None and len(uvs1) == len(verts) and any(u is not None for u in uvs1):
        uv_layer1 = me.uv_layers.new(name="UVMap.001")
        flat_uv1 = [0.0] * (2 * len(me.loops))

        for li, loop in enumerate(me.loops):
            uv = uvs1[loop.vertex_index]
            if uv is None:
                u = v = 0.0
            else:
                u, v = _vec2_to_tuple(uv)

            flat_uv1[2 * li + 0] = u
            flat_uv1[2 * li + 1] = 1.0 - v

        uv_layer1.data.foreach_set("uv", flat_uv1)

    # -----------------
    # Colors
    # -----------------
    colors = geom.colors
    if colors and len(colors) == len(verts) and len(me.loops) > 0:
        col = me.color_attributes.new(
            name="Col",
            type="BYTE_COLOR",
            domain="CORNER"
        )
        flat_col = [0.0] * (4 * len(me.loops))

        for li, loop in enumerate(me.loops):
            r, g, b, a = _color_to_rgba01(colors[loop.vertex_index])
            flat_col[4 * li + 0] = r
            flat_col[4 * li + 1] = g
            flat_col[4 * li + 2] = b
            flat_col[4 * li + 3] = a

        col.data.foreach_set("color", flat_col)

    # -----------------
    # Normals
    # -----------------
    normals = geom.normals
    if normals and len(normals) == len(verts) and len(me.loops) > 0:
        loop_normals = [
            _vec3_to_tuple(normals[loop.vertex_index])
            for loop in me.loops
        ]
        if hasattr(me, "use_auto_smooth"):
            me.use_auto_smooth = True
        else:
            me.shade_smooth()
        me.normals_split_custom_set(loop_normals)

    obj = bpy.data.objects.new(f"{matprefix}{name}", me)

    # -----------------
    # Initial Material binding
    # -----------------
    mat_name = mesh_entry.material.name

    if mat_name:
        mat_empty = bpy.data.objects.get(f"{matprefix}{mat_name}")            
        mats_col = bpy.data.collections.get("Materials")

        if (
            not mat_empty
            or mat_empty.type != 'EMPTY'
            or not mats_col
        ):
            _dbg(debug, f"{prefix}  [WARN] material EMPTY not found in Materials collection: {mat_name!r}")
            return obj, me, None

        mat_props = mat_empty.ttyd_world_material

        if not mat_props.materialRefs:
            _dbg(debug, f"{prefix}  [WARN] no material refs on EMPTY: {mat_name!r}")
            return obj, me, mat_empty

        base_mat = mat_props.materialRefs[0].material

        if len(me.materials) == 0:
            me.materials.append(base_mat)
        else:
            me.materials[0] = base_mat

        for p in me.polygons:
            p.material_index = 0

    return obj, me, mat_empty

def build_geometry_from_dmd(dmd: Any, context=None, debug=None):
    """
    Safe entrypoint: pass the dmd object; we’ll auto-pick dmd.sceneGraph if present.
    """
    root = dmd.sceneGraph
    return build_geometry_from_scenegraph(root, context=context, debug=debug)

def build_geometry_from_scenegraph(root_node: Any, context=None, debug=None):

    if context is None:
        context = bpy.context

    coll = context.scene.collection
    matprefix = context.scene.mat_prefix

    stats = {
        "nodes": 0,
        "empties": 0,
        "mesh_nodes": 0,
        "meshes_seen": 0,
        "meshes_built": 0,
        "meshes_skipped": 0,
    }

    def _parent_local(child_obj, parent_obj):
        child_obj.parent = parent_obj
        child_obj.matrix_parent_inverse = Matrix.Identity(4)

    def _node_local_matrix(node):
        T = (
            Matrix.Translation(Vector(_vec3_to_tuple(node.translation)))
            if node.translation is not None
            else Matrix.Identity(4)
        )

        if node.rotation is not None:
            rx, ry, rz = _vec3_to_tuple(node.rotation)
            R = Euler(
                (math.radians(rx), math.radians(ry), math.radians(rz)),
                "XYZ"
            ).to_matrix().to_4x4()
        else:
            R = Matrix.Identity(4)

        if node.scale is not None:
            sx, sy, sz = _vec3_to_tuple(node.scale)
            S = Matrix.Diagonal((sx, sy, sz, 1.0))
        else:
            S = Matrix.Identity(4)

        return T @ R @ S

    def walk(node, parent_obj, parent_world, depth, path):
        stats["nodes"] += 1

        name = node.name or "<unnamed>"
        meshes = node.meshes if hasattr(node, "meshes") else []
        children = node.children or []

        attrs = node.unk_data_mandatory
        lightMask = attrs.lightMask
        hit = attrs.hitAttributes
        cull = attrs.cullMode
        draw = attrs.drawMode
        wFlags = attrs.wFlags #used for heirarchy-based depth-sorting 

        prefix = f"{_indent(depth)}[{path}/{name}]"

        local = _node_local_matrix(node)
        world = parent_world @ local

        node_obj = None

        # -----------------------------
        # Single-mesh node
        # -----------------------------
        if len(meshes) == 1:
            stats["meshes_seen"] += 1
            mesh_entry = meshes[0]

            geom = _extract_geom(mesh_entry, debug=debug, prefix=prefix)
            if geom is not None:
                node_obj, mesh, mat_empty = _create_mesh_object(
                    name, geom, mesh_entry, debug=debug, prefix=prefix, context=context
                )
                if node_obj:
                    coll.objects.link(node_obj)
                    if parent_obj:
                        _parent_local(node_obj, parent_obj)
                        node_obj.matrix_basis = local
                    else:
                        node_obj.matrix_world = local

                    if name == "pPlane9_q00566":
                        print("=== Debugging pPlane9_q00566 ===")
                        node_obj.rotation_mode = 'XYZ'

                        # What you *intended* locally
                        print("scene local rot:", node.rotation)

                        # What your local matrix actually is (pre-Blender decomposition)
                        print("local matrix euler:", [math.degrees(a) for a in local.to_euler('XYZ')])

                        # What Blender shows after parenting+matrix_world assignment
                        print("blender rot_euler:", [math.degrees(a) for a in node_obj.rotation_euler])

                        # Also print parent scale to catch the usual culprit
                        if node_obj.parent:
                            ps = node_obj.parent.matrix_world.to_scale()
                            print("parent world scale:", ps)

                    props = node_obj.ttyd_world_mesh
                    ir = mesh_entry.local_ir
                    assert len(ir.positions) == len(ir.normals) == len(ir.uv0s) == len(ir.uv1s) == len(ir.colors), \
                        f"[IR] attribute array length mismatch on {name}"
                    for prim in ir.primitives:
                        for idx in prim.indices:
                            assert 0 <= idx < len(ir.positions), \
                                f"[IR] primitive index out of range on {name}: {idx} >= {len(ir.positions)}"
                            
                    props.has_nrm = bool(ir.normals) and any(n is not None for n in ir.normals)
                    props.has_uv0 = bool(ir.uv0s)    and any(u is not None for u in ir.uv0s)
                    props.has_uv1 = bool(ir.uv1s)    and any(u is not None for u in ir.uv1s)
                    props.has_col = bool(ir.colors)  and any(c is not None for c in ir.colors)

                    props.local_vertices.clear()
                    props.local_primitives.clear()

                    # --- vertices ---
                    for i in range(len(ir.positions)):
                        lv = props.local_vertices.add()
                        lv.pos = ir.positions[i]

                        if ir.normals and ir.normals[i] is not None:
                            lv.nrm = ir.normals[i]
                        if ir.uv0s and ir.uv0s[i] is not None:
                            lv.uv0 = ir.uv0s[i]
                        if ir.uv1s and ir.uv1s[i] is not None:
                            lv.uv1 = ir.uv1s[i]
                        if ir.colors and ir.colors[i] is not None:
                            r, g, b, a = ir.colors[i]
                            lv.col = (r / 255.0, g / 255.0, b / 255.0, a / 255.0)

                    # --- primitives ---
                    for prim in ir.primitives:
                        lp = props.local_primitives.add()
                        lp.opcode = prim.opcode
                        lp.indices = ",".join(str(i) for i in prim.indices)

                    props.ir_dirty = False
                    attr = node_obj.ttyd_attributes
                    attr.light_mask = lightMask
                    attr.draw_mode = draw
                    attr.cull_mode = cull_attributes_to_enum(cull)
                    attr.wFlags = wFlags
                    attr.hit_type = hit_attributes_to_enum(hit)
                    attr.hit_val = hit
                    
                    _preview_mat_with_drawmode(node_obj, mesh, props, attr, mat_empty, matprefix)

                    stats["meshes_built"] += 1
            else:
                stats["meshes_skipped"] += 1
                _dbg(debug, f"{prefix}  [SKIP mesh]")

        # -----------------------------
        # Empty transform holder
        # -----------------------------
        if node_obj is None:
            node_obj = bpy.data.objects.new(f"{matprefix}{name}", None)

            nodeProps = node_obj.ttyd_attributes
            nodeProps.light_mask = lightMask
            nodeProps.hit_val = hit
            nodeProps.hit_type = hit_attributes_to_enum(hit)
            nodeProps.cull_mode = cull_attributes_to_enum(cull)
            nodeProps.draw_mode = draw
            nodeProps.wFlags = wFlags #used for heirarchy-based depth-sorting """

            coll.objects.link(node_obj)
            stats["empties"] += 1
            if parent_obj:
                _parent_local(node_obj, parent_obj)
                node_obj.matrix_basis = local
            else:
                node_obj.matrix_world = local  # root

        # -----------------------------
        # Multi-mesh node
        # -----------------------------
        if len(meshes) > 1:
            node_obj.ttyd_world_empty.dmdObject = True

            for mi, mesh_entry in enumerate(meshes):
                stats["meshes_seen"] += 1
                geom = _extract_geom(mesh_entry, debug=debug, prefix=prefix)
                if geom is None:
                    stats["meshes_skipped"] += 1
                    _dbg(debug, f"{prefix}  [SKIP mesh[{mi}]]")
                    continue

                part_name = f"{name}__m{mi}"
                obj, mesh, mat_empty = _create_mesh_object(
                    part_name, geom, mesh_entry, debug=debug, prefix=prefix, context=context
                )
                if obj is None:
                    stats["meshes_skipped"] += 1
                    continue

                coll.objects.link(obj)
                _parent_local(obj, node_obj)
                obj.matrix_basis = Matrix.Identity(4)

                props = obj.ttyd_world_mesh
                props.meshFragment = True
                props.fragmentParent = node_obj.name

                ir = mesh_entry.local_ir
                assert len(ir.positions) == len(ir.normals) == len(ir.uv0s) == len(ir.uv1s) == len(ir.colors), \
                    f"[IR] attribute array length mismatch on {name}"
                for prim in ir.primitives:
                    for idx in prim.indices:
                        assert 0 <= idx < len(ir.positions), \
                            f"[IR] primitive index out of range on {name}: {idx} >= {len(ir.positions)}"

                props.has_nrm = bool(ir.normals) and any(n is not None for n in ir.normals)
                props.has_uv0 = bool(ir.uv0s)    and any(u is not None for u in ir.uv0s)
                props.has_uv1 = bool(ir.uv1s)    and any(u is not None for u in ir.uv1s)
                props.has_col = bool(ir.colors)  and any(c is not None for c in ir.colors)

                props.local_vertices.clear()
                props.local_primitives.clear()

                # --- vertices ---
                for i in range(len(ir.positions)):
                    lv = props.local_vertices.add()
                    lv.pos = ir.positions[i]

                    if ir.normals and ir.normals[i] is not None:
                        lv.nrm = ir.normals[i]
                    if ir.uv0s and ir.uv0s[i] is not None:
                        lv.uv0 = ir.uv0s[i]
                    if ir.uv1s and ir.uv1s[i] is not None:
                        lv.uv1 = ir.uv1s[i]
                    if ir.colors and ir.colors[i] is not None:
                        r, g, b, a = ir.colors[i]
                        lv.col = (r / 255.0, g / 255.0, b / 255.0, a / 255.0)

                # --- primitives ---
                for prim in ir.primitives:
                    lp = props.local_primitives.add()
                    lp.opcode = prim.opcode
                    lp.indices = ",".join(str(i) for i in prim.indices)

                props.ir_dirty = False

                attr = node_obj.ttyd_attributes
                attr.light_mask = lightMask
                attr.draw_mode = draw
                attr.cull_mode = cull_attributes_to_enum(cull)
                attr.wFlags = wFlags
                attr.hit_type = hit_attributes_to_enum(hit)
                attr.hit_val = hit
                _preview_mat_with_drawmode(obj, mesh, props, attr, mat_empty, matprefix)

                ref = node_obj.ttyd_world_empty.meshMembers.add()
                ref.obj = obj

                stats["meshes_built"] += 1

        for child in children:
            walk(child, node_obj, world, depth + 1, f"{path}/{name}")

    _dbg(debug, "=== TTYD build_geometry_from_scenegraph: START ===")
    walk(root_node, None, Matrix.Identity(4), 0, "")
    _dbg(debug, f"=== DONE: {stats} ===")
    return stats

def _preview_mat_with_drawmode(obj, mesh, props, attr, mat_empty, matprefix):
    if mat_empty is None:
        return
    props.emptyMaterial = mat_empty
    emptyProps = mat_empty.ttyd_world_material
    tevMode = emptyProps.tevConfig.tevMode

    if obj not in [u.obj for u in emptyProps.emptyMeshMembers]:
        used = emptyProps.emptyMeshMembers.add()
        used.obj = obj
        used.draw_mode = attr.draw_mode
        if attr.draw_mode > 3:
            print(f"drawmode: {attr.draw_mode}, {obj.name}")
        if emptyProps.tevConfig.tevMode != 0:
            print(f"tevmode: {emptyProps.tevConfig.tevMode}, {mat_empty.name}")

    material = bpy.data.materials.get(f"[DrawMode 0] {mat_empty.name}")
    o_nodes = material.node_tree.nodes
    o_links = material.node_tree.links

    if attr.cull_mode == 'BACK':
        material.use_backface_culling = True
    material = tevSwap(material, tevMode, o_nodes, o_links)
    
    if attr.draw_mode != 0:
        drawCheckMaterial = bpy.data.materials.get(f"[DrawMode {attr.draw_mode}] {mat_empty.name}")
        if drawCheckMaterial is None:
            newMat = material.copy()
            nodes = newMat.node_tree.nodes
            links = newMat.node_tree.links

            newMat.name = (f"[DrawMode {attr.draw_mode}] {mat_empty.name}")

            newRef = emptyProps.materialRefs.add()
            newRef.material = newMat

            if attr.draw_mode == 1: #Default material created--vtxCol/matSrc blended in
                newMat.blend_method = 'CLIP'

            if attr.draw_mode == 2: #Clipped texImage + blended alpha tex?
                newMat.blend_method = 'BLEND' #'MAYBE(?)' overrides material blend mode?
                
                stripMatSrc(nodes, links, tevMode)                

            elif attr.draw_mode == 3: #Blended alpha tex
                newMat.blend_method = 'BLEND'
        else:
            newMat = drawCheckMaterial

    else: #in the case of drawMode 0 we actually strip the matSrc rather than just returning the mat
        # this means technically default is DM 1, but it's essentially the 'base' we work from
        newMat = material
        nodes = newMat.node_tree.nodes
        links = newMat.node_tree.links

        stripMatSrc(nodes, links, tevMode)

    mesh.materials[0] = newMat
    props.previewMaterial = newMat

def tevSwap(material, tevMode, nodes, links):
    if tevMode == 0:
        return material
    elif tevMode == 1:
        tex0 = nodes.get("TEX0")
        tex1 = nodes.get("TEX1")
        color0 = nodes.get("Color0 Mix")
        color1 = nodes.get("Color1 Mix")
        alpha0 = nodes.get("Alpha0 Mix")
        alpha1 = nodes.get("Alpha1 Mix")
        shadermix = nodes.get("Shader Mix")

        if (
            color0 is not None
            and color1 is not None
            and alpha1 is not None
            and color1.type == 'VECT_MATH'
            and alpha1.type == 'VECT_MATH'
        ):
            newcol1 = nodes.new(type='ShaderNodeMixRGB')
            newcol1.location = color1.location
            col1NameBackup = color1.name
            alp1NameBackup = alpha1.name

            nodes.remove(color1)
            nodes.remove(alpha1)
            newcol1.name = col1NameBackup

            links.new(tex0.outputs['Color'], newcol1.inputs[1])
            links.new(tex1.outputs['Color'], newcol1.inputs[2])
            newcol1.inputs[0].default_value = 0.0
            links.new(newcol1.outputs['Color'], color0.inputs[0])

            if alpha0 is not None:
                links.new(tex0.outputs['Alpha'], alpha0.inputs[0])
            else:
                links.new(tex0.outputs['Alpha'], shadermix.inputs['Fac'])

        return material
    elif tevMode == 7:
        tex0 = nodes.get("TEX0")
        tex1 = nodes.get("TEX1")
        color0 = nodes.get("Color0 Mix")
        color1 = nodes.get("Color1 Mix")
        alpha0 = nodes.get("Alpha0 Mix")
        alpha1 = nodes.get("Alpha1 Mix")
        shadermix = nodes.get("Shader Mix")

        if (
            color0 is not None
            and color1 is not None
            and alpha1 is not None
            and color1.type == 'VECT_MATH'
            and alpha1.type == 'VECT_MATH'
        ):
            newcol1 = nodes.new(type='ShaderNodeMixRGB')
            newalpha1 = nodes.new(type='ShaderNodeMix')
            newcol1.location = color1.location
            newalpha1.location = alpha1.location
            col1NameBackup = color1.name
            alp1NameBackup = alpha1.name

            nodes.remove(color1)
            nodes.remove(alpha1)
            newcol1.name = col1NameBackup
            newalpha1.name = alp1NameBackup

            links.new(tex0.outputs['Color'], newcol1.inputs[1])
            links.new(tex1.outputs['Color'], newcol1.inputs[2])
            links.new(tex1.outputs['Alpha'], newcol1.inputs[0])
            links.new(newcol1.outputs['Color'], color0.inputs[0])

            links.new(tex1.outputs['Alpha'], newalpha1.inputs[0])
            links.new(tex0.outputs['Alpha'], newalpha1.inputs[2])
            newalpha1.inputs[3].default_value = 1.0
            if alpha0 is not None:
                links.new(newalpha1.outputs['Result'], alpha0.inputs[0])
            else:
                links.new(newalpha1.outputs['Result'], shadermix.inputs['Fac'])

        return material
    else:
        return material

def stripMatSrc(nodes, links, tevMode):
    color0mix = nodes.get("Color0 Mix")
    color0 = nodes.get("Color0")
    diffuse = nodes.get("Diffuse")
    tex0 = nodes.get("TEX0")
    tex1 = nodes.get("TEX1")

    #nodes.remove(color0mix)
    if color0 is not None and color0.type == 'RGB':
        nodes.remove(color0)
        if color0mix is not None:
            nodes.remove(color0mix)
        if tex1 is not None:
            color1mix = nodes.get("Color1 Mix")
            links.new(color1mix.outputs['Vector'], diffuse.inputs['Color'])
        elif tex0 is not None:
            links.new(tex0.outputs['Color'], diffuse.inputs['Color'])