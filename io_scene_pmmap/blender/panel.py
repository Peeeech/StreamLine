import bpy #type: ignore
import bmesh #type: ignore
from enum import IntEnum

"""
==============================
    Simple Helpers
==============================
"""
GX_TRIANGLES = 0x90
GX_QUADS = 0x80

class TTYDHitType:
    NONE  = 'NONE'
    WATER = 'WATER'
    SPIKE = 'SPIKE'
    PLANE = 'PLANE'
    BOAT  = 'BOAT'

class TTYDCullMode: # What gets culled, not what stays
    FRONT = 'FRONT'
    BACK = 'BACK'
    ALL = 'ALL'
    NONE = 'NONE'

class GXWrapMode(IntEnum):
    CLAMP  = 0
    REPEAT = 1
    MIRROR = 2

class LIGHT_MAP:
    ambientLight = 'ambientLight'
    pointLight = 'pointLight'
    directionalLight = 'directionalLight' 
    spotLight = 'spotLight'

class MATSRC:
    GX_SRC_REG = 'matCol'
    GX_SRC_VTX = 'vtxCol'

class BLENDMODE:
    OPAQUE = 'opaque'
    CLIP = 'clip'
    FULL = 'full'

def _clear_collection(col):
    col.clear()

def _read_color_value(av):
    # Blender color attribute value objects
    if hasattr(av, "color"):
        c = av.color  # length 4
        return (float(c[0]), float(c[1]), float(c[2]), float(c[3]))

    # Fallbacks (rare, but prevents silent zeroing)
    if hasattr(av, "value"):
        v = float(av.value)
        return (v, v, v, 1.0)

    if hasattr(av, "vector"):
        v = av.vector
        if len(v) == 4:
            return (float(v[0]), float(v[1]), float(v[2]), float(v[3]))
        if len(v) == 3:
            return (float(v[0]), float(v[1]), float(v[2]), 1.0)

    return (0.0, 0.0, 0.0, 0.0)

"""
==============================
    Registered Helpers
==============================
"""

class TTYDMeshMemberRef(bpy.types.PropertyGroup):
    obj: bpy.props.PointerProperty(
        type=bpy.types.Object
    ) #type: ignore

class TTYDEmptyMatMeshMemberRef(bpy.types.PropertyGroup):
    obj: bpy.props.PointerProperty(
        type=bpy.types.Object
    ) #type: ignore
    draw_mode: bpy.props.IntProperty() #type: ignore

class TTYDEmptyMainMaterialRef(bpy.types.PropertyGroup):
    material: bpy.props.PointerProperty(
        type=bpy.types.Material
    ) #type: ignore
    drawMode: bpy.props.IntProperty() #type: ignore

class TEVConfig(bpy.types.PropertyGroup):
    tevMode: bpy.props.IntProperty(
        name="TEV Mode",
        description="GX TEV mode / preset identifier"
    ) #type: ignore

class SamplerTEX(bpy.types.PropertyGroup):
    image: bpy.props.PointerProperty(
        type=bpy.types.Image,
        name="Texture Image"
    ) #type: ignore
    name: bpy.props.StringProperty() #type: ignore
    render_order: bpy.props.IntProperty(
        description="Higher = render first (afaik up to 6?)"
    ) #type: ignore
    wWidth: bpy.props.IntProperty() #type: ignore
    wHeight: bpy.props.IntProperty() #type: ignore

class texCoordTransform(bpy.types.PropertyGroup):
    translateX: bpy.props.FloatProperty() #type: ignore
    translateY: bpy.props.FloatProperty() #type: ignore
    scaleX: bpy.props.FloatProperty() #type: ignore
    scaleY: bpy.props.FloatProperty() #type: ignore
    rotateZ: bpy.props.FloatProperty() #type: ignore
    warpX: bpy.props.FloatProperty() #type: ignore
    warpY: bpy.props.FloatProperty() #type: ignore

class Sampler(bpy.types.PropertyGroup):
    wrapS: bpy.props.IntProperty() #type: ignore
    wrapT: bpy.props.IntProperty() #type: ignore
    unk_0a: bpy.props.IntProperty() #type: ignore
    unk_0b: bpy.props.IntProperty() #type: ignore

    texture: bpy.props.PointerProperty(type=SamplerTEX) #type: ignore
    texCoord: bpy.props.PointerProperty(type=texCoordTransform) #type: ignore
    
    showImage: bpy.props.BoolProperty(default=True) #type: ignore
    showTexCoord: bpy.props.BoolProperty(default=False) #type: ignore

class curveData(bpy.types.PropertyGroup):
    pos: bpy.props.FloatVectorProperty(size=3) #type: ignore
    param: bpy.props.FloatVectorProperty(size=3) #type: ignore

class TTYD_OT_add_sampler(bpy.types.Operator):
    bl_idname = "ttyd.add_sampler"
    bl_label = "Add Texture Sampler"
    bl_description = "Add a new texture sampler to this material"
    bl_options = {'UNDO'}

    def execute(self, context):
        obj = context.object
        if not obj or not hasattr(obj, "ttyd_world_material"):
            return {'CANCELLED'}

        mat = obj.ttyd_world_material

        sampler = mat.textureSamplers.add()

        # Optional: initialize defaults
        sampler.wrapS = 0
        sampler.wrapT = 0

        mat.numTextures = len(mat.textureSamplers)

        return {'FINISHED'}
    
class TTYD_OT_remove_sampler(bpy.types.Operator):
    bl_idname = "ttyd.remove_sampler"
    bl_label = "Remove Texture Sampler"
    bl_description = "Remove a texture sampler from this material"
    bl_options = {'UNDO'}

    index: bpy.props.IntProperty() #type: ignore

    def execute(self, context):
        obj = context.object
        if not obj or not hasattr(obj, "ttyd_world_material"):
            return {'CANCELLED'}

        mat = obj.ttyd_world_material

        if self.index < 0 or self.index >= len(mat.textureSamplers):
            return {'CANCELLED'}

        mat.textureSamplers.remove(self.index)
        mat.numTextures = len(mat.textureSamplers)

        return {'FINISHED'}

class TTYD_OT_add_joint_anim_track(bpy.types.Operator):
    bl_idname = "ttyd.add_joint_anim_track"
    bl_label = "Add Joint Anim Track"
    bl_description = "Add a new joint animation track"
    bl_options = {'UNDO'}

    def execute(self, context):
        # Wherever you store the anim props (adjust if not context.object)
        obj = context.object
        if not obj or not hasattr(obj, "ttyd_world_animation"):
            return {'CANCELLED'}

        animProps = obj.ttyd_world_animation
        jt = animProps.joint_table

        track = jt.tracks.add()

        # Reasonable defaults so UI + exporter don't choke
        track.name = f"track_{len(jt.tracks)-1:02d}"
        track.keyframeCount = 0

        # If you have these properties, initialize them safely
        # (comment out if they don't exist)
        try:
            track.anim_delta = (0.0, 0.0, 0.0)
        except Exception:
            pass

        # Keep count consistent with actual list length
        jt.count = len(jt.tracks)

        return {'FINISHED'}

