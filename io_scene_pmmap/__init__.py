# __init__.py
import bpy  #type: ignore
import subprocess
import json
import os
import sys
import shutil
import tempfile

from . import images
from . import effects
from . import materials
from . import geometries
from . import animations
from . import scenes

bl_info = {
    "name": "PMMap Parser",
    "author": "Peeeech",
    "version": (0, 2),
    "blender": (2, 80, 0),
    "location": "File > Import",
    "description": "Imports PMTTYD map files using JavaScript and Python parsers",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Import-Export",
}

class ImportBinaryFileOperator(bpy.types.Operator):
    """Import a d file using Node.js script"""
    bl_idname = "import_export.d_file"
    bl_label = "Import Binary File (d)"
    bl_options = {'REGISTER', 'UNDO'}

    filepath: bpy.props.StringProperty(
        name="File Path",
        description="Path to the binary d file",
        maxlen=1024,
        subtype='FILE_PATH'
    )  # type: ignore

    filter_glob: bpy.props.StringProperty(
        default="*",
        options={'HIDDEN'},
        maxlen=255,
    )  # type: ignore

    def execute(self, context):
        # 1) Get paths
        binary_file = self.filepath
        addon_dir   = os.path.dirname(__file__)
        pmmap_dir      = os.path.join(addon_dir, "pmmap")
        main_js     = os.path.join(pmmap_dir, "main.js")

        if not os.path.exists(main_js):
            self.report({'ERROR'}, f"main.js not found at {main_js}")
            return {'CANCELLED'}

        # 2) Check for 't' file
        if bpy.context.scene.t_import:
            t_file = os.path.join(os.path.dirname(binary_file), "t")
            if os.path.exists(t_file):
                tex_dir = os.path.join(addon_dir, "tex")

                # Clean out 'tex/' if it exists
                if os.path.exists(tex_dir):
                    for filename in os.listdir(tex_dir):
                        file_path = os.path.join(tex_dir, filename)
                        try:
                            if os.path.isdir(file_path):
                                shutil.rmtree(file_path)
                            else:
                                os.remove(file_path)
                        except Exception as e:
                            print(f"Error removing {file_path}: {e}")
                else:
                    os.makedirs(tex_dir)

            # 'python imageStream.py [t]'
            python_exe = bpy.app.binary_path_python
            try:
                subprocess.run(
                    [python_exe, "imageStream.py", t_file],
                    cwd=addon_dir,
                    check=True,
                    text=True
                )
                print("Successfully processed 't' with imageStream.py + decode.py.")
            except subprocess.CalledProcessError as e:
                print("=== CalledProcessError ===")
                print(f"Return code: {e.returncode}")
                print("--- STDOUT ---")
                print(e.stdout)
                print("--- STDERR ---")
                print(e.stderr)
                self.report({'ERROR'}, "Error running imageStream.py (see console for details).")
                return {'CANCELLED'}


        else:
            print("'t' file not found in the same directory as the imported file.")

        # 5) Ensure Node.js installed
        try:
            subprocess.run(['node', '--version'], check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.report({'ERROR'}, "Node.js is not installed or not found in PATH.")
            return {'CANCELLED'}

        # 6) Execute main.js with the binary file path
        try:
            result = subprocess.run(
                ['node', main_js, binary_file],
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            self.report({'ERROR'}, f"Error running main.js:\n{e.stderr.strip()}")
            return {'CANCELLED'}

        # 7) Extract sections from temp.txt
        model_path = os.path.join(addon_dir, "temp.txt")
        if os.path.exists(model_path):
            print("----- Extracting Sections from temp.txt -----")
            extract_sections(model_path)
            os.remove(model_path)           #Call to delete temp.txt: Useful for debugging, as it's the string all the py data pulls from
        else:
            return {'CANCELLED'}
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
    
    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, "t_import", text="Import Textures")
        layout.prop(context.scene, "coll_creation", text="Create Collections")

def menu_func_import(self, context):
    self.layout.operator(ImportBinaryFileOperator.bl_idname, text="Import Map File (d)")

def register():
    bpy.utils.register_class(ImportBinaryFileOperator)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    bpy.types.Scene.coll_creation = bpy.props.BoolProperty(
        name="Create Collections",
        description="If enabled, will automatically organize items from single 'world_root' empty into exportable collections",
        default=True,
    ) # type: ignore
    bpy.types.Scene.t_import = bpy.props.BoolProperty(
        name="Import textures",
        description="If enabled, will import 't' file alongside 'd' map file to create textures/materials",
        default=True,
    ) # type: ignore

def unregister():
    bpy.utils.unregister_class(ImportBinaryFileOperator)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

def extract_sections(file_path):
    """
    Reads a file and extracts content between specific start and end tags.
    """
    tags = [
        ("library_images", "/library_images"),
        ("library_effects", "/library_effects"),
        ("library_materials", "/library_materials"),
        ("library_geometries", "/library_geometries"),
#        ("library_animations", "/library_animations"),
        ("library_visual_scenes", "/library_visual_scenes"),
    ]
    try:
        with open(file_path, 'r') as file:
            content = file.read()

        for start_tag, end_tag in tags:
            start_index = content.find(start_tag)
            end_index = content.find(end_tag)
            if start_index != -1 and end_index != -1:
                start_index += len(start_tag)
                extracted_string = content[start_index:end_index].strip()

                # Pass extracted content to appropriate module
                if bpy.context.scene.t_import:
                    if start_tag == "library_images":
                        print("images")
                        images.process(extracted_string)

                    if start_tag == "library_effects":
                        print("effects")
                        effects.process(extracted_string)
                    if start_tag == "library_materials":
                        print("materials")
                        materials.process(extracted_string)
                if start_tag == "library_geometries":
                    print("geometries")
                    geometries.process(extracted_string)
#           Animations not implemented yet :(
#                elif start_tag == "library_animations":
#                   print("animations")
#                    animations.process(extracted_string)
                if start_tag == "library_visual_scenes":
                    print("scenes")
                    scenes.process(extracted_string)
            else:
                print(f"Tags {start_tag} and/or {end_tag} not found.")
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    register()
