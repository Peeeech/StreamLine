import bpy

# Select all objects in the scene
bpy.ops.object.select_all(action='DESELECT')
bpy.ops.object.select_all(action='SELECT')

# Apply all transforms to selected objects
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# Deselect all objects
bpy.ops.object.select_all(action='DESELECT')

def find_root_object():
    # Iterate through all objects in the scene
    for obj in bpy.context.scene.collection.objects:
        # Check if the object is an empty and has children
        if obj.type == 'EMPTY' and len(obj.children) > 0:
            return obj

    return None

def mark_descendants(parent_empty):
    # Mark the parent empty with a custom property
    parent_empty["linked_to_collection"] = True

    # Iterate through children of the parent empty
    for child_obj in parent_empty.children:
        # If the child object is an empty, recursively mark its descendants
        if child_obj.type == 'EMPTY':
            mark_descendants(child_obj)

def link_descendants(parent_collection, parent_empty):
    # Iterate through children of the parent empty
    for child_obj in parent_empty.children:
        # Unlink the child object from the Blender scene collection
        bpy.context.scene.collection.objects.unlink(child_obj)

        # If the child object is an empty and marked, link it to the collection
        if child_obj.type == 'EMPTY' and child_obj.get("linked_to_collection"):
            parent_collection.objects.link(child_obj)
            link_descendants(parent_collection, child_obj)  # Recursively link its descendants
        else:
            # Link the child object to the parent collection
            parent_collection.objects.link(child_obj)

def unparent_and_create_collections():
    # Find the root object in the scene
    root_obj = find_root_object()

    if not root_obj:
        print("Root object not found.")
        return

    # Set the scene
    scene = bpy.context.scene

    # Create a dictionary to store collections
    collections_dict = {}

    # Recursive function to mark descendants
    def mark_all_descendants(parent_empty):
        # Mark descendants recursively
        mark_descendants(parent_empty)

    # Recursive function to link descendants
    def link_all_descendants(parent_collection, parent_empty):
        # Iterate through children of the parent empty
        for child_obj in parent_empty.children:
            # Unlink the child object from the Blender scene collection
            bpy.context.scene.collection.objects.unlink(child_obj)

            # If the child object is an empty and marked, link it to the collection
            if child_obj.type == 'EMPTY' and child_obj.get("linked_to_collection"):
                parent_collection.objects.link(child_obj)
                link_all_descendants(parent_collection, child_obj)  # Recursively link its descendants
            else:
                # Link the child object to the parent collection
                parent_collection.objects.link(child_obj)

    # Iterate through child objects of the root
    for child_obj in root_obj.children:
        # Check if the child is an empty object
        if child_obj.type == 'EMPTY':
            # Create a new collection with the empty object's name
            collection_name = child_obj.name
            new_collection = bpy.data.collections.new(collection_name)

            # Link the new collection to the scene
            scene.collection.children.link(new_collection)

            # Mark descendants recursively
            mark_all_descendants(child_obj)

            # Link descendants recursively
            link_all_descendants(new_collection, child_obj)

            # Unlink the "A" and "S" empties from the Blender scene collection
            bpy.context.scene.collection.objects.unlink(child_obj)

    # Unlink the original root object
    scene.collection.objects.unlink(root_obj)

# Call the function
unparent_and_create_collections()

def rename_collections():
    # Get all collections in the scene
    collections = bpy.context.scene.collection.children

    # Iterate through collections and rename accordingly
    for collection in collections:
        if collection.name == "A":
            collection.name = "Hit"
        elif collection.name == "S":
            collection.name = "Map"

# Run the function to rename collections
rename_collections()

#Reorder collections for simplicity
def reorder_collections():
    # Names of the collections
    collection_names = ['Hit', 'Map']

    # Check if both collections exist in the scene
    if all(name in bpy.data.collections for name in collection_names):
        # Get references to the collections
        hit_collection = bpy.data.collections[collection_names[0]]
        map_collection = bpy.data.collections[collection_names[1]]

        # Get the parent of the collections (scene.collection)
        parent_collection = bpy.context.scene.collection

        # Swap the order of the collections
        parent_collection.children.unlink(hit_collection)
        parent_collection.children.unlink(map_collection)

        parent_collection.children.link(map_collection)
        parent_collection.children.link(hit_collection)

        print("Order swapped: '{}' is now above '{}'.".format(collection_names[1], collection_names[0]))
    else:
        print("One or both collections do not exist in the scene.")

# Call the function to reorder collections
reorder_collections()

# Replace 'Hit' with the actual name of your collection
collection_name = 'Hit'

# Replace 'View Layer' with the name of your target view layer
view_layer_name = 'View Layer'

# Get the collection
hit_collection = bpy.data.collections.get(collection_name)

# Get the target view layer
view_layer = bpy.context.scene.view_layers.get(view_layer_name)

# Check if the collection and view layer exist
if hit_collection and view_layer:
    # Get the collection's layer collection for the target view layer
    hit_layer_collection = view_layer.layer_collection.children.get(collection_name)

    # Exclude the collection from the view layer
    if hit_layer_collection:
        hit_layer_collection.exclude = True  # Set to True if you want to exclude the collection

        print(f"Collection '{collection_name}' excluded from the '{view_layer_name}' view layer.")
    else:
        print(f"Collection '{collection_name}' not found in the '{view_layer_name}' view layer.")
else:
    print(f"Collection '{collection_name}' or view layer '{view_layer_name}' not found in the scene.")