class TTYD_OT_remove_joint_anim_track(bpy.types.Operator):
    bl_idname = "ttyd.remove_joint_anim_track"
    bl_label = "Remove Joint Anim Track"
    bl_description = "Remove a joint animation track"
    bl_options = {'UNDO'}

    index: bpy.props.IntProperty()  # type: ignore

    def execute(self, context):
        obj = context.object
        if not obj or not hasattr(obj, "ttyd_world_animation"):
            return {'CANCELLED'}

        animProps = obj.ttyd_world_animation
        jt = animProps.joint_table

        if self.index < 0 or self.index >= len(jt.tracks):
            return {'CANCELLED'}

        jt.tracks.remove(self.index)
        jt.count = len(jt.tracks)

        return {'FINISHED'}

class TTYD_OT_sync_joint_anim_delta_from_loc(bpy.types.Operator):
    bl_idname = "ttyd.sync_joint_anim_delta_from_loc"
    bl_label = "Sync Delta from Location"
    bl_description = "Set anim_delta to the joint object's current location"
    bl_options = {'UNDO'}

    index: bpy.props.IntProperty()  # type: ignore

    def execute(self, context):
        obj = context.object
        if not obj or not hasattr(obj, "ttyd_world_animation"):
            return {'CANCELLED'}

        animProps = obj.ttyd_world_animation
        jt = animProps.joint_table

        if self.index < 0 or self.index >= len(jt.tracks):
            return {'CANCELLED'}

        track = jt.tracks[self.index]
        joint = getattr(track, "joint", None)

        # Expecting track.joint is a PointerProperty to an Object
        if joint is None or getattr(joint, "type", None) is None:
            self.report({'WARNING'}, "Track has no joint assigned.")
            return {'CANCELLED'}

        # Use local-space location (what you see in the N-panel Item/Transform)
        loc = joint.location
        track.anim_delta = (float(loc.x), float(loc.y), float(loc.z))

        return {'FINISHED'}

class TTYD_OT_sync_joint_anim_tracks(bpy.types.Operator):
    bl_idname = "ttyd.sync_joint_anim_tracks"
    bl_label = "Sync Joint Tracks"
    bl_description = "Resize joint track collection to match Track Count"
    bl_options = {'UNDO'}

    def execute(self, context):
        obj = context.object
        if not obj or not hasattr(obj, "ttyd_world_animation"):
            return {'CANCELLED'}

        animProps = obj.ttyd_world_animation
        jt = animProps.joint_table

        desired = max(0, int(jt.count))
        current = len(jt.tracks)

        if desired > current:
            for _ in range(desired - current):
                t = jt.tracks.add()
                t.name = f"track_{len(jt.tracks)-1:02d}"
                t.keyframeCount = 0
                try:
                    t.anim_delta = (0.0, 0.0, 0.0)
                except Exception:
                    pass
        elif desired < current:
            for _ in range(current - desired):
                jt.tracks.remove(len(jt.tracks) - 1)

        # enforce exact match
        jt.count = len(jt.tracks)
        return {'FINISHED'}

class TTYD_OT_select_object(bpy.types.Operator):
    bl_idname = "ttyd.select_object"
    bl_label = "Select Object"
    bl_description = "Select and focus this object"

    object_name: bpy.props.StringProperty() #type: ignore

    def execute(self, context):
        obj = bpy.data.objects.get(self.object_name)
        if not obj:
            return {'CANCELLED'}

        # Deselect all
        bpy.ops.object.select_all(action='DESELECT')

        # Select + activate
        obj.select_set(True)
        context.view_layer.objects.active = obj

        return {'FINISHED'}

def quantize(v, precision=5):
    return tuple(round(x, precision) for x in v)

class TTYD_OT_rebuild_local_ir(bpy.types.Operator):
    bl_idname = "ttyd.rebuild_local_ir"
    bl_label = "Rebuild Local IR"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh object.")
            return {'CANCELLED'}

        props = obj.ttyd_world_mesh

        # Force Blender to consider mesh data “dirty” and refresh evaluation
        obj.data.update()                 # tags mesh datablock for update
        obj.update_tag(refresh={'DATA'})  # ensure depsgraph sees data-layer changes
        context.view_layer.update()       # evaluate depsgraph now

        depsgraph = context.evaluated_depsgraph_get()
        eval_obj = obj.evaluated_get(depsgraph)
        eval_mesh = eval_obj.to_mesh(preserve_all_data_layers=True, depsgraph=depsgraph)

        try:
            # Ensure triangulation view without destroying CORNER layers
            eval_mesh.calc_loop_triangles()

            # ---- detect available attributes ----
            has_nrm = True
            has_uv0 = len(eval_mesh.uv_layers) >= 1
            has_uv1 = len(eval_mesh.uv_layers) >= 2

            # choose first layers consistently
            uv0 = eval_mesh.uv_layers[0].data if has_uv0 else None
            uv1 = eval_mesh.uv_layers[1].data if has_uv1 else None

            # ---- COLOR: Prefer "Col" explicitly (importer/exporter contract) ----
            ca = None
            if eval_mesh.color_attributes:
                ca = eval_mesh.color_attributes.get("Col")
                if ca is None:
                    ca = eval_mesh.color_attributes.active or eval_mesh.color_attributes[0]

            col_layer = None
            if ca and ca.data_type == 'BYTE_COLOR' and ca.domain == 'CORNER':
                expected = len(eval_mesh.loops) if ca.domain == 'CORNER' else len(eval_mesh.vertices)
                if expected > 0 and len(ca.data) == expected:
                    col_layer = ca.data

            has_col = bool(col_layer)

            props.has_nrm = has_nrm
            props.has_uv0 = has_uv0
            props.has_uv1 = has_uv1
            props.has_col = has_col

            # ---- rebuild IR ----
            _clear_collection(props.local_vertices)
            _clear_collection(props.local_primitives)

            vertex_map = {}
            tri_indices = []

            # Build expanded vertex stream using loop triangles (guaranteed tris)
            for tri in eval_mesh.loop_triangles:
                loops = tri.loops
                loops = (loops[0], loops[2], loops[1])

                for li in loops:
                    loop = eval_mesh.loops[li]
                    v = eval_mesh.vertices[loop.vertex_index]

                    # Build a unique key per vertex
                    
                    pos = tuple(v.co)
                    nrm = (loop.normal.x, loop.normal.y, loop.normal.z)
                    uv0_val = tuple(uv0[li].uv) if uv0 else None
                    uv1_val = tuple(uv1[li].uv) if uv1 else None
                    col_val = tuple(_read_color_value(col_layer[li])) if col_layer and ca.domain == 'CORNER' else tuple(_read_color_value(col_layer[loop.vertex_index])) if col_layer else None
                    
                    key = (
                        quantize(pos),
                        quantize(nrm) if has_nrm else None,
                        quantize(uv0_val) if has_uv0 else None,
                        quantize(uv1_val) if has_uv1 else None,
                        col_val if has_col else None
                    )

                    if key in vertex_map:
                        idx = vertex_map[key]
                    else:
                        lv = props.local_vertices.add()
                        idx = len(props.local_vertices) - 1

                        lv.pos = v.co[:]

                        n = loop.normal
                        lv.nrm = (n.x, n.y, n.z)

                        if uv0:
                            u = uv0[li].uv
                            lv.uv0 = (u.x, 1.0 - u.y)
                        else:
                            lv.uv0 = (0.0, 0.0)

                        if uv1:
                            u = uv1[li].uv
                            lv.uv1 = (u.x, 1.0 - u.y)
                        else:
                            lv.uv1 = (0.0, 0.0)

                        if col_layer:
                            if ca.domain == 'CORNER':
                                lv.col = _read_color_value(col_layer[li])
                            else:
                                lv.col = _read_color_value(col_layer[loop.vertex_index])
                        else:
                            lv.col = (0.0, 0.0, 0.0, 0.0)

                        vertex_map[key] = idx

                    tri_indices.append(idx)

            # One primitive packet: triangles over the entire expanded vertex list
            # ---- build triangle index buffer ----

            props.local_tri_indices = ",".join(map(str, tri_indices))


            # ---- build triangle primitives (unchanged behavior) ----
            for i in range(0, len(tri_indices), 3):
                prim = props.local_primitives.add()
                prim.opcode = GX_TRIANGLES
                prim.indices = f"{tri_indices[i]},{tri_indices[i+1]},{tri_indices[i+2]}"

            props.ir_dirty = False
            self.report({'INFO'}, f"Built Local IR: {len(props.local_vertices)} verts, 1 prim stream")
            return {'FINISHED'}

        finally:
            # Important: free evaluated mesh
            eval_obj.to_mesh_clear()
   
