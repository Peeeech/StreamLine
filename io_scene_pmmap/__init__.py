
import bpy  # type: ignore
import os
import shutil
import sys
import importlib.util
import subprocess

from . import pydmd
from .parsers import tplparse as ptpl
from .parsers import camparse as pcam

from .materials import pytpl as tpl
from .materials import images as txImg
from .materials import materials as txMat

from .blender import cam
from .blender import geometries
from .blender import streamLine
from .blender import lights
from .blender import animations

from .blender.ui import worldPanel as panel
from .blender.ui import workspace
from .blender.ui.helpers import cameraRaycast

#from .render import flattenSceneGraph
VISUAL_MODE = False

def checkVisMode():
    mode = getattr(bpy.types.Scene, "visual_map", None)

    if not mode:
        raise Exception("[FATAL] Visual Map scene object returned none")

    return bpy.context.scene.visual_map

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
    if not spec:
        raise Exception

    module = importlib.util.module_from_spec(spec)
    if not module or spec.loader is None:
        raise Exception

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

        print(binary_file, "1")

        if binary_file[-4:] == ".bin":
            print("YAAAY")

        print(binary_file, "2")

        #TODO: SPM implementation - consume .bin directly 

        dmd = pydmd.remoteCall(binary_file)
        if not isinstance(dmd, pydmd.DMDFile):
            raise Exception("This should never trigger.")

        """
        Architecture split: Blender backend vs Render backend
        =====================================================

        At this point the importer diverges into two separate backends which both
        come from the same parsed/localized DMD scene graph, but serve different roles.

        Blender backend
        ---------------
        Role:
            Authoritative authoring/export shell.

        Purpose:
            The Blender scene is intentionally expanded into many objects, empties,
            PropertyGroups, Actions/NLA tracks, material containers, texture containers,
            etc.

            This is not meant to be the fastest or simplest runtime representation.
            It exists so that:
                - Blender can display, select, inspect, and edit DMD data.
                - Properties can be modified through normal Blender UI/RNA paths.
                - The exporter can remain dumb and stable.
                - Export can simply walk named properties/containers and serialize them
                back into a DMD-like file without re-inferring meaning from raw meshes.

        Notes:
            Blender-side data is the long-lived editable representation. It preserves
            structure and metadata even when the render backend uses a more compact form.


        Render backend
        --------------
        Role:
            Derivative runtime/render representation.

        Purpose:
            The render backend receives a flattened binary scene blob representing the
            DMD node scene graph in a renderer-friendly form.

            This blob is built from the parsed/localized scene graph, not by walking
            Blender's evaluated scene every frame.

            Offsets/pointers from the original DMD-style graph are localized into stable
            integer IDs. These IDs are also usable as direct indexes into typed arrays.

        Example:
            material_id = 57

            Instead of storing a pointer to material 57, the render blob stores:

                material_id = 57

            The C++ renderer can resolve this as:

                material_base + (material_id * sizeof(MaterialWork))

            or, conceptually:

                materials[material_id]

            This mirrors the style of the original game/runtime work arrays while
            avoiding raw process pointers in the serialized blob.

        Important:
            The render blob is derived from the authoritative local/Blender-side data.
            It is allowed to be rebuilt, replaced, or optimized at any time.

            The C++ renderer should consume the blob, validate/resolve IDs, and build
            its own runtime state. It should not depend on Blender object traversal or
            Python object lifetimes during rendering.
        """

        if bpy.context.scene.orph_mat_clear:
            for mat in list(bpy.data.materials):
                if mat.users == 0:
                    bpy.data.materials.remove(mat)
            for img in list(bpy.data.images):
                bpy.data.images.remove(img)

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


            header, images = ptpl.parse_tpl(t_file)

            #flatScene = flattenSceneGraph.main(dmd, tpl=(header, images))

            #return {'FINISHED'}

            tpl.clear_directory(tex_dir)

            for i, image in enumerate(images):
                tpl.writeImage(tex_dir, i, image)

            if c_file:
                cam_road = pcam.parse_cam_road(c_file)

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

            #Fill in fog_table data
            if hasattr(bpy.types.Scene, "ttyd_fog_table"):
                fProps = bpy.context.scene.ttyd_fog_table
                fData = dmd.fog_table

                from pprint import pprint
                pprint(fData)

                fProps.fogEnabled = int(fData.wFogEnabled)
                fProps.fogMode = int(fData.fogMode)
                fProps.fogStart = int(fData.fogStart)
                fProps.fogEnd = int(fData.fogEnd)
                fProps.fogColor = (fData.fogColor.r / 255, fData.fogColor.g / 255, fData.fogColor.b / 255, fData.fogColor.a / 255)

            #Create imageEmpties
            if not checkVisMode():
                print(f"\nCreating images (empty containers) with tpl data\n")
                images = txImg.build_images_from_scene(images, tex_list, context)

            #Create materialEmpties
            print(f"\nCreating materials (empty containers) with image data\n")
            matData = dmd.data.materialData
            materials = txMat.build_materials_from_scene(matData, tex_list, context)

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
            if not checkVisMode():
                lights.build_lights_from_scene(dmd.data.lightData, matprefix, context)

            #Flip world axis before baking animations
            streamLine.main(matprefix)

            #Create animation tracks
            animations.build_anims_from_scene(dmd.data.animationData, matprefix, context)

        """
        These should probably go into streamLine for post-processing niceties
        """

        for screen in bpy.data.screens:
            for area in screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        space.shading.type = 'MATERIAL'

        hitLayCol = bpy.context.view_layer.layer_collection.children['Hit']
        hitLayCol.exclude = True

        if checkVisMode():
            bpy.data.collections.remove(bpy.data.collections['Cam'])
            bpy.data.collections.remove(bpy.data.collections['Unused'])
            bpy.data.collections.remove(bpy.data.collections['Lights'])

        return {'FINISHED'}
    


    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, "visual_map", text="Only Visual")
        layout.prop(context.scene, "tex_import", text="Import Textures")
        layout.prop(context.scene, "orph_mat_clear", text="Clear Existing Materials")
        layout.prop(context.scene, "mat_prefix", text="Prefix for unique material names")

