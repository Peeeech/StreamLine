import bpy #type: ignore

class TTYDFogTable(bpy.types.PropertyGroup):
    fogEnabled: bpy.props.BoolProperty(default=False, description="Whether fog will be visible in the exported map") #type: ignore
    fogMode: bpy.props.IntProperty(description="Unknown") #type: ignore
    fogStart: bpy.props.IntProperty(description="Distance from camera that fog should start") #type: ignore
    fogEnd: bpy.props.IntProperty(description="Distance from camera that fog should end") #type: ignore
    fogColor: bpy.props.FloatVectorProperty(
            name="Fog Color",
            description="0-255 RGB Values for Fog Color",
            subtype='COLOR',
            size=4,
            min=0,
            max=1.0,
            default=(0, 0, 0, 0)
        ) #type: ignore

classes = (TTYDFogTable,)

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except:
            pass
    # Scene UI state for collapsing
    if not hasattr(bpy.types.Scene, "ttyd_fog_expanded"):
        bpy.types.Scene.ttyd_fog_expanded = bpy.props.BoolProperty(default=False)

    if not hasattr(bpy.types.Scene, "ttyd_fog_table"):
        bpy.types.Scene.ttyd_fog_table = bpy.props.PointerProperty(type=TTYDFogTable)

def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass

    if hasattr(bpy.types.Scene, "ttyd_fog_table"):
        delattr(bpy.types.Scene, "ttyd_fog_table")

    if hasattr(bpy.types.Scene, "ttyd_fog_expanded"):
        delattr(bpy.types.Scene, "ttyd_fog_expanded")

def draw_fog_panel(layout, context):
    scene = context.scene
    props = scene.ttyd_fog_table
    expanded = getattr(scene, "ttyd_fog_expanded", False)

    #UI state
    header = layout.row(align=True)
    icon = 'TRIA_DOWN' if expanded else 'TRIA_RIGHT'
    header.prop(scene, "ttyd_fog_expanded", text="Fog", emboss=False, icon=icon)

    if expanded:
        #properties
        layout.prop(props, "fogEnabled")
        layout.prop(props, "fogMode")
        layout.prop(props, "fogStart")
        layout.prop(props, "fogEnd")
        layout.prop(props, "fogColor")