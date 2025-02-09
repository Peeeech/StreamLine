import bpy

def unparent_world_root_children(world_root):
    """
    Unparents all direct children of world_root while preserving their world transforms.
    Returns a list of these direct children.
    """
    children = list(world_root.children)
    for child in children:
        # Save the child's world transform
        world_matrix = child.matrix_world.copy()
        # Unparent the child
        child.parent = None
        # Restore the world transform so its visible location/rotation/scale remain unchanged
        child.matrix_world = world_matrix
    return children

def add_object_hierarchy_to_collection(obj, target_collection, master_collection):
    """
    Recursively adds an object (and all its descendants) to target_collection,
    and unlinks it from master_collection (to avoid duplicate appearances).
    """
    # Use object names for membership checks since Blender's collection membership check expects a string.
    if obj.name not in [o.name for o in target_collection.objects]:
        target_collection.objects.link(obj)
    if obj.name in [o.name for o in master_collection.objects]:
        master_collection.objects.unlink(obj)
    # Process all children recursively.
    for child in obj.children:
        add_object_hierarchy_to_collection(child, target_collection, master_collection)

def create_and_setup_collections(direct_children):
    """
    Creates three collections ("Map", "Hit", "Cam") in that order.
    Then, for each direct child (from world_root):
      - If its name starts with 'S' (case-insensitive), move its entire hierarchy into "Map".
      - If its name starts with 'A' (case-insensitive), move its entire hierarchy into "Hit".
    "Cam" is left empty.
    """
    scene = bpy.context.scene
    master_collection = scene.collection

    # Create the new collections.
    map_collection = bpy.data.collections.new("Map")
    hit_collection = bpy.data.collections.new("Hit")
    cam_collection = bpy.data.collections.new("Cam")

    # Link them to the master (scene) collection in the desired order.
    master_collection.children.link(map_collection)
    master_collection.children.link(hit_collection)
    master_collection.children.link(cam_collection)

    # Process each direct child from world_root.
    for child in direct_children:
        # Check the first letter (if the name exists)
        first_letter = child.name[0].upper() if child.name else ""
        if first_letter == "S":
            add_object_hierarchy_to_collection(child, map_collection, master_collection)
        elif first_letter == "A":
            add_object_hierarchy_to_collection(child, hit_collection, master_collection)
        else:
            print(f"Skipping '{child.name}': does not start with 'A' or 'S'.")

def main():
    # Get the world_root object.
    world_root = bpy.context.scene.objects.get("world_root")
    # Capture a list of world_root's direct children.
    direct_children = unparent_world_root_children(world_root)
    # Remove the now-unparented world_root.
    bpy.data.objects.remove(world_root, do_unlink=True)
    # Create collections and move hierarchies based solely on the first letter of the direct children's names.
    create_and_setup_collections(direct_children)
