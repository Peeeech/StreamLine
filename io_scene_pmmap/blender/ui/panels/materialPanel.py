import bpy #type: ignore
from ....materials import materials
from ....blender import geometries
from . import shared

shared_key = 'MATERIAL'

class MaterialEmptyRef(bpy.types.PropertyGroup):
    """Wrapper to reference a material empty object in a UIList"""
    obj: bpy.props.PointerProperty(type=bpy.types.Object)  # type: ignore

class TTYD_OT_RegenMaterial(bpy.types.Operator):
    bl_idname = "ttyd.regen_materials"
    bl_label = "Regenerate PMMap Materials"
    bl_description = "Delete and regenerate PMMap PreviewMaterials to match the current state of the material empty."

    object_name: bpy.props.StringProperty() # type: ignore

    def execute(self, context):
        obj = bpy.data.objects.get(self.object_name)
        if not obj:
            self.report({'WARNING'}, "Object not found")
            return {'CANCELLED'}
        if not hasattr(obj, "ttyd_world_material"):
            self.report({'WARNING'}, "Object is not a PMMap material empty")
            return {'CANCELLED'}
        
        props = obj.ttyd_world_material
        prevMats = props.materialRefs
        baseUsers = props.emptyMeshMembers

        newUsers = []
        if(prevMats[0].material == None or baseUsers[0].obj == None):
            self.report({'WARNING'}, "Material empty is in an invalid state, cannot regen")
            return {'CANCELLED'}
        
        for matRef in prevMats:
            print(matRef.material.name)
            bpy.data.materials.remove(matRef.material)
        for userRef in baseUsers:
            print(userRef.obj.name, userRef.draw_mode)
            newUsers.append(userRef.obj.name)

        print("Regen with users:", newUsers)
        props.materialRefs.clear()
        props.emptyMeshMembers.clear()

        materials.makeMaterialPreviewsForEmpty(obj, props, None)

        print("Make drawMode variants...")
        for userObjName in newUsers:
            userObj = bpy.data.objects.get(userObjName)
            if not userObj:
                print(f"User object {userObjName} not found, skipping")
                continue

            mesh = bpy.data.meshes.get(userObjName)
            if not mesh:
                print(f"Mesh for user object {userObjName} not found, skipping")
                continue

            attr = userObj.ttyd_attributes
            if not attr:
                print(f"Attributes for user object {userObjName} not found, skipping")
                continue

            geometries._preview_mat_with_drawmode(userObj, mesh, props, attr, obj)
            #function re-appends itself natively

        shared.sync_UI_state(shared_key)

        return {'FINISHED'}
    

def get_material_sync_state(obj):
    mat = getattr(obj, "ttyd_world_material", None)
    if not mat:
        print(f"failed to get mat at `get_material_sync_state` for {obj.name}")
        return None, None, False
    return obj, mat, True

"""    img = bpy.data.images.get(tex.name) or bpy.data.images.get(obj.name)
    if not img:
        return None, False

    names_match = (obj.name == tex.name == img.name)
    size_match = (img.size[0] == tex.width and img.size[1] == tex.height)
    return img, (names_match and size_match)"""

