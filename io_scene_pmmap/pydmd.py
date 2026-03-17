""" 
    ========================================================================
    Parsing script to parse data from Paper Mario: TTYD/SPM's DMD Map files
    Based on PistonMiner's MarioST_WorldData.bt Template in 010 Editor
                            -Peech (Hamptoad)
    ========================================================================

    This is the main driving script, which will be implemented into a Blender addon (alongside
    a forked version of Piston's io_scene_ttyd exporter) to push data straight into Blender
    to preserve as many nuanced variables as possible, and make round-trip source-code and
    custom maps be as close to 1:1 as possible

    --------------------------------------------------------------------
    Execution flow:
    --------------------------------------------------------------------
    (from CLI or from Blender's operator)
    
    ----------------------------------
    
    pyDmd.remoteCall(file_path, parse_dmd=True/False, parse_tpl=True/False, parse_cam_road=True/False)
        where the boolean flags default to Parse DMD, but can be set to parse TPL or cam_road files instead, which are used for textures and camera roads respectively

    remoteCall()
        -> if parse_dmd: calls DMDFile.parse() and returns a DMDFile object with all of the parsed data organized into its attributes
        -> if parse_tpl: calls TPLParse.parse_tpl() and returns the parsed TPL data as a tuple of (header, tplData)
        -> if parse_cam_road: calls CamParse.parse_cam_road() and returns the parsed cam_road data as a CamRoadData object

        Notably, remoteCall also has a commented-out Summary() function which can be used to print out the parsed data in a more human-readable format

    ----------------------------------

    in Blender mode:
    (from __init__.py, in the execute function of the operator)
    remoteCall() 
        -> gets the DMDFile obj
            - imports the TPL and Cam_Road data as well

            -> uses TPL data to create Blender textures and materials (from DMD data)
            -> uses cam_road data to create Blender camera roads and region planes
            -> uses DMD data to create Blender visual/collision geometry
            -> uses DMD data to create Blender lights
            -> uses DMD animation data to create Blender animation tracks and keyframes
            -> uses StreamLine.py to clean up the scene and apply the coordinate system conversion

    Pipeline Diagram:
    --------------------------------------------------------------------

    DMD File
    │
    ▼
    DMDParse.py
    │
    ├── TPLParse.py     (textures)
    ├── CamParse.py     (camera roads)
    │
    ▼
    DMDFile Object (IR)
    │
    ▼
    Blender Integration
    ├── materials.py
    ├── geometries.py
    ├── lights.py
    ├── animations.py
    ├── cam.py
    │
    ▼
    streamLine.py
    │
    ▼
    Final Blender Scene

    --------------------------------------------------------------------
    Project Architecture (as of 3/15/26):
    --------------------------------------------------------------------
            
    ./parsers/
        DMDParse.py: 
            Parses the DMD file into organized data structures, based on Piston's template. This is the core of the project, and
            the other parsers (tplparse and camparse) are essentially used as 'add-ons' to this main parser, since they are only used
            for texture and cam_road parsing, which are secondary to the main DMD parsing. This is also kept separate to allow for
            later implementation of a sort-of SDK for parsing DMD files in other contexts.

        TPLParse.py:
            Parses TPL texture files, which are used for textures in DMD files. This is only used for the texture parsing part of the DMD parsing,
            as materials themselves are handled within the DMD

        CamParse.py:
            Parses cam_road files, which are used for camera roads in DMD files. These are entirely separate from the main DMD parsing, 
            but take up the same world space, and are best visualized alongside the DMD data, so this is included as a 'companion' parser to the main DMD parsing.

    ----------------------------------
            
    ./classes/
        These are essentially just dataclasses structured like C-headers to allow for easier object management and organization, without polluting parsing / IR-creation

        animationH.py:
            Contain all of the keyframes, tracks, and animation table data classes
            (The AnimBundle is the top-level class, which contains the AnimationTables, which contains the Tracks, which contain the Keyframes)

        camH.py:
            Contains all of the cam_road data classes, which are used to organize the cam_road data into more manageable objects, 
            namely just the header, raw data, and organized data classes
            (The CamRoadCurve class is the main one, which contains all of the data for each individual curve, and is stored in a list within the CamRoadData class)

        materialH.py:
            Contains all of the material and texture data classes, which are used to organize the material and texture data from the DMD file into more manageable objects, 
            namely just the Texture, Sampler, and TEV classes, which are stored in lists within the MaterialData class

        objectsH.py:
            Contains the main data classes for the DMD object representations, which are mainly what are created in Blender / repr'd as empty objects in the scene graph.
            They also have a couple helpers used for mesh organization
        
        tableClasses.py:
            Contains the main data classes for the DMD tables, which are used to organize the raw table data from the DMD file into more manageable objects, 
            this is essentially the "main" header for the file itself, as the tables themselves are the top-level objects that the rest of the data is organized around, 
            and the DMDFile object itself revolves around.

        tplH.py:
            Contains the main data classes for the TPL texture data, which are used to organize the texture data from the TPL files into more manageable objects, 
            namely just the TextureHeader and TextureData classes, which are stored in lists within the TextureTable class

        tuplesH.py:
            Contains some helper data classes for tuples, such as XYZ and ColorRGBA, which are used throughout the other data classes to represent common data structures in a more manageable way.
            (ColorRGBA, XYZ, TanXY, and BBox)

    ----------------------------------

    ./materials/
        Contains material/texture management code, for things like decompiling the tpl textures, handling IR creation for materials and textures, and creating the actual Blender materials
        and textures. Materials are created in 2 stages, the first stage is the "EmptyMaterials" which are the empty objects used purely as representation/authoritative export data, and
        the second stage is the "PreviewMaterials" which are actual Blender Materials created with material nodes, to replicate GX materials as closely as possible, and to allow for better
        visualization of the materials in Blender, without worrying about the export data relying on finnicky node setups. 

        decode.py:
            Contains the code to decode the TPL texture data

        images.py:
            Contains the code to create and manage the actual Blender image data for the textures

        imageStream.py:
            Converts the IR decoded texture data into actual images

        materials.py:
            Contains the code to create and manage the actual Blender materials

    ----------------------------------

    ./Blender
        Contains the Blender-specific code to push data into Blender, and manage the UI
        (This is kept separate to avoid Blender dependencies in the core parsing code, and to make
        it easier to test the parsing code outside of Blender)

        animations.py:
            Contains the code to create and manage the Blender animation data, such as creating the animation tracks and keyframes from the DMD animation data

        cam.py:
            Contains the code to create and manage the Blender camera data; the camera roads / region planes from the cam_road data

        geometries.py:
            Contains the code to create and manage the Blender geometry data, such as creating the meshes from the DMD scene graph data
            (an update on the PreviewMaterials happens during this stage as well, as GX materials are rendered in "passes" unlike blender. Because of things like
            custom Draw_Modes which are embedded into the actual Joint/Mesh data, the materials have to be updated during the geometry creation stage to ensure that
            the material data is correct for the geometry, and not just a generic "preview" material)

        lights.py:
            Contains the code to create and manage the Blender light data, such as creating the lights from the DMD light table data

        panel.py:
            Contains the code to create the Blender UI panel for the addon, where all of the custom MetaData is displayed, viewable, and editable.

        streamLine.py:
            A final "clean-up" stage for the Blender data which is used to separate the sceneGraph cleanly into 'Map' and 'Hit' collections, as well as
            to apply the matrix conversion to display the normally Y-up DMD data in Blender's Z-up coordinate system

    --------------------------------------------------------------------
"""
import argparse

try:
    # Try relative import (when running as part of package)
    from .parsers import dmdparse as parseMain
except ImportError:
    # Fallback to absolute import (when run standalone)
    from parsers import dmdparse as parseMain
    
class DMDFile:
    def __init__(self):
        self.header = None
        self.info = None
        self.textures = []
        self.materials = []
        self.joints = []

    def parse(self, file):
        with open(file, "rb") as f:
            self.header = parseMain.header(f)
            offs = 32
            self.data = []

            self.offsetTable = parseMain.offsetTable(f, self.header, offs)
            self.tables = parseMain.table(f, self.header.table_count)

            self.animation_table = parseMain.animation_table(f, offs, self.tables)
            self.curve_table = parseMain.curve_table(f, offs, self.tables)
            self.fog_table = parseMain.fog_table(f, offs, self.tables)
            self.info = parseMain.info(f, offs, self.tables)
            self.light_table = parseMain.light_table(f, offs, self.tables)
            self.material_name_table = parseMain.material_name_table(f, offs, self.tables)
            self.texture_table = parseMain.texture_table(f, offs, self.tables)
            self.vcd_table = parseMain.vcd_table(f, offs, self.tables) if getattr(self.info, "versionString", None) == "ver1.02" else None

            self.tables.add_tableData("animation_table", self.animation_table)
            self.tables.add_tableData("curve_table", self.curve_table)
            self.tables.add_tableData("fog_table", self.fog_table)
            self.tables.add_tableData("information", self.info)
            self.tables.add_tableData("light_table", self.light_table)
            self.tables.add_tableData("material_name_table", self.material_name_table)
            self.tables.add_tableData("texture_table", self.texture_table)
            if self.vcd_table is not None: #for a few old Ver1.00 maps found in ttyd-disk-source
                self.tables.add_tableData("vcd_table", self.vcd_table)

            self.data = parseMain.vcdData(f, file, offs, self.tables, versionString=getattr(self.info, "versionString", None))

            self.sceneGraph = parseMain.sceneGraph(f, file, offs, self.tables, self.data, versionString=getattr(self.info, "versionString", None))

            return self.sceneGraph


    def summary(self):
        """Optional: print or return summary info"""
        print("---- DMD Summary ----\n")
        print(f"Header: {self.header}")
        print(f"Tables: {self.tables}")

        print(f"Animation Table: {self.animation_table}\n")
        print(f"Curve Table: {self.curve_table}\n")
        print(f"Fog Table: {self.fog_table}\n")
        print(f"Info: {self.info}\n")
        print(f"Light Table: {self.light_table}\n")
        print(f"Material Name Table: {self.material_name_table}\n")
        print(f"Texture Table: {self.texture_table}\n")
        print(f"VCD Table: {self.vcd_table}\n")

        print(f"Textures: {self.texture_table.count}")
        print(f"Materials: {self.material_name_table.count}")
        print(f"Joints: {len(self.joints)} (these aren't read yet, ignore this)")

            #.data contains: .[positionData, normalData, colorData, textureCoordinateData, lightData, animationData, materialData]

        #print(f"\n================ ANIM DATA START ================\n\n{self.data.animationData}")
        
        #print(self.sceneGraph) - as a replacement, use 'py scene_viewer [path/to/dmd/file]'

def remoteCall(file, parse_dmd=True, parse_tpl=False, parse_cam_road=False):
    if not parse_tpl and not parse_cam_road:
        dmd = DMDFile()
        dmd.parse(file)
        #dmd.summary()  
        return dmd
    else:
        try:
            from .parsers import tplparse
            from .parsers import camparse
        except:
            from parsers import tplparse
            from parsers import camparse

    if parse_tpl:
        return tplparse.parse_tpl(file)
    elif parse_cam_road:
        return camparse.parse_cam_road(file)

# Main script
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse DMD map file based off PistonMiner's 010 Template to extract map data.")

    fileType = parser.add_mutually_exclusive_group()

    parser.add_argument("file", type=str, help="The DMD (Display Model Data(?)) file.")
    fileType.add_argument("--d", action="store_true", help="Parse DMD data (default)")
    fileType.add_argument("--t", action="store_true", help="Parse TPL data instead of DMD")
    fileType.add_argument("--c", action="store_true", help="Parse cam_road data instead of DMD")
    args = parser.parse_args()

    args.d = not args.t and not args.c  # Default to DMD parsing if no specific type is chosen

    file = args.file
    dmd = remoteCall(file, args.d, args.t, args.c)