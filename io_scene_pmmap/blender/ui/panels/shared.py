import bpy #type: ignore

"""
============================================
shared.py
    -Peech

    This script is intended to act as a shared resource across
all of the `[type]panel.py` scripts to keep sync states in a single,
easily modifiable place to ensure logic is minimal, as well as keeping
a way to call an entire state refresh by passing each object of the
`SHARED_KEYS` in as a loop function

codename: panelDrv
============================================
"""

SHARED_KEYS = {
    'TEXTURE',
    'MATERIAL',
    'JOINT',
}

#region: Images
"""
======================
        Images
======================
"""

"""===== Helpers ====="""
def get_image_empties_unsorted():
    img_collection = bpy.data.collections.get("Images")
    if img_collection:
        return [o for o in img_collection.objects]
    return [
        o for o in bpy.data.objects
        if hasattr(o, "ttyd_world_empty") and getattr(o.ttyd_world_empty, "isTexture", False)
    ]

def rebuild_img_indices_from_refs(scene):
    refs = scene.ttyd_image_refs
    for i, ref in enumerate(refs):
        obj = ref.obj
        if obj and hasattr(obj, "ttyd_world_texture"):
            try:
                obj.ttyd_world_texture.index = i
            except Exception:
                pass

"""===== Main ====="""

def ensure_image_refs(scene):
    if not hasattr(scene, "ttyd_image_refs"):
        return False

    refs = scene.ttyd_image_refs
    objs = get_image_empties_unsorted()

    existing = [ref.obj for ref in refs if ref.obj]
    existing_set = set(existing)
    objs_set = set(objs)

    changed = False

    # Remove dead refs
    remove_indices = [i for i, ref in enumerate(refs) if not ref.obj or ref.obj not in objs_set]
    for i in reversed(remove_indices):
        refs.remove(i)
        changed = True

    # Add new objects at end
    existing = [ref.obj for ref in refs if ref.obj]
    existing_set = set(existing)
    for obj in objs:
        if obj not in existing_set:
            ref = refs.add()
            ref.obj = obj
            changed = True

    if changed:
        rebuild_img_indices_from_refs(scene)

        return True

"""
======================
      Images End
======================
"""
#region end

#region: Materials
"""
======================
      Materials
======================
"""

"""===== Helpers ====="""

def get_material_empties():
    mat_collection = bpy.data.collections.get("Materials")
    if mat_collection:
        return [o for o in mat_collection.objects]
    return [
        o for o in bpy.data.objects
        if hasattr(o, "ttyd_world_empty") and getattr(o.ttyd_world_empty, "isMaterial", False)
    ]

def rebuild_mat_indices_from_refs(scene):
    refs = scene.ttyd_material_refs
    for i, ref in enumerate(refs):
        obj = ref.obj
        if obj and hasattr(obj, "ttyd_world_material"):
            try:
                obj.ttyd_world_material.index = i
            except Exception:
                pass

"""===== Main ====="""

def ensure_material_refs(scene):
    if not hasattr(scene, "ttyd_material_refs"):
        return False

    refs = scene.ttyd_material_refs
    objs = get_material_empties()

    existing = [ref.obj for ref in refs if ref.obj]
    existing_set = set(existing)
    objs_set = set(objs)

    changed = False

    # Remove dead refs
    remove_indices = [i for i, ref in enumerate(refs) if not ref.obj or ref.obj not in objs_set]
    for i in reversed(remove_indices):
        refs.remove(i)
        changed = True

    # Add new objects at end
    existing = [ref.obj for ref in refs if ref.obj]
    existing_set = set(existing)
    for obj in objs:
        if obj not in existing_set:
            ref = refs.add()
            ref.obj = obj
            changed = True

    if changed:
        rebuild_mat_indices_from_refs(scene)
        return True

"""
======================
    Materials End
======================
"""

#region end

#region: Joints

"""===== Helpers ====="""

def is_valid_joint(obj):
    map_col = bpy.data.collections.get("Map")
    hit_col = bpy.data.collections.get("Hit")

    if not map_col and not hit_col:
        return False

    collections = obj.users_collection

    return (
        (map_col and map_col in collections) or
        (hit_col and hit_col in collections)
    )

def resolve_joint(obj):
    props = obj.ttyd_world_mesh if hasattr(obj, "ttyd_world_mesh") else None
    if props and props.meshFragment or obj.type == 'EMPTY':
        print("Still need to implement DMDObjs..")
        return obj
    return obj

"""===== Main ====="""
def ensure_joint_refs(scene, obj=None):
    if not hasattr(scene, "ttyd_joint_refs"):
        return False
    
    refs = scene.ttyd_joint_refs
    objs = bpy.context.selected_objects
    changed = False

    scene.ttyd_joint_refs.clear()

    existing = [ref.obj for ref in refs if ref.obj]
    existing_set = set(existing)
    for obj in objs:
        if obj not in existing_set:
            ref = refs.add()
            ref.obj = obj
            changed = True

    if obj:
        valid = is_valid_joint(obj)
        if valid:
            resolve_joint(obj)

    if changed:
        rebuild_mat_indices_from_refs(scene)
        return True

#region end

#region: Main
"""
======================
        Main
======================
"""

#TODO Depsgraph state-checker. manual ops just call no matter what, desp is purely visual for user

def sync_UI_state(override_UI=None):

    scene = bpy.context.scene
    bpy.context.view_layer.update()

    if override_UI == 'TEXTURE':
        update = ensure_image_refs(scene=scene)
        print(f"[SYNC] Sync called for `TEXTURE`: Changed? {update if update else 'False'}")

    elif override_UI == 'MATERIAL':
        update = ensure_material_refs(scene=scene)
        print(f"[SYNC] Sync called for `MATERIAL`: Changed? {update if update else 'False'}")

    elif override_UI == 'JOINT':
        update = ensure_joint_refs(scene=scene)
        print(f"[SYNC] Sync called for `JOINT`: Changed? {update if update else 'False'}")

    elif override_UI is not None:
        print(f"{override_UI} selected, but didn't match any keys in \n[{SHARED_KEYS}]")

    else:
        print("Syncing all UI state.")
        obj = None

        map_col = bpy.data.collections.get("Map")

        if not map_col:
            print("[WARNING] Map collection not created")
            assert(False)

        print(map_col)
        print(map_col.objects)

        for child in map_col.objects:
            print(f"\n\n{child.name}")
            obj = child if child.type == 'EMPTY' else None
            
            if obj:
                break
            continue

        if obj is None:
            print("No empties found in `Map` Collection to initialize Joint Panel.")
            for key in SHARED_KEYS:
                if key != 'JOINT':
                    sync_UI_state(override_UI=key)
            return
        
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        for key in SHARED_KEYS:
            sync_UI_state(override_UI=key)

"""
======================
      Main End
       -Peech
======================
"""