class TTYD_UL_MaterialsUIList(bpy.types.UIList):
    """Custom UIList for material empties with inline operators"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if not item.obj:
            layout.label(text="(invalid)")
            return
        
        scene = context.scene

        obj = item.obj
        col = layout.column(align=True)
        top_row = col.row(align=True)

        split = top_row.split(factor=0.8)
        t_left = split.row(align=True)
        t_right = split.row(align=True)
        t_left.alignment = 'LEFT'
        t_right.alignment = 'RIGHT'

        #if scene.ttyd_sel_mat_expanded:
        bottom_row = col.row(align=True)

        split = bottom_row.split(factor=0.6)
        b_left = split.row(align=True)
        b_right = split.row(align=True)
        b_left.alignment = 'LEFT'
        b_right.alignment = 'RIGHT'

        t_left.label(text=obj.name, icon='MATERIAL_DATA')

        tex = obj.ttyd_world_material if hasattr(obj, "ttyd_world_material") else None
        tex = obj.ttyd_world_material if hasattr(obj, "ttyd_world_material") else None
        emptyProp, mat, in_sync = get_material_sync_state(obj) if tex else (None, None, False)
        icon_id = 'FILE_TICK' if in_sync else 'FILE_REFRESH'

        #refresh_op = t_right.operator("ttyd.refresh_image", text="", icon=icon_id)
        #refresh_op.object_name = obj.name
        #TODO: add refresh operator to sync prev materials to emptyMat, and regen them

        regen_op = t_right.operator("ttyd.regen_materials", text="", icon='FILE_REFRESH')
        regen_op.object_name = obj.name

        selObj = t_right.operator("ttyd.select_show", text="", icon='OBJECT_DATA')
        selObj.object_name = obj.name

class TTYD_OT_delete_mat_empty(bpy.types.Operator):
    bl_idname = "ttyd.delete_material_empty"
    bl_label = "Delete PMMap Material Empty"

    def execute(self, context):
        scene = context.scene
        selected = bpy.context.selected_objects

        for obj in selected:
            print(obj.users_collection)
            for coll in obj.users_collection:
                if 'Materials' != coll:
                    print(f"Selected object {obj.name} not in Materials coll.. skipping.")
                    continue
            name = obj.name

            bpy.data.objects.remove(obj)
            print(f"Material Empty {name} was deleted.")

        shared.sync_UI_state(shared_key)

        return {'FINISHED'}

class TTYD_OT_create_mat_empty(bpy.types.Operator):
    bl_idname = "ttyd.create_material_empty"
    bl_label = "Create PMMap Material Empty"
    DEFAULT_BASE = "PMMapMaterial"

    base: bpy.props.StringProperty(default=DEFAULT_BASE) #type: ignore

    #ttyd_new_mat_1 = Sampler type, ttyd_new_mat_2 = Color type
    def execute(self, context):
        scene = context.scene
        print(scene.ttyd_new_mat_1) #TODO: Replace with (Flat Color / Tex)
        print(scene.ttyd_new_mat_2) #TODO: Replace with (Opaque / Blended [Clip option for Tex?])

        i = 1

        name = f"{self.base}_{i}"
        while name in bpy.data.objects:
            name = f"{self.base}_{i}"
            i += 1

        #if self.base == self.DEFAULT_BASE:
        #    print("Default call path")
        
        empty = bpy.data.objects.new(name=name, object_data=None)
        try:
            empty.ttyd_world_empty.isMaterial = True
        except Exception as e:
            print(e)
            pass

        master_collection = scene.collection
        mat_collection = bpy.data.collections.get("Materials")
        if mat_collection is None:
            mat_collection = bpy.data.collections.new("Materials")
            master_collection.children.link(mat_collection)

        mat_collection.objects.link(empty)
        context.scene["_last_created_empty"] = empty.name

        props = empty.ttyd_world_material
        props.color = props.blendAlphaModulationR = (255, 255, 255, 255)
        props.unk_009 = 1

        # Select and show
        try:
            bpy.ops.ttyd.select_show(object_name=empty.name)
        except Exception:
            pass

        shared.sync_UI_state(shared_key)

        return {'FINISHED'}

    

classes = (MaterialEmptyRef, TTYD_UL_MaterialsUIList, TTYD_OT_RegenMaterial, TTYD_OT_create_mat_empty, TTYD_OT_delete_mat_empty)

def on_mat_index_change(self, context):
    scene = self
    idx = scene.ttyd_material_refs_index

    if idx < 0 or idx >= len(scene.ttyd_material_refs):
        return
    
    #ensure Mat collection visible:
    for col in bpy.context.view_layer.layer_collection.children:
        if col.exclude == True and col.name == "Materials":
            col.exclude = not col.exclude

    ref = scene.ttyd_material_refs[idx]
    obj = ref.obj
    if not obj:
        return

    # Deselect all without bpy.ops
    for o in context.view_layer.objects:
        o.select_set(False)

    obj.select_set(True)
    context.view_layer.objects.active = obj

class TTYDMatMode1: # What gets culled, not what stays
    OPAQUE = 'OPAQUE'
    CLIP = 'CLIP'
    BLEND = 'BLEND'
    SUBTRACT_ALPHA = 'SUBTRACT ALPHA'
    NO_TEX = 'NO TEX'

class TTYDMatMode2:
    VTEX = 'VERTEX COLORS'
    MATC = 'RGBA MATERIAL COLOR'

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except:
            pass

    if not hasattr(bpy.types.Scene, "ttyd_materials_expanded"):
        bpy.types.Scene.ttyd_materials_expanded = bpy.props.BoolProperty(default=True) # type: ignore
    if not hasattr(bpy.types.Scene, "ttyd_materials_imp_expanded"):
        bpy.types.Scene.ttyd_materials_imp_expanded = bpy.props.BoolProperty(default=True) # type: ignore
    if not hasattr(bpy.types.Scene, "ttyd_materials_uiList_expanded"):
        bpy.types.Scene.ttyd_materials_uiList_expanded = bpy.props.BoolProperty(default=True) # type: ignore
    if not hasattr(bpy.types.Scene, "ttyd_new_mat_1"):
        bpy.types.Scene.ttyd_new_mat_1 = bpy.props.EnumProperty(
        name="",
        description="TTYD Material-Sampler Rendering Method",
        items=[
            (TTYDMatMode1.OPAQUE, "Solid color", "Opaque diffused texture"),
            (TTYDMatMode1.CLIP, "Clipped Alpha", "Diffused texture; access to complete alpha pixels (No blending)"),
            (TTYDMatMode1.BLEND, "Blended Colors", "Diffused texture; access to alpha grading"),
            (TTYDMatMode1.NO_TEX, "None", "No texture (no samplers)"),
        ],
        default=TTYDMatMode1.OPAQUE,
    ) #type: ignore
        
    if not hasattr(bpy.types.Scene, "ttyd_new_mat_2"):
        bpy.types.Scene.ttyd_new_mat_2 = bpy.props.EnumProperty(
        name="",
        description="TTYD Material; Color Mode mixed into final color calculation",
        items=[
            (TTYDMatMode2.VTEX, "Vertex colors", "Uses geometry-based vertex colors"),
            (TTYDMatMode2.MATC, "Material color", "Uses RGBA Vector in material metadata"),
        ],
        default=TTYDMatMode2.MATC,
    ) #type: ignore

    if not hasattr(bpy.types.Scene, "ttyd_material_refs"):
        bpy.types.Scene.ttyd_material_refs = bpy.props.CollectionProperty(type=MaterialEmptyRef) # type: ignore
    if not hasattr(bpy.types.Scene, "ttyd_material_refs_index"):
        bpy.types.Scene.ttyd_material_refs_index = bpy.props.IntProperty(default=0, update=on_mat_index_change) # type: ignore

def unregister():

    if hasattr(bpy.types.Scene, "ttyd_materials_expanded"):
        try:
            delattr(bpy.types.Scene, "ttyd_materials_expanded")
        except Exception:
            pass

    if hasattr(bpy.types.Scene, "ttyd_materials_imp_expanded"):
        try:
            delattr(bpy.types.Scene, "ttyd_materials_imp_expanded")
        except Exception:
            pass

    if hasattr(bpy.types.Scene, "ttyd_sel_mat_expanded"):
        del bpy.types.Scene.ttyd_sel_mat

    if hasattr(bpy.types.Scene, "ttyd_material_refs"):
        try:
            delattr(bpy.types.Scene, "ttyd_material_refs")
        except Exception:
            pass
    if hasattr(bpy.types.Scene, "ttyd_material_refs_index"):
        try:
            delattr(bpy.types.Scene, "ttyd_material_refs_index")
        except Exception:
            pass

    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass

def indent_split(layout, factor=0.05, align=True):
    """factor is from-left, higher factor = bigger indent"""
        
    row = layout.row(align=align)
    split = row.split(factor=factor, align=align)
    left = split.row(align=align) # indent / icon
    right = split.row(align=align) #actual content     

    return left, right

def split_4(layout, align=True, leftSplitFac=0.5, rightSplitFac=0.5):
    row = layout.row(align=align)

    splitA = row.split(factor=0.5, align=align)
    left = splitA.row(align=align)
    right = splitA.row(align=align)

    split1B = left.split(factor=leftSplitFac, align=align)
    l1 = split1B.row(align=align)
    l2 = split1B.row(align=align)

    split2B = right.split(factor=rightSplitFac, align=align)
    r1 = split2B.row(align=align)
    r2 = split2B.row(align=align)

    return l1, l2, r1, r2

def draw_materials_panel(layout, context):
    scene = context.scene
    expanded = getattr(scene, "ttyd_materials_expanded", False)
    importExpanded = getattr(scene, "ttyd_materials_imp_expanded", False)
    uilistExpanded = getattr(scene, "ttyd_materials_uiList_expanded", False)

    header = layout.row(align=True)
    _, subsplit_r1 = indent_split(layout)

    icon = 'TRIA_DOWN' if expanded else 'TRIA_RIGHT'
    header.prop(scene, "ttyd_materials_expanded", text="Materials", emboss=False, icon=icon)

    if not expanded:
        return
    
    impIcon  = 'TRIA_DOWN' if importExpanded else 'TRIA_RIGHT'
    uiIcon = 'TRIA_DOWN' if uilistExpanded else 'TRIA_RIGHT'

    subsplit_r1.prop(scene, "ttyd_materials_imp_expanded", text="Import/Creation Settings", emboss=True, icon=impIcon)

    # Import / creation options
    if importExpanded: #0.1 indent to offset tri-icon in subsplit
        _, indented1 = indent_split(layout, 0.1)

        settingsBox = indented1.box()
        labelRow1 = settingsBox.row(align=True)
        enumRow1 = settingsBox.row(align=True)

        label1, _, label2, _ = split_4(labelRow1, leftSplitFac=0.95, rightSplitFac=0.95)
        l1, _, r1, _ = split_4(enumRow1, leftSplitFac=0.95, rightSplitFac=0.95)
        
        label1.label(text="Base Material Type")
        label2.label(text="Material Color Type")

        l1.prop(scene, "ttyd_new_mat_1")
        r1.prop(scene, "ttyd_new_mat_2")

    _, subsplit_r2 = indent_split(layout)

    subsplit_r2.prop(scene, "ttyd_materials_uiList_expanded", text="GX Materials List", emboss=True, icon=uiIcon)
    subsplit_r2.operator("ttyd.delete_material_empty", text="", icon='X')
    subsplit_r2.operator("ttyd.create_material_empty", text="", icon='ADD')

    if uilistExpanded:
        # Actual material content data
        if len(scene.ttyd_material_refs) == 0:
            layout.label(text="No PMMap material empties found.")
            return

        _, indented2 = indent_split(layout, 0.1)

        uiBox = indented2.box()

        uiBox.template_list(
            "TTYD_UL_MaterialsUIList",
            "material_empties",
            scene,
            "ttyd_material_refs",
            scene,
            "ttyd_material_refs_index",
            rows=min(5, max(1, len(scene.ttyd_material_refs)))
        )

    for ref in scene.ttyd_material_refs:
        if ref.obj in bpy.context.selected_objects:
            materialProps = ref.obj.ttyd_world_material

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
                    box.prop(sampler, "texBlendMode")
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