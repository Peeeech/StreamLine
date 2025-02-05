import os
import sys
import bpy # type: ignore

def process(extracted_string):
    filenames = extracted_string.strip().split("\n")
    tex_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tex')
    textures = []
    imgs = []
    paths = []

    for i, filename in enumerate(filenames):
        old_name = f"i-{i+1}.png"
        old_path = os.path.join(tex_dir, old_name.strip('"'))
        new_name = filename.strip('"')
        textures.append(new_name[:-4])
        tex_path = os.path.join(tex_dir, new_name)
        imgs.append(new_name)
        paths.append(tex_path)

        if os.path.exists(old_path):
            os.rename(old_path, tex_path)
        else:
            print(f"File '{old_path}' does not exist!")
            continue
    global images
    global imagePaths
    images = imgs
    imagePaths = paths