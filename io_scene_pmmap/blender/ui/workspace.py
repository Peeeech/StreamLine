import bpy #type: ignore
from .panels import imagePanel as image_panel
from .panels import materialPanel as material_panel
from .panels import jointPanel as joint_panel
from .helpers import cameraRaycast

# Object setup to determine what setup func to run for a given workspace, and which areas to keep
SETUP_FUNCS = {
    "Shading": {
        "areas": ['PROPERTIES', 'OUTLINER', 'VIEW_3D']
    }
}

class UIQueue:
    def __init__(self):
        self.steps = []
        
    def add(self, func, delay=0.01):
        self.steps.append((func, delay))
        
    def run(self):
        def execute_step(i=0):
            if i >= len(self.steps):
                return None
            func, delay = self.steps[i]
            func()
            return delay, i + 1
        
        def runner(state={"i": 0}):
            i = state["i"]
            if i >= len(self.steps):
                return None
            func, delay = self.steps[i]
            func()
            state["i"] += 1
            return delay
        
        bpy.app.timers.register(runner)
    
# Used as a placeholder to simulate time passing in the queue, since we can't reliably context-swap without it
def buffer():
    print("Starting queue...")

def swap(name):
    ws = bpy.data.workspaces.get(f"{name}")
    bpy.context.window.workspace = ws

def delayed_check():
    ws = bpy.context.window.workspace
    print("After update:", ws.name)

def cleanup(ws=None):

    workspace = SETUP_FUNCS[ws]
    areas = workspace.get("areas")
    cleanAreas(toKeep=len(areas), areas=areas)

def split_workspace(type_to_split, direction, factor):
    context = bpy.context
    window = context.window
    screen = window.screen
    for area in screen.areas:
        if area.type == type_to_split.upper():
            with context.temp_override(window=window, screen=screen, area=area):
                bpy.ops.screen.region_toggle(region_type='UI')
                bpy.ops.screen.area_split(direction=f'{direction}'.upper(), factor=factor)

def change_area(original_type, new_type, override=False):
    """Changes an area of a given type to a new type. If multiple areas of the original type exist, only one will be changed based on the override flag (first found if False, second found if True)"""
    areasToCheck = []
    for area in bpy.context.window.screen.areas:
        if area.type == original_type.upper():
            areasToCheck.append(area)
            
    if len(areasToCheck) == 1:
        areasToCheck[0].type = f'{new_type}'.upper()
        return
    elif len(areasToCheck) == 2:
        first_area = areasToCheck[0]
        second_area = areasToCheck[1]

    if not override:
        second_area.type = f'{new_type}'.upper()
    else:
        first_area.type = f'{new_type}'.upper()


    # Dedicated setup for the shading workspace follows cleanup, to keep logic modulated and isolated to this function 

# Cleans up the workspace by closing areas that aren't in the specified list, until only the specified number of areas remain
def cleanAreas(toKeep=1, areas=None):
    window = bpy.context.window
    screen = bpy.context.window.screen

    areaCnt = len(screen.areas)
    areaCache = [area.type for area in screen.areas]
    print("Initial areas:", areaCache)

    for area in bpy.context.window.screen.areas:
        if len(screen.areas) <= toKeep:
            print("Stopping cleanup")
            break

        print("Area:", area.type)
        if area.type not in areas:
            with bpy.context.temp_override(window=window, screen=screen, area=area):
                bpy.ops.screen.area_close()

# Brings back the default workspaces by appending them from the startup file, and returns them in a list for later use in workspace setup functions
def import_workspaces(context):
    if context is None:
        context = bpy.context

    def get_ws(name):
        return bpy.data.workspaces.get(name)

    bpy.ops.workspace.append_activate(
            idname='Layout',
            filepath=bpy.utils.user_resource('CONFIG', path='startup.blend')
        )

    layout_ws = get_ws('Layout')
    layout_ws.name = "Layout"

    bpy.ops.workspace.append_activate(
        idname='Scripting',
        filepath=bpy.utils.user_resource('CONFIG', path='startup.blend')
    )

    scripting_ws = get_ws('Scripting')
    scripting_ws.name = "Scripting"

    bpy.ops.workspace.append_activate(
        idname='Shading',
        filepath=bpy.utils.user_resource('CONFIG', path='startup.blend')
    )

    shading_ws = get_ws('Shading')
    shading_ws.name = "Shading"

    bpy.ops.workspace.append_activate(
        idname='UV Editing',
        filepath=bpy.utils.user_resource('CONFIG', path='startup.blend')
    )

    uv_editing_ws = get_ws('UV Editing')
    uv_editing_ws.name = "UV Editing"

    bpy.ops.workspace.append_activate(
        idname='Texture Paint',
        filepath=bpy.utils.user_resource('CONFIG', path='startup.blend')
    )
    
    return [layout_ws, scripting_ws, shading_ws, uv_editing_ws]

