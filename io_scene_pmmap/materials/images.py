import os
import sys
import json
import bpy #type: ignore

def rename(tex_names, tex_dir):
    images = {}
        #skip check if files already renamed
    check_file = os.path.join(tex_dir, "i-1.png")
    if not os.path.exists(check_file):
        for i, filename in enumerate(tex_names):
            new_name = (f"{filename}.png")
            tex_path = os.path.join(tex_dir, new_name)
            images[i] = {
            "name": filename,
            "path": tex_path,
            "tpl_index": i
            }
        return images

    #enumerate and rename files based on index (offset by 1 to account for i-0)
    for i, filename in enumerate(tex_names):
        old_name = f"i-{i+1}.png"
        old_path = os.path.join(tex_dir, old_name.strip('"'))
        new_name = (f"{filename}.png")
        tex_path = os.path.join(tex_dir, new_name)

        if os.path.exists(old_path):
            os.rename(old_path, tex_path)
        else:
            print(f"File '{old_path}' does not exist!")
            continue
        images[i] = {
            "name": filename,
            "path": tex_path,
            "tpl_index": i
        }
    return images

def build_images_from_scene(tpl, imgs, context):
    images = []

    for img in tpl:
        empty = bpy.data.objects.new(
            name=f"{context.scene.mat_prefix}{imgs[img.index]}",
            object_data=None
        )
        empty.ttyd_world_empty.isTexture = True

        tex_props = empty.ttyd_world_texture
        tex_props.index = img.index
        tex_props.name = imgs[img.index]
        tex_props.width = img.width
        tex_props.height = img.height
        tex_props.format = img.format
        tex_props.wrap_s = img.wrap_s
        tex_props.wrap_t = img.wrap_t
        tex_props.min_filter = img.min_filter
        tex_props.mag_filter = img.mag_filter
        tex_props.lod_bias = img.lod_bias
        tex_props.edge_lod_enable = img.edge_lod_enable
        tex_props.min_lod = img.min_lod
        tex_props.max_lod = img.max_lod

        images.append(empty)
    
    scene = bpy.context.scene
    master_collection = scene.collection

    img_collection = bpy.data.collections.get("Images")

    if img_collection is None:
        img_collection = bpy.data.collections.new("Images")
        master_collection.children.link(img_collection)

    for i, img in enumerate(images):
        img_collection.objects.link(img)

    return images