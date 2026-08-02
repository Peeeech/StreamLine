import bpy #type: ignore
from ..helpers import imgs
from . import shared

shared_key = 'TEXTURE'

FMT = {
    0: "I4",
    1: "I8",
    2: "IA4",
    3: "IA8",
    4: "RGB565",
    5: "RGB5A3",
    6: "RGBA32",
    14: "CMPR",
}

class MaxImageImportSize(bpy.types.PropertyGroup):
    """Max size in (x, y) for image to scale down on process (prevents lag from CMPR-checking images 1000+ pixels)"""
    #Will preserve aspect ratio by finding ratio of (in width/height)--biggestWH:importSize and multiplying both vals by it, then rounding to closest flat pixel.
    pixels: bpy.props.IntProperty(default=64) #type: ignore

class ImageEmptyRef(bpy.types.PropertyGroup):
    """Wrapper to reference an image empty object in a UIList"""
    obj: bpy.props.PointerProperty(type=bpy.types.Object)  # type: ignore

def get_image_sync_state(obj):
    tex = getattr(obj, "ttyd_world_texture", None)
    if not tex:
        return None, False

    img = bpy.data.images.get(tex.name) or bpy.data.images.get(obj.name)
    if not img:
        return None, False

    names_match = (obj.name == tex.name == img.name)
    size_match = (img.size[0] == tex.width and img.size[1] == tex.height)
    return img, (names_match and size_match)

def rebuild_indices_from_refs(scene):
    refs = scene.ttyd_image_refs
    for i, ref in enumerate(refs):
        obj = ref.obj
        if obj and hasattr(obj, "ttyd_world_texture"):
            try:
                obj.ttyd_world_texture.index = i
            except Exception:
                pass

class TTYD_UL_ImagesUIList(bpy.types.UIList):
    """Custom UIList for image empties with inline operators"""

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if not item.obj:
            layout.label(text="(invalid)")
            return

        obj = item.obj
        col = layout.column(align=True)
        top_row = col.row(align=True)

        split = top_row.split(factor=0.6)
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

        t_left.label(text=obj.name, icon='IMAGE_DATA')

        tex = obj.ttyd_world_texture if hasattr(obj, "ttyd_world_texture") else None
        img, in_sync = get_image_sync_state(obj) if tex else (None, False)
        icon_id = 'FILE_TICK' if in_sync else 'FILE_REFRESH'

        refresh_op = t_right.operator("ttyd.refresh_image", text="", icon=icon_id)
        refresh_op.object_name = obj.name

        btn = t_right.operator("ttyd.select_show", text="", icon='RESTRICT_SELECT_OFF')
        btn.object_name = obj.name

        scene = context.scene
        is_active = (index == scene.ttyd_image_refs_index)

        if tex and is_active:
            b_right.label(text=f"{tex.width}x{tex.height}")
            b_right.label(text=f"Idx:{tex.index}")

            format = FMT.get(getattr(tex, "format", None), "Unknown")
            b_left.label(text=f"    Format: {format}")

            up_op = t_right.operator("ttyd.reorder_image", text="", icon='TRIA_UP')
            up_op.object_name = obj.name
            up_op.direction = "UP"

            down_op = t_right.operator("ttyd.reorder_image", text="", icon='TRIA_DOWN')
            down_op.object_name = obj.name
            down_op.direction = "DOWN"

class TTYD_OT_show_image(bpy.types.Operator):
    bl_idname = "ttyd.show_image"
    bl_label = "Show Image in Image Editor"

    object_name: bpy.props.StringProperty()  # type: ignore

    def execute(self, context):
        obj = bpy.data.objects.get(self.object_name)
        if not obj:
            self.report({'WARNING'}, "Object not found")
            return {'CANCELLED'}

        img, _, _ = sync_image_for_object(obj)
        if not img:
            self.report({'WARNING'}, "No image datablock found or created")
            return {'CANCELLED'}

        # Try to find an existing Image Editor and show the image there
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'IMAGE_EDITOR':
                    for space in area.spaces:
                        if space.type == 'IMAGE_EDITOR':
                            space.image = img
                            self.report({'INFO'}, f"Displayed {img.name} in Image Editor")
                            return {'FINISHED'}
                        
        shared.sync_UI_state(shared_key)

        self.report({'WARNING'}, 'No Image Editor area found in current screen')
        return {'CANCELLED'}