def isolate_map_collection():
    view_layer = bpy.context.view_layer
    root = view_layer.layer_collection

    def recurse(layer_col):
        name = layer_col.collection.name

        # Keep Map visible, hide everything else
        layer_col.exclude = (name != "Map")

        for child in layer_col.children:
            recurse(child)

    recurse(root)

def prep():
    screen = bpy.context.screen
    window = bpy.context.window

    for area in screen.areas:
        if area.type == 'OUTLINER':
            space = area.spaces.active
            space.display_mode = 'VIEW_LAYER'

            for region in area.regions:
                if region.type == 'WINDOW':

                    with bpy.context.temp_override(
                            window=window,
                            screen=screen,
                            area=area,
                            region=region,
                            space_data=space
                        ):
                        
                        bpy.ops.outliner.show_one_level(open=False)

                    isolate_map_collection()

        elif area.type == 'VIEW_3D':
            space = area.spaces.active
            space.shading.type = 'SOLID'
            space.shading.color_type = 'TEXTURE'

            region_3d = space.region_3d
            region_3d.view_location = (0, 0, 0)
            region_3d.view_rotation = (0.7948, 0.6068, 0, 0)
            region_3d.view_distance = 160
            region_3d.view_perspective = 'PERSP' # 'PERSP' 'ORTHO' 'CAMERA'

class PMMAP_OT_setup_workspace(bpy.types.Operator):
    bl_idname = "pmmap.setup_workspace"
    bl_label = "PMMap Workspace"

    def execute(self, context):
        exportColls = ["Images", "Materials", "Lights", "Map", "Hit", "Cam", "Unused", "Animations"]

        for collection in bpy.data.collections:
            if collection.name not in exportColls:
                objects = []
                for obj in collection.objects:
                    bpy.data.objects.remove(obj, do_unlink=True, do_id_user=True, do_ui_user=True)
                bpy.data.collections.remove(collection)

        existingCollections = []
        for collection in bpy.data.collections:
            existingCollections.append(collection.name)

        scene = bpy.context.scene
        master = scene.collection

        for exCollection in exportColls:
            if exCollection not in existingCollections:
                newCol = bpy.data.collections.new(exCollection)

                master.children.link(newCol)
            


        # keep only one workspace
        start_ws_list = bpy.data.workspaces[:]
        start_scr_list = bpy.data.screens[:]

        for idx, ws in enumerate(start_ws_list):
            ws.name = f"deprecated[{idx}]"

        for idx, scr in enumerate(start_scr_list):
            scr.name = f"deprecated[{idx}]"

        bpy.ops.workspace.delete_all_others()

        # set up custom tex-asset workspace
        pm_ws = context.workspace
        pm_scr = context.screen
        pm_ws.name = "Texture Assets"
        pm_scr.name = "Texture Assets"

        window = context.window
        screen = window.screen

        # collapse to one area
        while len(screen.areas) > 1:
            area = screen.areas[-1]
            with context.temp_override(window=window, screen=screen, area=area):
                bpy.ops.screen.area_close()

        area = screen.areas[0]
        area.type = 'IMAGE_EDITOR'

        # From this point on, the workspace is set to just the Image Editor, so everything following is just to set it up for PMMap

        with context.temp_override(window=window, screen=screen, area=area):
            bpy.ops.screen.region_toggle(region_type='UI')
            bpy.ops.screen.area_split(direction='VERTICAL', factor=0.75)

        areas = screen.areas
        left_area = areas[0]
        right_area = areas[1]

        right_area.type = 'PROPERTIES'

        #bring back defaults
        #NOTE: For setting up workspaces, we use a state-machine like queue system to ensure that context changes have time to propagate before the next step runs,
            # since we can't reliably context-swap without it. This is especially important for the workspace setup functions, as blender's .context doesn't update immediately after calls

        workspaces = import_workspaces(context)

        wsList = ["Texture Assets", "Layout", "Scripting", "Shading", "UV Editing", "Texture Paint"]

        queue = UIQueue()
        queue.add(lambda: buffer())
        
        for workspace in wsList:
            queue.add(lambda ws=workspace: swap(ws))
            queue.add(lambda: prep())

        queue.add(lambda: swap("Shading"))
        queue.add(lambda: delayed_check())
        queue.add(lambda: cleanup("Shading"))
        queue.add(lambda: split_workspace("view_3d", "horizontal", 0.25))
        queue.add(lambda: change_area("view_3d", "image_editor", override=False))


        #swap back
        #queue.add(lambda: swap(f"Texture Assets"))
        #queue.add(lambda: delayed_check())
        
        queue.run()

        return {'FINISHED'}
    
