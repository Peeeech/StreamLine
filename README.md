# PLEASE READ INSTRUCTIONS BELOW:
To export this with PistonMiner's exporter, you will need to change one of the scripts within it. You will have to open 'dmd.py' which is right inside the io_scene_ttyd folder in your addons folder.
You need to replace lines 750-751, which are:

initially:
                            tc_layer_name = blender_uv_layers[tc_index]
							tc_layer = blender_mesh.uv_layers[tc_layer_name]
replace it with:
                            tc_layer = blender_mesh.uv_layers.active

You should be able to just use CTRL+F to search "tc_layer_name" without quotations to find the first of the two lines that need replaced, as it's the only occurrence of it in the script. 

After replacing the lines, the entire 'if' statement should read as follows (starting on line 749, finishing on line 756):
                            if tc_index < len(blender_uv_layers):
								tc_layer = blender_mesh.uv_layers.active
								tc_data = tuple(tc_layer.data[loop_index].uv)
							else:
								# todo-blender_io_ttyd: Figure out if this is a
								# fatal error; probably should be.
								assert(False)
								tc_data = (0.0, 0.0)

# StreamLine
Second iteration of streamLine project, complete overhaul of previous method

# Once again, This entire process has only been made possible thanks to the efforts of:
PistonMiner, Jasper (noclip), Jemaroo, Jdaster64, NWPlayer, Rain, Peardian, and many others in the Petalburg (https://discord.gg/kGzG2BtsBX), Noclip (https://discord.gg/zGFeKVRv5v), and other discord servers

With help from Peardian's code, who uploaded the models to the ModelsResource using an exporter made from some of noclip's source code, I was able to get their modified code running in Node to get rid of any html code used. This version of streamLine now lets you import a 'd' map file straight into blender, and it will parse the data to create the map. It's far from perfect, still not having any animation data, but it handles geometry, vertex colors, UV maps, as well as importing the 't' file (assuming it's in the same folder that 'd' was) and will produce the images and materials necessary for the scene. It also has operator presets to disable importing or altering textures/materials at all, as well as disabling the final step of reorganizing into collections/applying transformations to the geometry. I plan on trying to update it to where Node isn't necessary, but this may lead to requiring some other python libraries.

# NOTE:
Using this tool requires having Node installed and linked to your path variable (my version is v20.11.0 if you ever run into errors with a different version)
https://nodejs.org/en/download

# NOTE 2:
Using the images section of this tool will also try to install PIL if you do not have it installed, which considering blender's native python API doesn't, you probably won't. I set up the installation subprocess a long time ago and haven't tested it much, so please let me know if it doesn't work and I will try to fix it. If you would not like to use PIL, you would have to uncheck the 'Import Textures' checkbox, as it's vital for checking for transparency when creating the materials.

Finally, if you run into any problems, or if you get a console message in blender that says to contact me, it's due to UVColors not being implemented, as none of the maps I tested had them, and I haven't been able to work on them because of it.

SET-UP
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
1. Install Node (https://nodejs.org/en/download) and ensure it's linked to your path variable
2. Put the io_scene_pmmap folder into your blender's addons folder
3. Open blender and click 'Edit' -> 'Preferences' -> 'Add-ons' -> Find and endable "Import-Export: PMMap Parser"
4. When you click 'File' -> 'Import' a new option will be present, with this, import a 'd' file from a dumped ISO of Paper Mario TTYD
    (Note: the 'Import Textures' functions will only work properly if the 't' file is in the same directory as the selected 'd' file)
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

TO EXPORT
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Using PistonMiner's IO_Scene_TTYD: (https://github.com/PistonMiner/ttyd-tools/)
1. Make sure that after importing with this addon that you save the .blend file and reopen it before trying to export, or it will just export a blank file.
2. Ensure all materials follow the format present in either node example
3. Ensure all objects have a UV Map named 'UVMap' and a Vertex group named 'Col'
4. Select each collection respectively with the operator presets and click export
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

# Extras from my deprecated repo:

SOME TERMS
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Blender terms (in relation to this, any knowledge on blender as a program will have to be either asked directly or learned on your own time),
 - The `MAP` collection is all of the `VISIBLE` data that you see while playing the game. Inherently, Mario won't collide with anything in this collection, as like stated, it is ONLY the VISUAL data
 - The `HIT` collection is all of the `COLLISION` data that Mario interacts with. This can exist where there is no object in the Map collection to make invisible walls, or can be omitted to make objects not be collided with
     When adding a new object, moving it, or deleting it in the Map collection, ensure that you alter the Hit collection so that Mario reacts to it as intended, whether it be hitting it or not
 - The `CAM` (or whatever you name it) collection is the `CAMERA` road data, that controls how the camera moves based on where you are in the room at any given point.

File terms (when exporting 3 files are created, which share names with 3 of the files in a map folder)
 - The `d` file contains `map data`, including the Map and Hit collections' data, and animation data (in the original files, and when it's properly processed by this)
 - The `t` file contains `texture data`, including all textures used across the entire map
 - The `c` file contains `camera data`, including the paths the camera follows and the zones where it's active
Also, in any maps with NPC's there's an `s` file, which contains `sprite data` for each location. At the moment this isn't integrated into this program in any way. Though it may be far in the future, I wouldn't expect it any time soon

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

CAMERA ROAD
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

To effectively make a custom camera path you're going to need (at least) 2 things

A Nurbs Path which is the actual path the camera follows
A Plane mesh which dictates the area you're in to make the camera follow said path

To set up the camera path;

1. Create the Plane mesh and scale it to where you want the camera to follow the path (the size of the Nurbs Path follows in relation to the size of the Plane, so the easiest method would probably be to have the Path go from one end of the plane to another)
2. Create the Nurbs Path and edit vertices of it (subdividing it if you want to make it go in different directions without making a second set)
3. Once both objects are in the desired locations click on the Path object and in the `Context` menu underneath the Scene Collection (Context is the orange square with 4 extruded corners around it) and expand `Custom Properties`
4. Add a new custom property named `clamp_distance_left` and set the `Property Value` to how far left of Mario you want the camera to reside
5. Add a new custom property named `clamp_distance_right` and set the `Property Value` to how far right of Mario you want the camera to reside
     (Setting these numbers to the same value will center the camera on him)
6. Add one last custom property named `marker0` and set the Property Value to the same name as the Plane Mesh you created earlier

This process can be repeated, adding a new set of objects to create multiple "zones" where the camera follows differing paths, just ensure you update the `marker0` property to reflect the correct name of the mesh you want that line to adhere to if you duplicate the first set of camera objects

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