class TTYD_OT_create_from_blender(bpy.types.Operator):
    bl_idname = "ttyd.batch_create_empty"
    bl_label = "Create PMMap Empties from Blender `Images` datablocks"

    def execute(self, context):
        scene = context.scene
        images = []

        for img in bpy.data.images:
            if img.name == "Render Result":
                render = bpy.data.images.get(img.name)
                bpy.data.images.remove(render)
            else:
                images.append(img)

        for img in images:
            existing = bpy.data.objects.get(img.name)

            if existing and getattr(existing, "ttyd_world_empty", None):
                imgEmpty = existing

            else:
                convimg, scale = imgs.blender_image_to_pil(img, max_size=64)
                fmt = imgs.detect_format(convimg)
                bpy.ops.ttyd.create_image_empty(base=img.name, format=imgs.TPL_FORMATS[fmt])
                name = context.scene.get("_last_created_empty")
                imgEmpty = bpy.data.objects.get(name)
                if imgEmpty:
                    print(imgEmpty.name, imgs.TPL_FORMATS[fmt], fmt)

        shared.sync_UI_state(shared_key)

        return {'FINISHED'}

class TTYD_OT_create_image_empty(bpy.types.Operator):
    bl_idname = "ttyd.create_image_empty"
    bl_label = "Create PMMap Image Empty"
    DEFAULT_BASE = "PMMapImage"

    base: bpy.props.StringProperty(default=DEFAULT_BASE) #type: ignore
    format: bpy.props.IntProperty(default=0) #type: ignore
    size: bpy.props.IntVectorProperty(size=2) #type: ignore

    def execute(self, context):
        scene = context.scene
        name = f"{self.base}"

        self.size = (scene.ttyd_image_ioSize, scene.ttyd_image_ioSize)

        i = 1
        while name in bpy.data.objects:
            name = f"{self.base}_{i}"
            i += 1

        if self.base == self.DEFAULT_BASE:
            width, height = self.size
            img = bpy.data.images.new(name, width=width, height=height)
            img.use_fake_user = True
        else:
            img = bpy.data.images.get(self.base)
            (width, height) = self.size

        empty = bpy.data.objects.new(name=name, object_data=None)
        # mark as PMMap image-empty
        try:
            empty.ttyd_world_empty.isTexture = True
            tex = empty.ttyd_world_texture
            tex.index = -1
            tex.name = name
            tex.width = width
            tex.height = height
            tex.format = self.format
            tex.wrap_s = 0
            tex.wrap_t = 0
            tex.min_filter = 0
            tex.mag_filter = 0
        except Exception as e:
            print(e)
            pass

        master_collection = scene.collection
        img_collection = bpy.data.collections.get("Images")
        if img_collection is None:
            img_collection = bpy.data.collections.new("Images")
            master_collection.children.link(img_collection)

        img_collection.objects.link(empty)
        context.scene["_last_created_empty"] = empty.name

        # Select and show
        try:
            bpy.ops.ttyd.select_show(object_name=empty.name)
        except Exception:
            pass

        shared.sync_UI_state(shared_key)

        self.report({'INFO'}, f"Created image {name} ({width}x{height})")
        return {'FINISHED'}