def menu_func_import(self, context):
    self.layout.operator(ImportBinaryFileOperator.bl_idname, text="Import DMD Map File (d)")

#region: register

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
    panel.TTYD_OT_sync_joint_anim_pivot_from_loc,
    panel.TTYD_OT_select_object,
    panel.TTYD_OT_rebuild_local_ir,
    panel.TTYD_OT_rebuild_camroad_ir,
    panel.TTYD_OT_set_active_camroad_object,
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
    panel.TTYDWorldPanel,
)

def register():
    for cls in classes:
        try:
            bpy.utils.register_class(cls)
        except:
            pass


    # Custom properties for objects and materials
    bpy.types.Object.ttyd_world_mesh = bpy.props.PointerProperty(type=panel.TTYDWorldMeshProperties)
    bpy.types.Object.ttyd_world_empty = bpy.props.PointerProperty(type=panel.TTYDWorldEmptyProperties)
    bpy.types.Object.ttyd_world_curve = bpy.props.PointerProperty(type=panel.TTYDWorldCurveProperties)
    bpy.types.Object.ttyd_attributes = bpy.props.PointerProperty(type=panel.TTYDJointAttributes)
    bpy.types.Object.ttyd_world_animation = bpy.props.PointerProperty(type=panel.TTYDEmptyAnimationProperties)
    bpy.types.Object.ttyd_world_light = bpy.props.PointerProperty(type=panel.TTYDLightProperties)
    bpy.types.Object.ttyd_world_material = bpy.props.PointerProperty(type=panel.TTYDEmptyMaterialProperties)
    bpy.types.Object.ttyd_world_texture = bpy.props.PointerProperty(type=panel.TTYDEmptyTextureProperties)
    bpy.types.Material.meshReferences = bpy.props.PointerProperty(type=panel.TTYDMaterialProperties)
    
    # Custom import settings
    bpy.types.Scene.visual_map = bpy.props.BoolProperty(name="Purely Visual Map Geometry", description="Strips custom properties and Local IRs for purely visual map", default=VISUAL_MODE)

    bpy.types.Scene.tex_import = bpy.props.BoolProperty(name="Import Textures", description="Pulls 't' file from same directory to create textures for materials", default=True)  # type: ignore
    bpy.types.Scene.orph_mat_clear = bpy.props.BoolProperty(name="Delete Materials", description="Deletes existing material data in the blender file", default=True)  # type: ignore
    bpy.types.Scene.mat_prefix = bpy.props.StringProperty(name="deprecated.", description="Only use for previewing reasons to avoid material overlap. They will break roundtrip logic if not replacing TPL.", default="") #type: ignore

    # Add the import option to the File > Import menu
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)
    
    # External registers
    workspace.register()
    cameraRaycast.register()

def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

    workspace.unregister()
    cameraRaycast.unregister()

    objattributes = ["ttyd_world_mesh", "ttyd_world_empty", "ttyd_world_light", "ttyd_world_material",]
    sceneattributes = ["visual_map", "mat_prefix", "orph_mat_clear", "tex_import",]

    for attr in objattributes:
        if hasattr(bpy.types.Object, attr):
            attribute = getattr(bpy.types.Object, attr)
            del attribute

    for attr in sceneattributes:
        if hasattr(bpy.types.Scene, attr):
            attribute = getattr(bpy.types.Scene, attr)
            del attribute

    for cls in reversed(classes):
        try:
            bpy.utils.unregister_class(cls)
        except:
            pass