class TTYD_OT_rebuild_camroad_ir(bpy.types.Operator):
    bl_idname = "ttyd.rebuild_camroad_ir"
    bl_label = "Rebuild CamRoad IR"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):

        obj = context.object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "Select a mesh object.")
            return {'CANCELLED'}

        props = obj.ttyd_world_mesh

        if not props.isCamRoadRegion:
            self.report({'ERROR'}, "Mesh is not marked as CamRoad Region.")
            return {'CANCELLED'}

        mesh = obj.data

        _clear_collection(props.local_vertices)
        _clear_collection(props.local_primitives)

        vert_cursor = 0

        for poly in mesh.polygons:

            prim_indices = []

            for vid in poly.vertices:

                v = mesh.vertices[vid]

                lv = props.local_vertices.add()
                lv.pos = v.co[:]

                prim_indices.append(vert_cursor)
                vert_cursor += 1

            prim = props.local_primitives.add()

            # opcode is basically irrelevant for camRoad,
            # but keep GX_QUADS-style placeholder for consistency
            prim.opcode = 0x80
            prim.indices = ",".join(str(i) for i in prim_indices)

        props.has_nrm = False
        props.has_uv0 = False
        props.has_uv1 = False
        props.has_col = False
        props.ir_dirty = False

        self.report(
            {'INFO'},
            f"Built CamRoad IR: {len(props.local_vertices)} verts, {len(props.local_primitives)} polygons"
        )

        return {'FINISHED'}



class TTYD_OT_stripify_mesh(bpy.types.Operator):
    bl_idname = "ttyd.stripify_mesh"
    bl_label = "Stripify Mesh"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        self.report({'WARNING'}, "Stripify not implemented yet. Use Rebuild Local IR (triangles) for now.")
        return {'CANCELLED'}

"""
==============================
    Top Level Empty / Mesh Properties
==============================
"""

#region: 'ttyd_world_empty'
class TTYDWorldEmptyProperties(bpy.types.PropertyGroup):
    dmdObject: bpy.props.BoolProperty(default=False) #type: ignore
    meshMembers: bpy.props.CollectionProperty(
        type=TTYDMeshMemberRef
    ) #type: ignore
    isLight: bpy.props.BoolProperty(default=False) #type: ignore
    isMaterial: bpy.props.BoolProperty(default=False) #type: ignore
    isTexture: bpy.props.BoolProperty(default=False) #type: ignore
    isAnimation: bpy.props.BoolProperty(default=False) #type: ignore

#region: 'ttyd_world_mesh'
class TTYDLocalVertex(bpy.types.PropertyGroup):
    pos: bpy.props.FloatVectorProperty(
        name="Position",
        size=3,
        subtype='XYZ'
    )  # type: ignore

    nrm: bpy.props.FloatVectorProperty(
        name="Normal",
        size=3,
        subtype='XYZ'
    )  # type: ignore

    uv0: bpy.props.FloatVectorProperty(
        name="UV0",
        size=2,
        subtype='COORDINATES'
    )  # type: ignore

    uv1: bpy.props.FloatVectorProperty(
        name="UV1",
        size=2,
        subtype='COORDINATES'
    )  # type: ignore

    col: bpy.props.FloatVectorProperty(
        name="Color",
        size=4,
        subtype='COLOR_GAMMA',
        min=0.0,
        max=1.0
    )  # type: ignore

class TTYDLocalPrimitive(bpy.types.PropertyGroup):
    opcode: bpy.props.IntProperty()#type: ignore
    indices: bpy.props.StringProperty()#type: ignore

class TTYDWorldMeshProperties(bpy.types.PropertyGroup):
    local_vertices: bpy.props.CollectionProperty(type=TTYDLocalVertex)#type: ignore
    local_primitives: bpy.props.CollectionProperty(type=TTYDLocalPrimitive)#type: ignore

    ir_dirty: bpy.props.BoolProperty(
        name="IR Out of Date",
        default=False
    ) #type: ignore

    showIR: bpy.props.BoolProperty(default=False) #type: ignore

    has_nrm: bpy.props.BoolProperty(default=False) #type: ignore
    has_uv0: bpy.props.BoolProperty(default=False) #type: ignore
    has_uv1: bpy.props.BoolProperty(default=False) #type: ignore
    has_col: bpy.props.BoolProperty(default=False) #type: ignore

    meshFragment: bpy.props.BoolProperty(default=False) #type: ignore
    fragmentParent: bpy.props.StringProperty() #type: ignore
    emptyMaterial: bpy.props.PointerProperty(
        name="Empty Material Data",
        type=bpy.types.Object
    ) #type: ignore
    previewMaterial: bpy.props.PointerProperty(
        name="Preview Material",
        type=bpy.types.Material
    ) #type: ignore

    isCamRoadRegion: bpy.props.BoolProperty(default=False) #type: ignore
    bbox_min: bpy.props.FloatVectorProperty(size=3) #type: ignore
    bbox_max: bpy.props.FloatVectorProperty(size=3) #type: ignore

#region: 'ttyd_world_curve'
class TTYDWorldCurveProperties(bpy.types.PropertyGroup):
    Marker: bpy.props.PointerProperty(
        name="Camera Road Marker",
        type=bpy.types.Object
    ) #type: ignore
    wbLockY: bpy.props.IntProperty() #type: ignore
    wLockedYVal: bpy.props.FloatProperty() #type: ignore
    bDisabled: bpy.props.IntProperty() #type: ignore
    # pad 20
    clampStartSegment: bpy.props.IntProperty() #type: ignore
    clampEndSegment: bpy.props.IntProperty() #type: ignore
    clampMaxDistanceLeft: bpy.props.FloatProperty() #type: ignore
    clampMaxDistanceRight: bpy.props.FloatProperty() #type: ignore
    clampStartSegmentProgress: bpy.props.FloatProperty() #type: ignore
    clampEndSegmentProgress: bpy.props.FloatProperty() #type: ignore
    wCameraToTargetDistance: bpy.props.FloatProperty() #type: ignore
    # unk 8
    camElevationDegrees: bpy.props.FloatProperty() #type: ignore
    # unk 8
    camPitchDegrees: bpy.props.FloatProperty() #type: ignore
    # unk 8
    shiftXRate: bpy.props.FloatProperty() #type: ignore
    unk_80: bpy.props.FloatProperty() #type: ignore
    wbEnableClamping: bpy.props.IntProperty() #type: ignore
    bbox_min: bpy.props.FloatVectorProperty(size=3) #type: ignore
    bbox_max: bpy.props.FloatVectorProperty(size=3) #type: ignore
    curve_data_count: bpy.props.IntProperty() #type: ignore
    geometry_count: bpy.props.IntProperty() #type: ignore
    zero: bpy.props.IntProperty() #type: ignore
    unk_count: bpy.props.IntProperty() #type: ignore

    localCurveIR: bpy.props.CollectionProperty(type=curveData) #type: ignore


"""
==============================
    Secondary Empty Properties
==============================
"""
#region: 'ttyd_attributes'
class TTYDJointAttributes(bpy.types.PropertyGroup):
    origin_offset: bpy.props.FloatVectorProperty(size=3) #type: ignore #anim_delta pushed to here for obj-specific I/O purposes
    light_mask: bpy.props.IntProperty() #type: ignore
    draw_mode: bpy.props.IntProperty() #type: ignore
    cull_mode: bpy.props.EnumProperty(
        name="Cull Mode",
        description="TTYD GX Culling Mode",
        items=[
            (TTYDCullMode.FRONT, "Front", "Only back visible"),
            (TTYDCullMode.BACK, "Back", "Only front visible"),
            (TTYDCullMode.ALL,  "All",  "Completely invisible"),
            (TTYDCullMode.NONE, "None", "Front and back visible"),
        ],
        default=TTYDCullMode.NONE,
    ) #type: ignore
    wFlags: bpy.props.IntProperty(
        description="18 = Heirarchy-based depth-sorting for children."
    ) #type: ignore
    hit_type: bpy.props.EnumProperty(
        name="Hit Type (ONLY EFFECTIVE IN HIT COLLECTION)",
        description="TTYD hitbox interaction type",
        items=[
            (TTYDHitType.NONE,  "None",  "No special interaction"),
            (TTYDHitType.WATER, "Water", "Water hazard"),
            (TTYDHitType.SPIKE, "Spike", "Spike hazard"),
            (TTYDHitType.PLANE, "Plane", "Paper Plane panel"),
            (TTYDHitType.BOAT,  "Boat",  "Paper Boat panel"),
        ],
        default=TTYDHitType.NONE,
    ) #type: ignore
    hit_val: bpy.props.IntProperty() #type: ignore

#region: 'ttyd_world_texture'
class TTYDEmptyTextureProperties(bpy.types.PropertyGroup):
    index: bpy.props.IntProperty() #type: ignore

    name: bpy.props.StringProperty(
        name="Texture Name",
        default=""
    ) #type: ignore
    render_order: bpy.props.IntProperty() #type: ignore

    # ---- Dimensions / format ----
    width: bpy.props.IntProperty() #type: ignore
    height: bpy.props.IntProperty() #type: ignore
    format: bpy.props.IntProperty() #type: ignore

    # ---- Sampler state ----
    wrap_s: bpy.props.IntProperty() #type: ignore
    wrap_t: bpy.props.IntProperty() #type: ignore
    min_filter: bpy.props.IntProperty() #type: ignore
    mag_filter: bpy.props.IntProperty() #type: ignore

    # ---- LOD ----
    lod_bias: bpy.props.FloatProperty() #type: ignore
    edge_lod_enable: bpy.props.BoolProperty() #type: ignore
    min_lod: bpy.props.IntProperty() #type: ignore
    max_lod: bpy.props.IntProperty() #type: ignore

#region: 'ttyd_world_material'
class TTYDEmptyMaterialProperties(bpy.types.PropertyGroup):
    """
    First four are appended to materialEmpty for Blender Preview/Navigation purposes
    """
    materialRefs: bpy.props.CollectionProperty(
        type=TTYDEmptyMainMaterialRef
        ) #type: ignore
    emptyMeshMembers: bpy.props.CollectionProperty(
        type=TTYDEmptyMatMeshMemberRef
        ) #type: ignore
    showBlenderData: bpy.props.BoolProperty(default=False) #type: ignore
    draw_mode: bpy.props.IntProperty() #type: ignore
    
    """
    Actual DmdMaterial properties
    """
    name: bpy.props.StringProperty() #type: ignore
    color: bpy.props.IntVectorProperty(size=4) #type: ignore
    matSrc: bpy.props.EnumProperty(
        name="matSrc",
        description="TTYD GX Material Source (Vertex Colors / Single Material Color)",
        items=[
            (MATSRC.GX_SRC_REG, "Material Color", "Uses the Vector4 RGBA Values as a flat color for the 'light source'"),
            (MATSRC.GX_SRC_VTX, "Vertex Colors", "Uses the related mesh's vector colors as the 'light source'"),
        ]
    ) #type: ignore
    unk_009: bpy.props.IntProperty() #type: ignore
    blendMode: bpy.props.EnumProperty(
        name="blendMode",
        description="TTYD GX Material Blend Mode (Color / Alpha)",
        items=[
            (BLENDMODE.OPAQUE, "Opaque", "No vtex transparency mixed into final color"),
            (BLENDMODE.CLIP, "CLIP", "Pixels fully discarded when under half transparency"),
            (BLENDMODE.FULL, "Full", "Vtex alpha subtracted"),
        ]
    ) #type: ignore
    numTextures: bpy.props.IntProperty() #type: ignore
    #texCoords embedded in sampler data to preserve index
    showSamplers: bpy.props.BoolProperty(default=True) #type: ignore
    blendAlphaModulationR: bpy.props.IntVectorProperty(size=4) #type: ignore
    textureSamplers: bpy.props.CollectionProperty(type=Sampler) #type: ignore
    tevConfig: bpy.props.PointerProperty(type=TEVConfig) #type: ignore

#region: 'ttyd_world_light'
class TTYDLightProperties(bpy.types.PropertyGroup): 
    """Data ref for exporter. Very well could pull some from sceneGraph on exp, but by linking all data 1:1 it'll make for seamless obj creation"""
    type: bpy.props.EnumProperty(
        name="type",
        description="TTYD GX Light Object type",
        items=[
            (LIGHT_MAP.ambientLight, "Ambient", "Constant additive light applied uniformly to all shaded vertices"), #World-Nodes-simulation
            (LIGHT_MAP.pointLight, "Point", "Position-based omnidirectional vertex light with distance attenuation"), #POINT (with custom math)
            (LIGHT_MAP.directionalLight,  "Directional",  "Infinite-distance directional light affecting all vertices equally"), #SUN
            (LIGHT_MAP.spotLight, "Spot", "Position-based directional light with angular cone and attenuation"), #SPOT
        ],
        default=LIGHT_MAP.pointLight,
    ) #type: ignore
    base_color: bpy.props.IntVectorProperty(size=4) #type: ignore
    multiplier: bpy.props.FloatVectorProperty(size=4) #type: ignore
    spotAngle: bpy.props.FloatProperty() #type: ignore
    angularAttenuation: bpy.props.FloatProperty() #type: ignore
    distanceAttenuationType: bpy.props.IntProperty() #type: ignore
    wFlags: bpy.props.IntProperty() #type: ignore
    enableFlags: bpy.props.IntProperty() #type: ignore

#region: anim table helpers

    # anim tracks
