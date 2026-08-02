import os
import re
import bpy #type: ignore

def sorted_alphanumeric(data):
    convert = lambda text: int(text) if text.isdigit() else text.lower()
    alphanum_key = lambda key: [ convert(c) for c in re.split('([0-9]+)', key) ] 
    return sorted(data, key=alphanum_key)

def rename(tex_names, tex_dir):
    images = {}
        #skip check if files already renamed
    filenames = sorted_alphanumeric(os.listdir(tex_dir))

    check_file = filenames[0][:3]
    if not check_file == "i_0":
        for i, filename in enumerate(tex_names):
            new_name = (f"{filename}.png")
            tex_path = os.path.join(tex_dir, new_name)
            images[i] = {
            "name": filename,
            "path": tex_path,
            "tpl_index": i
            }
        return images

    else:
        #enumerate and rename files based on index
        for i, filename in enumerate(tex_names):
            old_name = os.path.join(tex_dir, filenames[i])
            tex_path = os.path.join(tex_dir, (f"{filename}.png"))

            os.rename(old_name, tex_path)

            images[i] = {
                "name": filename,
                "path": tex_path,
                "tpl_index": i
            }
        return images

FORMATS = {
    '0': 'I4', 
    '1': 'I8', 
    '2': 'IA4',
    '3': 'IA8',
    '4': 'RGB565',
    '5': 'RGB5A3',
    '6': 'RGBA32',
    '7': 'C4',
    '8': 'C8',
    '9': 'C14X2',
    '14': 'CMPR',
}

def build_images_from_scene(tpl, imgs, context):
    images = []

    for idx, img in enumerate(tpl):
        try:
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
        except IndexError:
            fallbackName = f"i_{img.index}_{FORMATS.get(f'{img.format}')}_{img.width}x{img.height}"

            print(f"[Warning]: IndexError, TPL doesn't match stored DMD texture-name list. Renaming to a fallback, but this could cause errors! Double check index values!\n    renamed to: {context.scene.mat_prefix}[{idx}]")
            empty = bpy.data.objects.new(
                name=fallbackName,
                object_data=None
            )
            empty.ttyd_world_empty.isTexture = True

            tex_props = empty.ttyd_world_texture
            tex_props.index = img.index
            tex_props.name = fallbackName
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