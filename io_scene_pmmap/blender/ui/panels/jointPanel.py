import bpy #type: ignore

class JointRef(bpy.types.PropertyGroup):
    """Wrapper to reference a material empty object in a UIList"""
    obj: bpy.props.PointerProperty(type=bpy.types.Object)  # type: ignore

class TTYD_UL_JointUIList(bpy.types.UIList):
    """UIList to display joint empties in the joint panel"""
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        joint_ref = item
        if not joint_ref.obj:
            layout.label(text="(invalid)")
            return
        obj = joint_ref.obj
        col = layout.column(align=True)
        top_row = col.row(align=True)

        split = top_row.split(factor=0.9)
        t_left = split.row(align=True)
        t_right = split.row(align=True)

        bottom_row = col.row(align=True)

        split = bottom_row.split(factor=0.6)
        b_left = split.row(align=True)
        b_right = split.row(align=True)

        t_left.alignment = 'LEFT'
        t_right.alignment = 'RIGHT'
        b_left.alignment = 'LEFT'
        b_right.alignment = 'RIGHT'

        if obj.type == 'MESH':        
            t_left.label(text=obj.name, icon='BONE_DATA')
        elif obj.type == 'EMPTY':
            t_left.label(text=obj.name, icon='EMPTY_DATA')

        selObj = t_right.operator("ttyd.select_object", text="", icon='RESTRICT_SELECT_OFF')
        selObj.object_name = obj.name

def on_joint_index_changed(self, context):
    scene = self
    idx = scene.ttyd_joint_refs_index

    if idx < 0 or idx >= len(scene.ttyd_joint_refs):
        return

    ref = scene.ttyd_joint_refs[idx]
    obj = ref.obj
    if not obj:
        return

    # Avoid clearing panel; just set active object to the selected joint ref
    context.view_layer.objects.active = obj

classes = (JointRef, TTYD_UL_JointUIList)

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except:
            pass

    if not hasattr(bpy.types.Scene, "ttyd_joints_expanded"):
        bpy.types.Scene.ttyd_joints_expanded = bpy.props.BoolProperty(default=True) # type: ignore

    if not hasattr(bpy.types.Scene, "ttyd_joint_refs"):
        bpy.types.Scene.ttyd_joint_refs = bpy.props.CollectionProperty(type=JointRef) #type: ignore
    if not hasattr(bpy.types.Scene, "ttyd_joint_refs_index"):
        bpy.types.Scene.ttyd_joint_refs_index = bpy.props.IntProperty(update=on_joint_index_changed) #type: ignore

def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass

    if hasattr(bpy.types.Scene, "ttyd_joints_expanded"):
        try:
            del bpy.types.Scene.ttyd_joints_expanded
        except AttributeError:
            pass
    
    if hasattr(bpy.types.Scene, "ttyd_joint_refs"):
        try:
            del bpy.types.Scene.ttyd_joint_refs
        except AttributeError:
            pass

    if hasattr(bpy.types.Scene, "ttyd_joint_refs_index"):
        try:
            del bpy.types.Scene.ttyd_joint_refs_index
        except AttributeError:
            pass

def draw_joint_panel(layout, context):
    scene = context.scene
    expanded = getattr(scene, "ttyd_joints_expanded", False)

    header = layout.row(align=True)
    icon = 'TRIA_DOWN' if expanded else 'TRIA_RIGHT'
    header.prop(scene, "ttyd_joints_expanded", text="Joints", icon=icon, emboss=False)

    if not expanded:
        return

    row = layout.row()
    row.label(text="Joint Panel", icon='BONE_DATA')

    layout.template_list(
        "TTYD_UL_JointUIList",
        "",
        scene,
        "ttyd_joint_refs",
        scene,
        "ttyd_joint_refs_index",
        rows=min(5, len(scene.ttyd_joint_refs))
    )