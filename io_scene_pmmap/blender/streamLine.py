import bpy #type: ignore
import math
from mathutils import Matrix #type: ignore
from bpy_extras.io_utils import axis_conversion #type: ignore

C = axis_conversion(
        from_forward='-Z', from_up='Y',
        to_forward='Y',   to_up='Z'
    ).to_4x4()

def add_object_hierarchy_to_collection(obj, target_collection):
    # Link to target collection if not already linked
    if obj.name not in target_collection.objects:
        target_collection.objects.link(obj)

    # Unlink from ALL other collections
    for col in list(obj.users_collection):
        if col != target_collection:
            col.objects.unlink(obj)

    if target_collection.name == "Unused" and bpy.data.objects.get("U") is None:
        U = bpy.data.objects.new(name="U", object_data=None)
        target_collection.objects.link(U)
        return U
    elif target_collection.name == "Unused":
        U = bpy.data.objects.get("U")
        return U

    # Recurse
    for child in obj.children:
        add_object_hierarchy_to_collection(child, target_collection)

def apply_axis_to_object_world(obj, C):
    obj.matrix_world = C @ obj.matrix_world

def detach_children_keep_world(parent_obj):
    kids = list(parent_obj.children)
    for k in kids:
        mw = k.matrix_world.copy()
        k.parent = None
        k.matrix_world = mw
    return kids

def create_and_setup_collections(direct_children):
    scene = bpy.context.scene
    master = scene.collection

    map_col = bpy.data.collections.new("Map")
    hit_col = bpy.data.collections.new("Hit")
    cam_col = bpy.data.collections.new("Cam")
    unused  = bpy.data.collections.new("Unused")
    light_col = bpy.data.collections.get("Lights")

    master.children.link(map_col)
    master.children.link(hit_col)
    master.children.link(cam_col)
    master.children.link(unused)

    world_snap = snapshot_world(direct_children)
    unused_objs = []

    for obj in bpy.context.scene.objects:
        if obj.type == 'CURVE':
            apply_axis_to_object_world(obj, C)
            add_object_hierarchy_to_collection(obj, cam_col)

    for wrapper in direct_children:
        name = wrapper.name or ""
        first = name[0].upper() if name else ""
        last  = name[-1].upper() if name else ""

        if (first == "S") or (last == "S"):
            target = map_col
        elif (first == "A") or (last == "A"):
            target = hit_col
        else:
            target = unused
            U = add_object_hierarchy_to_collection(wrapper, target)
            unused_objs.append(wrapper)
            continue

        # 1) Apply axis conversion using snapshot ONLY
        apply_axis_from_snapshot([wrapper], C, world_snap)

        # 2) Move hierarchy to collection (should not touch transforms)
        add_object_hierarchy_to_collection(wrapper, target)

        # Optional: force depsgraph update if you’re immediately reading properties
        bpy.context.view_layer.update()

    U = None

    for obj in unused_objs:
        obj.parent = U

    if U is not None:
        U.rotation_mode = 'XYZ'
        U.rotation_euler = (math.radians(90.0), 0.0, 0.0)

    # Lights are world-space objects, apply axis conversion directly
    for light in light_col.objects:
        apply_axis_to_object_world(light, C)
 
def snapshot_world(objs):
    return {o: o.matrix_world.copy() for o in objs if o and o.name in bpy.context.scene.objects}

def apply_axis_from_snapshot(objs, C, world_snapshot):
    for o in objs:
        Mw_old = world_snapshot[o]
        o.matrix_world = C @ Mw_old

def main(matprefix=""):
    # Get the world_root object.
    world_root = bpy.context.scene.objects.get(f"{matprefix}world_root")
    if not world_root:
        print("❌ world_root not found")
        return
    
    direct_children = list(world_root.children)
    original_pos = []
    
    for i, child in enumerate(direct_children):
        original_pos.append((child.location.copy()))

    # Capture a list of world_root's direct children.
    detach_children_keep_world(world_root)

    # Remove the now-unparented world_root.
    bpy.data.objects.remove(world_root, do_unlink=True)

    # Create collections and move hierarchies based solely on the first letter of the direct children's names.
    create_and_setup_collections(direct_children)

    for i, child in enumerate(direct_children):
        name = child.name or ""
        first = name[0].upper() if name else ""
        last  = name[-1].upper() if name else ""
        if (first == "S") or (last == "S") or (first == "A") or (last == "A"):
            child.location = (original_pos[i][0], original_pos[i][2], original_pos[i][1])
        else:
            child.location = (original_pos[i][0], original_pos[i][1], original_pos[i][2])