class TTYDJointAnimTrack(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty() #type: ignore
    joint: bpy.props.PointerProperty(type=bpy.types.Object) #type: ignore
    anim_origin: bpy.props.FloatVectorProperty(size=3) #type: ignore        #------- Might just be able to use val from keyframe 0?
    anim_rotation: bpy.props.FloatVectorProperty(size=3) #type: ignore      #------- ^ ^ ^ ^
    anim_scale: bpy.props.FloatVectorProperty(size=3) #type: ignore         #------- ^ ^ ^ ^
    anim_delta: bpy.props.FloatVectorProperty(size=3) #type: ignore
    keyframeCount: bpy.props.IntProperty() #type: ignore

    action: bpy.props.PointerProperty(type=bpy.types.Action) #type: ignore

class TTYDUVAnimTrack(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty() #type: ignore
    samplerIndex: bpy.props.IntProperty() #type: ignore
    mat: bpy.props.PointerProperty(type=bpy.types.Object) #type: ignore
    mat_v: bpy.props.PointerProperty(type=bpy.types.Object) #type: ignore
    mat_v_x: bpy.props.PointerProperty(type=bpy.types.Object) #type: ignore
    skew: bpy.props.FloatVectorProperty(size=2) #type: ignore

    action: bpy.props.PointerProperty(type=bpy.types.Action) #type: ignore

class TTYDAlphaAnimTrack(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty() #type: ignore
    mat: bpy.props.PointerProperty(type=bpy.types.Object) #type: ignore
    mat_v: bpy.props.PointerProperty(type=bpy.types.Object) #type: ignore
    mat_v_x: bpy.props.PointerProperty(type=bpy.types.Object) #type: ignore

    action: bpy.props.PointerProperty(type=bpy.types.Action) #type: ignore

class TTYDLightTransAnimTrack(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty() #type: ignore
    light: bpy.props.PointerProperty(type=bpy.types.Object) #type: ignore
    anim_origin: bpy.props.FloatVectorProperty(size=3) #type: ignore        #------- Might just be able to use val from keyframe 0?
    anim_rotation: bpy.props.FloatVectorProperty(size=3) #type: ignore      #------- ^ ^ ^ ^
    anim_scale: bpy.props.FloatVectorProperty(size=3) #type: ignore         #------- ^ ^ ^ ^
    keyframeCount: bpy.props.IntProperty() #type: ignore

    action: bpy.props.PointerProperty(type=bpy.types.Action) #type: ignore

class TTYDLightParamAnimTrack(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty() #type: ignore
    light: bpy.props.PointerProperty(type=bpy.types.Object) #type: ignore

    action: bpy.props.PointerProperty(type=bpy.types.Action) #type: ignore

    # anim tables

class TTYDJointAnimTable(bpy.types.PropertyGroup):
    count: bpy.props.IntProperty() #type: ignore
    tracks: bpy.props.CollectionProperty(type=TTYDJointAnimTrack) #type: ignore

class TTYDUVAnimTable(bpy.types.PropertyGroup):
    count: bpy.props.IntProperty() #type: ignore
    tracks: bpy.props.CollectionProperty(type=TTYDUVAnimTrack) #type: ignore

class TTYDAlphaAnimTable(bpy.types.PropertyGroup):
    count: bpy.props.IntProperty() #type: ignore
    tracks: bpy.props.CollectionProperty(type=TTYDAlphaAnimTrack) #type: ignore

class TTYDLightTransAnimTable(bpy.types.PropertyGroup):
    count: bpy.props.IntProperty() #type: ignore
    tracks: bpy.props.CollectionProperty(type=TTYDLightTransAnimTrack) #type: ignore

class TTYDLightParamAnimTable(bpy.types.PropertyGroup):
    count: bpy.props.IntProperty() #type: ignore
    tracks: bpy.props.CollectionProperty(type=TTYDLightParamAnimTrack) #type: ignore
    

#region: 'ttyd_world_animation'
class TTYDEmptyAnimationProperties(bpy.types.PropertyGroup):

    name: bpy.props.StringProperty() #type: ignore
    length: bpy.props.FloatProperty() #type: ignore

    joint: bpy.props.BoolProperty(default=False) #type: ignore
    uv: bpy.props.BoolProperty(default=False) #type: ignore
    alpha: bpy.props.BoolProperty(default=False) #type: ignore
    lightT: bpy.props.BoolProperty(default=False) #type: ignore
    lightP: bpy.props.BoolProperty(default=False) #type: ignore

    joint_table: bpy.props.PointerProperty(type=TTYDJointAnimTable) #type: ignore
    uv_table: bpy.props.PointerProperty(type=TTYDUVAnimTable) #type: ignore
    alpha_table: bpy.props.PointerProperty(type=TTYDAlphaAnimTable) #type: ignore
    lightT_table: bpy.props.PointerProperty(type=TTYDLightTransAnimTable) #type: ignore
    lightP_table: bpy.props.PointerProperty(type=TTYDLightParamAnimTable) #type: ignore

"""
==============================
    Material Properties / Panel
==============================
"""
# material 'meshReferences'
class TTYDMaterialProperties(bpy.types.PropertyGroup):
    meshMembers: bpy.props.CollectionProperty(
        type=TTYDMeshMemberRef
    ) #type: ignore

"""
==============================
    Panels
==============================
"""

# Material Panel
class TTYDMaterialPanel(bpy.types.Panel):
    """Handles the storage of mesh users for TTYD (And eventually SPM) DMD materials"""
    bl_idname = "OBJECT_PT_TTYD_World_Material"
    bl_label = "TTYD World (Material)"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "material"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        mat = context.material
        return mat

    def draw_header(self, context):
        layout = self.layout

    def draw(self, context):
        layout = self.layout
        obj = context.material

        props = obj.meshReferences
        box = layout.box()
        box.label(text="Mesh Members")
        for ref in props.meshMembers:
            box.template_ID(ref, "obj", open="object.open")

# Empty / Mesh / Light / Empty(material) / Empty(anim) Panel
class TTYDWorldPanel(bpy.types.Panel):
    """Handles the storage of main variables for I/O of TTYD (And eventually SPM) DMD meshes, empties, materials, and lights"""
    bl_idname = "OBJECT_PT_TTYD_World_Props"
    bl_label = "TTYD World Properties"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        obj = context.object
        return obj and obj.type in {'MESH', 'EMPTY', 'LIGHT', 'CURVE'}

    def draw_header(self, context):
        layout = self.layout

    def draw(self, context):
        layout = self.layout
        obj = context.object
        
        # ---------- EMPTY (Joint / Pointer / Material) ----------
        if obj.type == 'EMPTY':
            props = obj.ttyd_world_empty

            attr = obj.ttyd_attributes
             #Rendering properties
            layout.prop(attr, "origin_offset")
            layout.prop(attr, "light_mask")
            layout.prop(attr, "draw_mode")
            layout.prop(attr, "cull_mode")
            layout.prop(attr, "wFlags")
            layout.prop(attr, "hit_type")
            layout.prop(attr, "hit_val")

            layout.label(text="DMD Object", icon='OUTLINER_OB_EMPTY')
            layout.prop(props, "dmdObject")
            layout.prop(props, "isLight")
            layout.prop(props, "isMaterial")
            layout.prop(props, "isTexture")
            layout.prop(props, "isAnimation")

            if props.dmdObject:
                box = layout.box()
                box.label(text="Mesh Members")
                for ref in props.meshMembers:
                    box.template_ID(ref, "obj", open="object.open")

            if props.isLight:
                lightProps = obj.ttyd_world_light

                layout.label(text="Light Data", icon='OUTLINER_DATA_LIGHT')
                layout.prop(lightProps, "type")
                layout.prop(lightProps, "base_color")
                layout.prop(lightProps, "multiplier")
                layout.prop(lightProps, "spotAngle")
                layout.prop(lightProps, "angularAttenuation")
                layout.prop(lightProps, "distanceAttenuationType")
                layout.prop(lightProps, "wFlags")
                layout.prop(lightProps, "enableFlags"), #True if bytes are '0x12d60d8', has been True in all testing so far
                
            if props.isMaterial:
                materialProps = obj.ttyd_world_material

                blendataHeader = layout.row(align=True)
                blendataHeader.prop(
                    materialProps,
                    "showBlenderData",
                    text="Show Blender Users",
                    icon="TRIA_DOWN" if materialProps.showBlenderData else "TRIA_RIGHT",
                    emboss=True,
                )
                if materialProps.showBlenderData:
                    layout.label(text="Material Data", icon='MATERIAL_DATA')
                    box = layout.box()
                    box.label(text="Preview Material References")

                    for ref in materialProps.materialRefs:
                        box.template_ID(ref, "material", open="material.open")

                    box.label(text="Meshes Using This Material")

                    for ref in materialProps.emptyMeshMembers:
                        row = box.row(align=True)
                        split = row.split(factor=0.80, align=True)
                        left = split.row(align=True)
                        right = split.row(align=True)

                        left.template_ID(ref, "obj", open="object.open")
                        right.label(text=f"[DM {ref.draw_mode}]")

                        op = row.operator(
                            "ttyd.select_object",
                            text="",
                            icon='RESTRICT_SELECT_OFF'
                        )
                        op.object_name = ref.obj.name

                layout.prop(materialProps, "name")
                layout.prop(materialProps, "color")
                layout.prop(materialProps, "matSrc")
                layout.prop(materialProps, "unk_009")
                layout.prop(materialProps, "blendMode")
                layout.prop(materialProps, "numTextures")
                layout.prop(materialProps, "blendAlphaModulationR")

                layout.label(text="Texture Samplers", icon='TEXTURE')

                samplerHeader = layout.row(align=True)
                samplerHeader.prop(
                    materialProps,
                    "showSamplers",
                    text="Show Samplers",
                    icon="TRIA_DOWN" if materialProps.showSamplers else "TRIA_RIGHT",
                    emboss=True,
                )
                samplerHeader.label(text=f" ({len(materialProps.textureSamplers)})")

                samplerHeader.operator("ttyd.add_sampler", text="", icon='ADD')

                if materialProps.showSamplers:
                    for i, sampler in enumerate(materialProps.textureSamplers):
                        box = layout.box()

                        row = box.row(align=True)
                        row.label(text=f"Sampler {i}", icon='TEXTURE_DATA')

                        remove = row.operator(
                            "ttyd.remove_sampler",
                            text="",
                            icon='X'
                        )
                        remove.index = i

                        box.prop(sampler, "wrapS")
                        box.prop(sampler, "wrapT")
                        box.prop(sampler, "unk_0a")
                        box.prop(sampler, "unk_0b")

                        imgheader = box.row(align=True)
                        imgheader.prop(
                            sampler,
                            "showImage",
                            text="Show Image Datablock",
                            icon="TRIA_DOWN" if sampler.showImage else "TRIA_RIGHT",
                            emboss=True,
                        )

                        if sampler.showImage:
                            if sampler.texture:
                                tex_box = box.box()
                                tex_box.label(text="Texture")
                                tex_box.prop(sampler.texture, "image")
                                tex_box.prop(sampler.texture, "name")
                                tex_box.prop(sampler.texture, "render_order")
                                tex_box.prop(sampler.texture, "wWidth")
                                tex_box.prop(sampler.texture, "wHeight")

                        texheader = box.row(align=True)
                        texheader.prop(
                            sampler,
                            "showTexCoord",
                            text="Show Texture Coordinates (Advanced)",
                            icon="TRIA_DOWN" if sampler.showTexCoord else "TRIA_RIGHT",
                            emboss=True,
                        )
                        if sampler.showTexCoord:
                            tc = sampler.texCoord
                            tc_box = box.box()
                            box.prop
                            info = tc_box.column()
                            info.label(text="Only touch these if you know what you're doing!")

                            col = tc_box.column(align=True)
                            col.prop(tc, "translateX")
                            col.prop(tc, "translateY")

                            col = tc_box.column(align=True)
                            col.prop(tc, "scaleX")
                            col.prop(tc, "scaleY")

                            col = tc_box.column(align=True)
                            col.prop(tc, "warpX")
                            col.prop(tc, "warpY")

                            tc_box.prop(tc, "rotateZ")

                tev = materialProps.tevConfig

                box = layout.box()
                box.label(text="TEV Config", icon='NODE_MATERIAL')
                box.prop(tev, "tevMode")

            if props.isTexture:
                texProps = obj.ttyd_world_texture
                layout.prop(texProps, "index")
                layout.prop(texProps, "name")
                layout.prop(texProps, "render_order")
                layout.prop(texProps, "width")
                layout.prop(texProps, "height")
                layout.prop(texProps, "format")
                layout.prop(texProps, "wrap_s")
                layout.prop(texProps, "wrap_t")
                layout.prop(texProps, "min_filter")
                layout.prop(texProps, "mag_filter")
                layout.prop(texProps, "lod_bias")
                layout.prop(texProps, "edge_lod_enable")
                layout.prop(texProps, "min_lod")
                layout.prop(texProps, "max_lod")

            if props.isAnimation:
                animProps = obj.ttyd_world_animation

                boolBox = layout.box()
                row = boolBox.row(align=True)

                boolBox.prop(animProps, "name")
                boolBox.prop(animProps, "length")

                row.prop(animProps, "joint")
                row.prop(animProps, "uv")
                row.prop(animProps, "alpha")
                row.prop(animProps, "lightT")
                row.prop(animProps, "lightP")

                if animProps.joint:
                    jt = animProps.joint_table
                    jointBox = layout.box()
                    jointBox.label(text="Joint Animation Table")

                    row = jointBox.row(align=True)
                    row.prop(jt, "count", text="Track Count")
                    row.operator("ttyd.sync_joint_anim_tracks", text="Sync", icon="FILE_REFRESH")

                    for i, track in enumerate(jt.tracks):
                        trackRow = jointBox.row(align=True)
                        trackRow.prop(track, "name", text=f"Track {i}")
                        op = trackRow.operator("ttyd.remove_joint_anim_track", text="", icon="X")
                        op.index = i

                        refBox = jointBox.box()
                        refBox.prop(track, "joint")
                        refBox.prop(track, "keyframeCount")
                        deltarow = refBox.row(align=True)
                        deltarow.prop(track, "anim_delta", text="Delta")
                        op = deltarow.operator("ttyd.sync_joint_anim_delta_from_loc", text="", icon="SNAP_ON")
                        op.index = i
                        refBox.prop(track, "action")

                    jointBox.operator("ttyd.add_joint_anim_track", icon="ADD")

                if animProps.uv:
                    uvBox = layout.box()
                    uvBox.label(text="UV Animation Table")
                    uvBox.prop(animProps.uv_table, "count", text="Track Count")
                    for i in range(animProps.uv_table.count):
                        trackBox = uvBox.box()
                        track = animProps.uv_table.tracks[i]
                        trackRow = trackBox.row(align=True)
                        trackRow.prop(track, "name")
                        trackRow.label(text=f"Track [{i}]")
                        skewRow = trackBox.row(align=True)
                        trackBox.prop(track, "samplerIndex")
                        skewRow.prop(track, "skew")

                        mRow = trackBox.row(align=True)
                        vRow = trackBox.row(align=True)
                        vxRow = trackBox.row(align=True)

                        mSplit = mRow.split(factor=0.25, align=True)
                        mLeft = mSplit.row(align=True)
                        mRight = mSplit.row(align=True)

                        vSplit = vRow.split(factor=0.25, align=True)
                        vLeft = vSplit.row(align=True)
                        vRight = vSplit.row(align=True)

                        vxSplit = vxRow.split(factor=0.25, align=True)
                        vxLeft = vxSplit.row(align=True)
                        vxRight = vxSplit.row(align=True)

                        mLeft.label(text="[mat]")
                        mRight.template_ID(track, "mat", open="object.open")
                        sel = mRow.operator(
                            "ttyd.select_object",
                            text="",
                            icon='RESTRICT_SELECT_OFF'
                        )
                        sel.object_name = track.mat.name if track.mat else ""                            

                        vLeft.label(text="[mat]_v")
                        vRight.template_ID(track, "mat_v", open="object.open")
                        sel = vRow.operator(
                            "ttyd.select_object",
                            text="",
                            icon='RESTRICT_SELECT_OFF'
                        )
                        sel.object_name = track.mat_v.name if track.mat_v else ""

                        vxLeft.label(text="[mat]_v_x")
                        vxRight.template_ID(track, "mat_v_x", open="object.open")
                        sel = vxRow.operator(
                            "ttyd.select_object",
                            text="",
                            icon='RESTRICT_SELECT_OFF'
                        )
                        sel.object_name = track.mat_v_x.name if track.mat_v_x else ""

                        trackBox.prop(track, "action")
                
                if animProps.alpha:
                    alphaBox = layout.box()
                    alphaBox.label(text="Material Alpha Animation Table")
                    alphaBox.prop(animProps.alpha_table, "count", text="Track Count")
                    for i in range(animProps.alpha_table.count):
                        trackBox = alphaBox.box()
                        track = animProps.alpha_table.tracks[i]
                        trackRow = trackBox.row(align=True)
                        trackRow.prop(track, "name")
                        trackRow.label(text=f"Track [{i}]")

                        mRow = trackBox.row(align=True)
                        vRow = trackBox.row(align=True)
                        vxRow = trackBox.row(align=True)

                        mSplit = mRow.split(factor=0.25, align=True)
                        mLeft = mSplit.row(align=True)
                        mRight = mSplit.row(align=True)

                        vSplit = vRow.split(factor=0.25, align=True)
                        vLeft = vSplit.row(align=True)
                        vRight = vSplit.row(align=True)

                        vxSplit = vxRow.split(factor=0.25, align=True)
                        vxLeft = vxSplit.row(align=True)
                        vxRight = vxSplit.row(align=True)

                        mLeft.label(text="[mat]")
                        mRight.template_ID(track, "mat", open="object.open")
                        sel = mRow.operator(
                            "ttyd.select_object",
                            text="",
                            icon='RESTRICT_SELECT_OFF'
                        )
                        sel.object_name = track.mat.name if track.mat else ""                            

                        vLeft.label(text="[mat]_v")
                        vRight.template_ID(track, "mat_v", open="object.open")
                        sel = vRow.operator(
                            "ttyd.select_object",
                            text="",
                            icon='RESTRICT_SELECT_OFF'
                        )
                        sel.object_name = track.mat_v.name if track.mat_v else ""

                        vxLeft.label(text="[mat]_v_x")
                        vxRight.template_ID(track, "mat_v_x", open="object.open")
                        sel = vxRow.operator(
                            "ttyd.select_object",
                            text="",
                            icon='RESTRICT_SELECT_OFF'
                        )
                        sel.object_name = track.mat_v_x.name if track.mat_v_x else ""

                        trackBox.prop(track, "action")
                    

                if animProps.lightT:
                    jointBox = layout.box()
                    jointBox.label(text="Light Transform Animation Table")
                    jointBox.prop(animProps.lightT_table, "count", text="Track Count")
                    for i in range(animProps.lightT_table.count):
                        track = animProps.lightT_table.tracks[i]
                        trackRow = jointBox.row(align=True)
                        trackRow.prop(track, "name")
                        refBox = jointBox.box()
                        refBox.prop(track, "light")
                        refBox.prop(track, "keyframeCount")
                        refBox.prop(track, "action")

                if animProps.lightP:
                    lightPBox = layout.box()
                    lightPBox.label(text="Light Parameter Animation Table")
                    lightPBox.prop(animProps.lightP_table, "count", text="Track Count")
                    for i in range(animProps.lightP_table.count):
                        track = animProps.lightP_table.tracks[i]
                        trackRow = lightPBox.row(align=True)
                        trackRow.prop(track, "name")

        # ---------- MESH (Fragment / Standalone) ----------
        elif obj.type == 'MESH':
            props = obj.ttyd_world_mesh

             # -------------------------
            # Local Mesh IR
            # -------------------------

            layout.prop(props, "isCamRoadRegion")
            if props.isCamRoadRegion:
                bbox_box = layout.box()
                bbox_box.prop(props, "bbox_min")
                bbox_box.prop(props, "bbox_max")

            IRbox = layout.box()
            row = IRbox.row()
            row.label(text="Local Mesh IR", icon='OUTLINER_DATA_MESH')

            if props.ir_dirty:
                row.label(text="OUT OF DATE", icon='ERROR')

            IRbox.prop(
                props,
                "showIR",
                text="Show IR Data",
                icon="TRIA_DOWN" if props.showIR else "TRIA_RIGHT",
                emboss=True,
            )

            if props.showIR:
                IRbox.prop(props, "has_nrm")
                IRbox.prop(props, "has_uv0")
                IRbox.prop(props, "has_uv1")
                IRbox.prop(props, "has_col")

                # ---- Vertex Buffer ----
                vtx_box = IRbox.box()
                vtx_box.label(
                    text=f"Local Vertices ({len(props.local_vertices)})",
                    icon='VERTEXSEL'
                )

                if props.local_vertices:
                    col = vtx_box.column(align=True)

                    for i, v in enumerate(props.local_vertices):
                        row = col.row(align=True)
                        row.label(text=f"{i:>3}")

                        # Position (always present)
                        px, py, pz = v.pos
                        row.label(text=f"P ({px:.4f}, {py:.4f}, {pz:.4f})")

                        sub = row.row(align=True)
                        sub.scale_x = 0.85

                        # Normal
                        if any(n != 0.0 for n in v.nrm):
                            nx, ny, nz = v.nrm
                            sub.label(text=f"N ({nx:.2f}, {ny:.2f}, {nz:.2f})")

                        # UV0
                        if any(u != 0.0 for u in v.uv0):
                            u0, v0 = v.uv0
                            sub.label(text=f"UV0 ({u0:.3f}, {v0:.3f})")

                        # UV1
                        if any(u != 0.0 for u in v.uv1):
                            u1, v1 = v.uv1
                            sub.label(text=f"UV1 ({u1:.3f}, {v1:.3f})")

                        # Color
                        if any(c != 0.0 for c in v.col):
                            r, g, b, a = v.col
                            sub.label(text=f"C ({r:.2f},{g:.2f},{b:.2f},{a:.2f})")

                else:
                    vtx_box.label(text="(no local vertex buffer)", icon='INFO')

                # ---- Primitive Stream ----
                prim_box = IRbox.box()
                prim_box.label(
                    text=f"Primitives ({len(props.local_primitives)})",
                    icon='MESH_GRID'
                )

                if props.local_primitives:
                    for i, prim in enumerate(props.local_primitives):
                        pbox = prim_box.box()
                        pbox.label(
                            text=f"[{i}] Opcode: {hex(prim.opcode)}",
                            icon='DOT'
                        )
                        pbox.label(text=f"Indices: {prim.indices}")
                else:
                    prim_box.label(text="(no primitives)", icon='INFO')

                # -------------------------
                # IR Operations
                # -------------------------
                ops = layout.box()
                ops.label(text="IR Operations", icon='TOOL_SETTINGS')

                row = ops.row(align=True)
                row = ops.row(align=True)

                if props.isCamRoadRegion:
                    row.operator("ttyd.rebuild_camroad_ir", icon='FILE_REFRESH')
                else:
                    row.operator("ttyd.rebuild_local_ir", icon='FILE_REFRESH')
                    row.operator("ttyd.stripify_mesh", icon='MOD_TRIANGULATE')

                if props.ir_dirty:
                    ops.label(
                        text="Rebuild required before export",
                        icon='ERROR'
                    )

            #DMDObject Data
            layout.label(text="Mesh Role", icon='MESH_DATA')
            layout.prop(props, "meshFragment")
            if props.meshFragment:
                layout.prop(props, "fragmentParent")
            
            #TTYD/Blender Material Refs
            layout.label(text="Material Data", icon='MATERIAL_DATA')
            box = layout.box()
            row = box.row(align=True)
            row.prop(props, "emptyMaterial", text="Material Empty")
            sel = row.operator(
                "ttyd.select_object",
                text="",
                icon='RESTRICT_SELECT_OFF'
            )
            sel.object_name = props.emptyMaterial.name if props.emptyMaterial else ""

            box.label(text="Preview Material Reference")
            box.template_ID(props, "previewMaterial", open="material.open")

            attr = obj.ttyd_attributes
             #Rendering properties
            layout.prop(attr, "origin_offset")
            layout.prop(attr, "light_mask")
            layout.prop(attr, "draw_mode")
            layout.prop(attr, "cull_mode")
            layout.prop(attr, "wFlags")
            layout.prop(attr, "hit_type")
            layout.prop(attr, "hit_val")

        # ---------- CURVE (Camera Path) ----------
        elif obj.type == 'CURVE':
            props = obj.ttyd_world_curve

            layout.label(text="Camera Path Data", icon='CURVE_DATA')
            layout.prop(props, "Marker")

            box = layout.box()

            for i, ref in enumerate(props.localCurveIR):
                col = box.column()
                col.label(text=f"Entry {i}")

                col.prop(ref, "pos", text="Pos")
                col.prop(ref, "param", text="Param")

            layout.prop(props, "wbLockY")
            layout.prop(props, "wLockedYVal")
            layout.prop(props, "bDisabled")
            layout.prop(props, "clampStartSegment")
            layout.prop(props, "clampEndSegment")
            layout.prop(props, "clampMaxDistanceLeft")
            layout.prop(props, "clampMaxDistanceRight")
            layout.prop(props, "clampStartSegmentProgress")
            layout.prop(props, "clampEndSegmentProgress")
            layout.prop(props, "wCameraToTargetDistance")
            layout.prop(props, "camElevationDegrees")
            layout.prop(props, "camPitchDegrees")
            layout.prop(props, "shiftXRate")
            layout.prop(props, "unk_80")
            layout.prop(props, "wbEnableClamping")
            layout.prop(props, "bbox_min")
            layout.prop(props, "bbox_max")
            layout.prop(props, "curve_data_count")
            layout.prop(props, "geometry_count")
            layout.prop(props, "zero")
            layout.prop(props, "unk_count")
            