class TTYD_OT_refresh_image(bpy.types.Operator):
    bl_idname = "ttyd.refresh_image"
    bl_label = "Refresh Image Datablock"

    object_name: bpy.props.StringProperty()  # type: ignore

    def execute(self, context):
        obj = bpy.data.objects.get(self.object_name)
        shared.sync_UI_state(shared_key)

        if not obj:
            self.report({'WARNING'}, "Object not found")
            return {'CANCELLED'}

        image, matched, updated = sync_image_for_object(obj)
        if image:
            self.report({'INFO'}, f"Image datablock set to '{image.name}'")
            return {'FINISHED'}

        self.report({'WARNING'}, "No image created")
        return {'CANCELLED'}

class TTYD_OT_reorder_image(bpy.types.Operator):
    bl_idname = "ttyd.reorder_image"
    bl_label = "Reorder Image Index"

    object_name: bpy.props.StringProperty()  # type: ignore
    direction: bpy.props.StringProperty()  # type: ignore

    def execute(self, context):
        scene = context.scene
        refs = scene.ttyd_image_refs

        current_index = -1
        for i, ref in enumerate(refs):
            if ref.obj and ref.obj.name == self.object_name:
                current_index = i
                break

        if current_index == -1:
            self.report({'WARNING'}, "Object not found in UI list")
            return {'CANCELLED'}

        if self.direction == "UP":
            new_index = current_index - 1
        elif self.direction == "DOWN":
            new_index = current_index + 1
        else:
            self.report({'WARNING'}, "Invalid direction")
            return {'CANCELLED'}

        if not (0 <= new_index < len(refs)):
            self.report({'WARNING'}, "Cannot reorder further in this direction")
            return {'CANCELLED'}

        refs.move(current_index, new_index)
        scene.ttyd_image_refs_index = new_index
        rebuild_indices_from_refs(scene)

        for area in context.screen.areas if context.screen else []:
            area.tag_redraw()

        shared.sync_UI_state(shared_key)

        return {'FINISHED'}

def sync_image_for_object(obj):
    # tex.name is authoritative; object name and image datablock name follow it
    tex = None
    try:
        tex = obj.ttyd_world_texture
    except Exception:
        tex = None

    updated = False

    if tex and getattr(tex, "name", None):
        tex_name = tex.name
        target_w = max(1, int(getattr(tex, "width", 64) or 64))
        target_h = max(1, int(getattr(tex, "height", 64) or 64))

        # Prefer tex.name lookup first, since RNA name is authoritative
        img = bpy.data.images.get(tex_name)
        if not img:
            img = bpy.data.images.get(obj.name)

        # Create if missing
        if not img:
            img = bpy.data.images.new(tex_name, width=target_w, height=target_h)
            img.use_fake_user = True
            updated = True
        else:
            # Rename image to tex.name
            if img.name != tex_name:
                try:
                    img.name = tex_name
                    updated = True
                except Exception:
                    pass

            # Resize image to RNA dimensions
            try:
                if img.size[0] != target_w or img.size[1] != target_h:
                    img.scale(target_w, target_h)
                    img.update()
                    updated = True
            except Exception:
                pass

        # Rename object to tex.name
        if obj.name != tex_name:
            try:
                obj.name = tex_name
                updated = True
            except Exception:
                pass

        return img, True, updated

    # fallback
    img = bpy.data.images.get(obj.name)
    if img and tex is not None:
        try:
            if tex.name != img.name:
                tex.name = img.name
                updated = True
        except Exception:
            pass

        try:
            target_w = max(1, int(getattr(tex, "width", img.size[0]) or img.size[0]))
            target_h = max(1, int(getattr(tex, "height", img.size[1]) or img.size[1]))
            if img.size[0] != target_w or img.size[1] != target_h:
                img.scale(target_w, target_h)
                img.update()
                updated = True
        except Exception:
            pass

    return img, (img is not None), updated

classes = (MaxImageImportSize, ImageEmptyRef, TTYD_UL_ImagesUIList, TTYD_OT_show_image, TTYD_OT_create_from_blender, TTYD_OT_create_image_empty, TTYD_OT_refresh_image, TTYD_OT_reorder_image)

def on_image_index_changed(self, context):
    scene = self
    idx = scene.ttyd_image_refs_index

    if idx < 0 or idx >= len(scene.ttyd_image_refs):
        return

    ref = scene.ttyd_image_refs[idx]
    obj = ref.obj
    if not obj:
        return
    
    #ensure Images collection visible:
    for col in bpy.context.view_layer.layer_collection.children:
        if col.exclude == True and col.name == "Images":
            col.exclude = not col.exclude

    # Deselect all without bpy.ops
    for o in context.view_layer.objects:
        o.select_set(False)

    obj.select_set(True)
    context.view_layer.objects.active = obj

    # Optional: sync/show image too
    img, _, _ = sync_image_for_object(obj)
    if img:
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'IMAGE_EDITOR':
                    for space in area.spaces:
                        if space.type == 'IMAGE_EDITOR':
                            space.image = img
                            return

scene_attr = ["ttyd_image_refs", "ttyd_image_refs_index"]

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except:
            pass
    # Scene UI state for collapsing
    if not hasattr(bpy.types.Scene, "ttyd_images_expanded"):
        bpy.types.Scene.ttyd_images_expanded = bpy.props.BoolProperty(default=False)
    
    # Max size for imported images
    if not hasattr(bpy.types.Scene, "ttyd_image_ioSize"):
        bpy.types.Scene.ttyd_image_ioSize = bpy.props.IntProperty(default=64)

    # Selected image expanded
    if not hasattr(bpy.types.Scene, "ttyd_img_selected"):
        bpy.types.Scene.ttyd_img_selected = bpy.props.PointerProperty(type=bpy.types.Object)

    # UIList collection of image empty references
    if not hasattr(bpy.types.Scene, "ttyd_image_refs"):
        bpy.types.Scene.ttyd_image_refs = bpy.props.CollectionProperty(type=ImageEmptyRef)
    if not hasattr(bpy.types.Scene, "ttyd_image_refs_index"):
        bpy.types.Scene.ttyd_image_refs_index = bpy.props.IntProperty(default=0, update=on_image_index_changed)


def unregister():
    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass

    if hasattr(bpy.types.Scene, "ttyd_images_expanded"):
        delattr(bpy.types.Scene, "ttyd_images_expanded")

    if hasattr(bpy.types.Scene, "ttyd_image_ioSize"):
        delattr(bpy.types.Scene, "ttyd_image_ioSize")

    if hasattr(bpy.types.Scene, "ttyd_img_selected"):
        delattr(bpy.types.Scene, "ttyd_img_selected")

    if hasattr(bpy.types.Scene, "ttyd_image_refs"):
        delattr(bpy.types.Scene, "ttyd_image_refs")

    if hasattr(bpy.types.Scene, "ttyd_image_refs_index"):
        delattr(bpy.types.Scene, "ttyd_image_refs_index")


def draw_images_panel(layout, context):
    scene = context.scene
    expanded = getattr(scene, "ttyd_images_expanded", False)

    header = layout.row(align=True)
    icon = 'TRIA_DOWN' if expanded else 'TRIA_RIGHT'
    header.prop(scene, "ttyd_images_expanded", text="Images", emboss=False, icon=icon)
    header.operator("ttyd.create_image_empty", text="", icon='ADD')
    header.prop(scene, "ttyd_image_ioSize", text="")
    header.operator("ttyd.batch_create_empty", text="", icon='IMAGE_DATA')

    if not expanded:
        return

    if len(scene.ttyd_image_refs) == 0:
        layout.label(text="No PMMap image empties found.")
        return

    layout.template_list(
        "TTYD_UL_ImagesUIList",
        "image_empties",
        scene,
        "ttyd_image_refs",
        scene,
        "ttyd_image_refs_index",
        rows=min(5, max(1, len(scene.ttyd_image_refs)))
    )
    for ref in scene.ttyd_image_refs:
        if ref.obj in bpy.context.selected_objects:
            texProps = ref.obj.ttyd_world_texture
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