class TTYD_OT_select_show(bpy.types.Operator):
    bl_idname = "ttyd.select_show"
    bl_label = "Select and Show Related"

    object_name: bpy.props.StringProperty()  # type: ignore

    def execute(self, context):
        obj = bpy.data.objects.get(self.object_name)
        if not obj:
            self.report({'WARNING'}, "Object not found")
            return {'CANCELLED'}

        # Deselect all
        bpy.ops.object.select_all(action='DESELECT')

        # Attempt to resolve/sync image using the object's texture name
        img, _, _ = image_panel.sync_image_for_object(obj)
        if img:
            #ensure Images collection visible:
            for col in bpy.context.view_layer.layer_collection.children:
                if col.exclude == True and col.name == "Images":
                    col.exclude = not col.exclude

            # Select + activate
            obj.select_set(True)
            context.view_layer.objects.active = obj

            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'IMAGE_EDITOR':
                        for space in area.spaces:
                            if space.type == 'IMAGE_EDITOR':
                                space.image = img
                                return {'FINISHED'}
                    
        empty, mat, _ = material_panel.get_material_sync_state(obj)
        # Skip activation to only grab meshes
        if mat and empty and empty.ttyd_world_empty.isMaterial:
            print(mat, _)
            #ensure Materials collection visible:
            for col in bpy.context.view_layer.layer_collection.children:
                if col.exclude == True and col.name == "Materials":
                    col.exclude = not col.exclude

            objs = []
            for ref in mat.emptyMeshMembers:
                objs.append(ref.obj)
                print(obj.name)
                    
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'VIEW_3D':
                        for space in area.spaces:
                            if space.type == 'VIEW_3D':
                                for i, ref in enumerate(bpy.context.scene.ttyd_material_refs):
                                    if ref.obj == obj:
                                        bpy.context.scene.ttyd_material_refs_index = i
                                        bpy.ops.object.select_all(action='DESELECT')
                                        
                                for o in objs:
                                    o.select_set(True)

        # If no image area found, still return finished (selection done)
        return {'FINISHED'}
    
class PMMAP_PT_image_panel(bpy.types.Panel):
    bl_label = "PMMap Image Viewer"
    bl_idname = "PMMAP_PT_image_panel"
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "PM-Textures"

    def draw(self, context):
        layout = self.layout
        image_panel.draw_images_panel(layout, context)

# duplicate panel draw to 3D Viewport Panel
class TTYDGlobalPanel(bpy.types.Panel):
    bl_label = "PM Map"
    bl_idname = "TTYD_PT_images_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'PM Map'

    def draw(self, context):
        image_panel.draw_images_panel(self.layout, context)
        material_panel.draw_materials_panel(self.layout, context)
        joint_panel.draw_joint_panel(self.layout, context)

classes = (
    PMMAP_OT_setup_workspace,
    TTYD_OT_select_show,
    PMMAP_PT_image_panel,
    TTYDGlobalPanel
)

def draw_menu(self, context):
    self.layout.operator(PMMAP_OT_setup_workspace.bl_idname, text="PMMap Workspace")

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except:
            pass

    bpy.types.TOPBAR_MT_window.append(draw_menu)
    # Register image panel UI within the workspace initializer
    try:
        image_panel.register()
    except Exception as e:
        print("image", e)
    # Register material panel UI within the workspace initializer
    try:
        material_panel.register()
    except Exception as e:
        print("material", e)
        pass
    # Register joint panel UI within the workspace initializer
    try:
        joint_panel.register()
    except Exception as e:
        print("joint", e)


def unregister():
    bpy.types.TOPBAR_MT_window.remove(draw_menu)

    # Unregister image panel
    try:
        image_panel.unregister()
    except Exception:
        pass
    # Unregister material panel
    try:
        material_panel.unregister()
    except Exception:
        pass
    # Unregister joint panel
    try:
        joint_panel.unregister()
    except Exception:
        pass

    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass