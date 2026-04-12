
import bpy  # type: ignore
import os
import shutil
import sys
import importlib.util
import subprocess

from . import pydmd
from .parsers import tplparse as ptpl
from .parsers import camparse as pcam

from .materials import decode as txDc
from .materials import imageStream as txIS
from .materials import images as txImg
from .materials import materials as txMat

from .blender import cam
from .blender import geometries
from .blender import streamLine
from .blender import panel
from .blender import lights
from .blender import animations

geomDebug = True

addon_dir = os.path.dirname(__file__)

bl_info = {
    "name": "PMMap Importer",
    "author": "Peeeech",
    "version": (1, 0),
    "blender": (5, 0, 0),
    "location": "File > Import",
    "description": "Imports Paper Mario Maps using a Python buffer parser",
    "warning": "This is an early alpha version. Expect bugs and missing features. Please report any issues on the GitHub page. It also has a requirement for Pillow to import textures, which is attempted to be automatically installed if not found, but may require manual installation in some cases.",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Import-Export",
}

def import_from_path(name, path):
    spec = importlib.util.spec_from_file_location(name, os.path.join(addon_dir, path))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class ImportBinaryFileOperator(bpy.types.Operator):
    """Imports DMD files using a Python buffer parser"""
    bl_idname = "import_export.dmd_file"
    bl_label = "Import DMD File (d)"
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

    def invoke(self, context, event):
        """Opens file browser for user selection before execution"""
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        """Only runs when a file is selected"""
        if not self.filepath:
            self.report({'ERROR'}, "No file selected.")
            return {'CANCELLED'}
        
        self.import_d_file(context)

        return {'FINISHED'}
    
    #region: DMD Import Logic
    def import_d_file(self, context):
        """Handles the actual file import logic"""
        binary_file = self.filepath

        # Proceed with DMD import logic...
        print(f"Importing DMD file: {binary_file}")

        for coll in bpy.data.collections:
            bpy.data.collections.remove(coll)

        dmd = pydmd.remoteCall(binary_file)

        if bpy.context.scene.orph_mat_clear:
            for mat in list(bpy.data.materials):
                if mat.users == 0:
                    bpy.data.materials.remove(mat)

        if bpy.context.scene.tex_import:
            try:
                import PIL
            except ImportError:
                print("PIL (Pillow) is not installed. Attempting to install...")
                try:
                    subprocess.Popen([sys.executable, "-m", "ensurepip"]).communicate()
                    subprocess.Popen([sys.executable, "-m", "pip", "install", "Pillow"]).communicate()
                    import PIL # type: ignore
                    print("PIL (Pillow) has been successfully installed.")
                except Exception as e:
                    print(f"Error installing PIL (Pillow): {e}") 

            try:
                import numpy
            except ImportError:
                print("NumPy is not installed. Attempting to install...")
                try:
                    subprocess.Popen([sys.executable, "-m", "ensurepip"]).communicate()
                    subprocess.Popen([sys.executable, "-m", "pip", "install", "numpy"]).communicate()
                    import numpy # type: ignore
                    print("NumPy has been successfully installed.")
                except Exception as e:
                    print(f"Error installing NumPy: {e}") 

            #Path helpers for texture/cam_road file
            t_file = os.path.join(os.path.dirname(binary_file), "t")
            if not os.path.isfile(t_file):
                print(f"Texture file not found at expected TTYD location: {t_file}\nTrying SPM texture path...")
                t_file = os.path.abspath((binary_file)[:-4] + ".tpl")
                if not os.path.isfile(t_file):
                    print(f"Texture file not found at expected SPM location: {t_file}\nAborting at texture import.")
                    return {'FAILED'}
                
            c_file = os.path.join(os.path.dirname(binary_file), "c")
            if not os.path.isfile(c_file):
                print(f"Camera file not found at expected TTYD location: {c_file}\nTrying SPM camera path...")
                c_file = os.path.join(os.path.dirname(binary_file), "camera_road.bin")
                if not os.path.isfile(c_file):
                    print(f"Camera file not found at expected SPM location: {c_file}\nAborting camera import.")
                    c_file = None
                
            addon_dir = os.path.dirname(__file__)
            tex_dir = os.path.join(addon_dir, "materials", "tex")
            tex_dir = os.path.abspath(tex_dir)

            #Check for/Clear out/Create "tex" directory
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

            header, tpl = ptpl.parse_tpl(t_file)
            if c_file:
                cam_road = pcam.parse_cam_road(c_file)

            txIS.extract_tpl_to_png(t_file, tex_dir)

            #Decode images
            print(f"\nDecoding Tex folder: {tex_dir}\n")            
            txDc.decode(tex_dir)

            #Rename images            
            print(f"\nRenaming Tex files in: {tex_dir}\n")
            tex_list = dmd.texture_table.textures
            txImg.rename(tex_list, tex_dir)

            #Import images
            matprefix = context.scene.mat_prefix

            print(f"\nImporting images from: {tex_dir}\n")
            for fname in os.listdir(tex_dir):
                full_path = os.path.join(tex_dir, fname)
                img_name = os.path.splitext(fname)[0]

                img = bpy.data.images.get(img_name)
                if img is None:
                    img = bpy.data.images.load(full_path)
                    img.name = f"{matprefix}{img_name}"

                img.use_fake_user = True

            #Create imageEmpties
            print(f"\nCreating images (empty containers) with tpl data\n")
            images = txImg.build_images_from_scene(tpl, tex_list, context)

            #Create materialEmpties
            print(f"\nCreating materials (empty containers) with image data\n")
            matData = dmd.data.materialData
            materials = txMat.build_materials_from_scene(matData, tex_list, context)

            bpy.context.view_layer.update()

            for window in bpy.context.window_manager.windows:
                for area in window.screen.areas:
                    area.tag_redraw()

            #create cam_road
            if c_file:
                cam.create_camroad_from_binary(cam_road, context)

            #Create geometry
            global geomDebug
            geometries.build_geometry_from_dmd(dmd, context, geomDebug)

            #Create lights
            lights.build_lights_from_scene(dmd.data.lightData, matprefix, context)

            #Flip world axis before baking animations
            streamLine.main(matprefix)

            #Create animation tracks
            animations.build_anims_from_scene(dmd.data.animationData, matprefix, context)

        return {'FINISHED'}
    


    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, "tex_import", text="Import Textures")
        layout.prop(context.scene, "orph_mat_clear", text="Clear Existing Materials")
        layout.prop(context.scene, "mat_prefix", text="Prefix for unique material names")

def menu_func_import(self, context):
    self.layout.operator(ImportBinaryFileOperator.bl_idname, text="Import DMD Map File (d)")

#region: register
_registered = False

classes = (
    ImportBinaryFileOperator,
    panel.TTYDMeshMemberRef,
    panel.TTYDEmptyMatMeshMemberRef,
    panel.TTYDEmptyMainMaterialRef,
    panel.TEVConfig,
    panel.texCoordTransform,
    panel.SamplerTEX,
    panel.Sampler,
    panel.curveData,

    panel.TTYD_OT_add_sampler,
    panel.TTYD_OT_remove_sampler,
    panel.TTYD_OT_add_joint_anim_track,
    panel.TTYD_OT_remove_joint_anim_track,
    panel.TTYD_OT_sync_joint_anim_tracks,
    panel.TTYD_OT_sync_joint_anim_delta_from_loc,
    panel.TTYD_OT_select_object,
    panel.TTYD_OT_rebuild_local_ir,
    panel.TTYD_OT_rebuild_camroad_ir,
    panel.TTYD_OT_stripify_mesh,
    panel.TTYDLocalVertex,
    panel.TTYDLocalPrimitive,

    panel.TTYDWorldMeshProperties,
    panel.TTYDWorldEmptyProperties,
    panel.TTYDWorldCurveProperties,
    panel.TTYDJointAttributes,
    panel.TTYDLightProperties,
    
    panel.TTYDJointAnimTrack,
    panel.TTYDUVAnimTrack,
    panel.TTYDAlphaAnimTrack,
    panel.TTYDLightTransAnimTrack,
    panel.TTYDLightParamAnimTrack,

    panel.TTYDJointAnimTable,
    panel.TTYDUVAnimTable,
    panel.TTYDAlphaAnimTable,
    panel.TTYDLightTransAnimTable,
    panel.TTYDLightParamAnimTable,
    
    panel.TTYDEmptyAnimationProperties,
    panel.TTYDEmptyTextureProperties,
    panel.TTYDEmptyMaterialProperties,

    panel.TTYDMaterialProperties,
    panel.TTYDMaterialPanel,
    panel.TTYDWorldPanel,
)

def register():
    global _registered
    if _registered:
        return
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.ttyd_world_mesh = bpy.props.PointerProperty(
        type=panel.TTYDWorldMeshProperties
    )

    bpy.types.Object.ttyd_world_empty = bpy.props.PointerProperty(
        type=panel.TTYDWorldEmptyProperties
    )

    bpy.types.Object.ttyd_world_curve = bpy.props.PointerProperty(
        type=panel.TTYDWorldCurveProperties
    )

    bpy.types.Object.ttyd_attributes = bpy.props.PointerProperty(
        type=panel.TTYDJointAttributes
    )

    bpy.types.Object.ttyd_world_animation = bpy.props.PointerProperty(
        type=panel.TTYDEmptyAnimationProperties
    )

    bpy.types.Object.ttyd_world_light = bpy.props.PointerProperty(
        type=panel.TTYDLightProperties
    )

    bpy.types.Object.ttyd_world_material = bpy.props.PointerProperty(
        type=panel.TTYDEmptyMaterialProperties
    )

    bpy.types.Object.ttyd_world_texture = bpy.props.PointerProperty(
        type=panel.TTYDEmptyTextureProperties
    )

    bpy.types.Material.meshReferences = bpy.props.PointerProperty(
        type=panel.TTYDMaterialProperties
    )
    
    bpy.types.Scene.tex_import = bpy.props.BoolProperty(
        name="Import Textures",
        description="Pulls 't' file from same directory to create textures for materials",
        default=True,
    )  # type: ignore

    bpy.types.Scene.orph_mat_clear = bpy.props.BoolProperty(
        name="Delete Materials",
        description="Deletes existing material data in the blender file",
        default=True,
    )  # type: ignore

    bpy.types.Scene.mat_prefix = bpy.props.StringProperty(
        name="Only use for previewing reasons to avoid material overlap. They will break roundtrip logic if not replacing TPL.",
        default="",
    ) #type: ignore

    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    
    _registered = True

def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)
    del bpy.types.Object.ttyd_world_mesh
    del bpy.types.Object.ttyd_world_empty
    del bpy.types.Object.ttyd_world_light
    del bpy.types.Object.ttyd_world_material
    del bpy.types.Scene.mat_prefix
    del bpy.types.Scene.orph_mat_clear
    del bpy.types.Scene.tex_import

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)