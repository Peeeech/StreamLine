# QUICK OVERVIEW:
This blender addon works as an almost-lossless I/O for TTYD/SPM DMD, TPL, and Cam_Road files (`d`, `t`, and `c` respectively)

First of all: Huge credit to PistonMiner for the original version of his `io_scene_ttyd` addon from ttyd_tools, which my fork here is derived from

# StreamLine
Third iteration of streamLine project, once again a complete overhaul of previous method

## Once again, This entire process has only been made possible thanks to the efforts of:
PistonMiner, Jasper (noclip), Jemaroo, Jdaster64, NWPlayer, Rain, Peardian, and many others in the Petalburg (https://discord.gg/kGzG2BtsBX), Noclip (https://discord.gg/zGFeKVRv5v), and other discord servers

# NOTE:
The iteration of this tool no longer requires a Node.js install as it's all Python-based, but it does rely on PIL and NumPy libs. PIL and Numpy will automatically attempt to be installed into the blender-embedded python environment upon map-import.

SET-UP
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
1. Put both the `io_scene_pmmap` and `io_scene_ttyd` folders into your blender's addons folder
2. Open blender and click 'Edit' -> 'Preferences' -> 'Add-ons' -> Find and enable `PMMap Importer` and `Paper Mario DMD Map Exporter`
3. When you click 'File' -> 'Import' a new option will be present, with this, import a 'd' file from a dumped ISO of Paper Mario TTYD
    (Note: the 'Import Textures' functions will only work properly if the 't' file is in the same directory as the selected 'd' file, same as the Camera_Road only importing if the 'c' file is in the same dir)
4. When you click 'File' -> 'Export' a new option will be present, with this, collections will automatically be set up upon map import to allow you to choose export directory (note the filename doesn't affect the output)
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# Extras from my deprecated repo:

SOME TERMS
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Blender terms (in relation to this, any knowledge on blender as a program will have to be either asked directly or learned on your own time),
 - The `MAP` collection is all of the `VISIBLE` data that you see while playing the game. Inherently, Mario won't collide with anything in this collection, as it is ONLY the VISUAL data
 - The `HIT` collection is all of the `COLLISION` data that Mario interacts with. This can exist where there is no object in the Map collection to make invisible walls, or can be omitted to make objects not be collided with
     - When adding a new object, moving it, or deleting it in the Map collection, ensure that you alter the Hit collection so that Mario reacts to it as intended, whether it be colliding or rendering
 - The `CAM` collection is the `CAMERA ROAD` data, that controls how the camera moves based on where you are in the room at any given point. It uses curves as 'rails' that the camera slides on, with activation planes that determine regions that activate the rail they're parented to

File terms (when exporting 3 files are created, which share names with 3 of the files in a map folder)
 - The `d` file contains `map data`, including the Map and Hit collections' data, and animation data (in the original files, and when it's properly processed by this)
 - The `t` file contains `texture data`, including all textures used across the entire map
 - The `c` file contains `camera data`, including the paths the camera follows and the zones where it's active

(With SPM the equivalent of these are `map.dat`, `[map_id].tpl`, and `camera_road.bin` respectively. once renamed and replaced in the file bins, these will work directly)

Also, in any maps with NPC's there's an `s` file, which contains `sprite data` (NPC layouts) for each location. At the moment this isn't integrated into this program in any way. Though it may be far in the future, I wouldn't expect it any time soon

--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
CUSTOM PANEL
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Most things will be accessible by clicking on the type of object you want to edit, going to the `Object (Object Properties)` subsection of the `Properties` tab (The Object tab is the orange square with an outline around the corners), and then expanding the `TTYD World Properties` panel.

The panel itself has a few different setups depending on the kind of object, so we'll go through each.

## Attributes (Universal between Empties and Meshes)
Notably some of these are only applied to meshes, but the attributes block is present on every joint in DMD, and certain multi-mesh objects (see `dmdObject`s in Empty-Specifics) need the flags to exist on empties so they are appended to each fragment-mesh

- origin_offset: used as a pivot marker to mimic offsets used by the original exporter, as Maya had extraneous animation-pivots beyond blender's single-origin
- light_mask: a bitmask to define which of the lights in the scene will be rendered on the object (
- draw_mode: uint32 flag to determine how meshes are rendered
- cull_mode: uint32 flag to determine culling mode (simplified to an Enum in renderer)
	- Note: cull_mode: 'BACK' means the back is getting culled, and only the front is visible
 - wFlags: used for visual scene setup
	- Only use-case known is wFlags: (18) on a parent sorts it's children by render-order in-game. this is how multiple decals are layered over each-other without Z-fighting
 - hit_type: used for collision flags
	- simplified to an enum for things like Boat_Panels, Plane_Panels, etc.; hit_val is used as a backup to preserve non-mapped vals, and can be set manually with the enum = 'NONE' to export with

## Empty-Specifics
BOOLS: (dmdObject, isLight, isMaterial, isTexture, isAnimation)
These booleans are used to set up custom panel-drawing to avoid having to set up multiple panels, and have all of the embedded metadata accessible for each object without the flag-setters having to special case metadata accessors

### dmdObject:
- Mesh Members: used to represent multi-mesh objects in a way that they can be recreated on export, as blender doesn't natively support single objects with multiple, distinguishable meshes like DMD does. Not currently creatable manually, only used as a visualizer / lossless preservation

### isLight:
Light Data
- base_color: RGBA color (0-255) of the source GX light
- multiplier: used separate from base_color for animation driving to avoid messing up the static light objects
- spotAngle:
- distanceAttenuationType:
- wFlags: unk
- enableFlags: unk

### isMaterial:
Material Data
- Blender Users: list of meshes using the material, automatically appended from drawMode material variant creation. not manually editable, will eventually be auto-updated by a material-rebuild function
- color: baked RGBA value
- matSrc: boolean flag to either render with baked color / vertex colors in geometry
- unk_009: unk
- blendMode: Used to define whether an object is opaque ('OPAQUE'), translucent ('FULL' [fully blended]), or clipped ('CLIP')
- numTextures: visual repr for how many textures embedded, very unlikely to not ever match sampler count
- blendAlphaModulation: likely the driven value for materialBlendAlpha animations; unk for sure
- textureSamplers: list of sampler objects to register textures in the GX material space. See 'Sampler' in dedicated `Materials` section
- TEV Config: full struct unk, currently only exposes single TEV Mode value, which uses pre-defined render modes in the game to adjust how materials are rendered. Only a select few are currently implemented.

### isTexture:
Texture Data (Simple container to preserve image index / metadata)
- index: used to organize images during serialization, required to preserve round-tripping since the original serializer didn't use any 'obvious' ordering
- texture name: string that needs to match an `Image` datablock in blender 1:1

### isAnimation:
Animation Bundle Data (contains tables for multiple animation types. will be expanded on more in dedicated `Animations` section
BOOLS: 'joint', 'uv', 'alpha', 'lightT', 'lightP'
Universal - track count: essentially the number of independent animations driven by the table
one anim bundle can have anywhere from 0-5 of the bools active, each bool defines an animation table's presence in the bundle.

Joint (Or Light Transform) Table:
Used for mesh animations
- joint (or light): the object being targeted
- keyframeCount: the amount of different positions the animation has
- action: reference to the NLA action that holds keyframe/transformation data

  
UV Table:
Used for texture-transform animations
- name: name of the material being targeted (will attempt to find `name`, `name_v`, and `name_v_x`. this is the exact switch logic the original game used)
- skew: offset for the image pre-animation
- samplerIndex: used to decide which sampler an animation is for; only ever non-zero on multi-sampler materials
- `[mat], [mat_v], [mat_v_x]`: ref to the actual material(s) that the animation affects
- action: reference to the NLA action that holds keyframe/transformation data

Alpha Table: 
unk yet; presumably a way to cleanly animate an entire object's visible alpha for fade-like effects?

Light Transform Table:
See Joint Table; identical except set up for Light objects.
(notably, on export, light transforms are *also* serialized as joint transforms)

Light Param Table:
Used to change things like light color, angle, strength, etc.
(all driven parameters are found in the `Object` panel for the light)
- name: name of light targeted
- action: reference to the NLA action that holds keyframe/transformation data
  
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
ANIMATIONS
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

To create custom animation tracks, I would highly recommend first finding a map with the custom animation type you want to see how the layouts are set up and to have a reference guide
- Note that no maps in TTYD use the `matAlphaBlend` animation table with any meaningful data. (one case exists, but the values are zeroed out and presumably not called in the map's REL)

- Also note that animation tracks added to a map will have to be called with a REL patch, unless the map already calls the AnimBundle(DMDAnimation container name). Removing animation data or objects / materials that source maps rely on will lead to crashes when the game tries to load them, so removing existing animations isn't currently a trivial task.

Within the `Animations` collection, each empty inside acts as a DMD-Animation-Bundle object, for the exporter to serialize at the top-level. Animation drivers from the REL are inherently activated by calling the name of the bundle (the name is stored within the `isAnimation` section of the empty container)

TODO: Finish dedicated sections

--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
