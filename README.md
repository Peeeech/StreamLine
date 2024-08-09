Hi! Excited you're interested in using my (VERY) WIP script-set to make editing TTYD maps easier.
This entire process has only been made possible thanks to the efforts of PistonMiner, Jasper (noclip), Jemaroo, Jdaster64, NWPlayer, Rain, Peardian, and many others in the Petalburg (https://discord.gg/kGzG2BtsBX), Noclip (https://discord.gg/zGFeKVRv5v), and other discord servers

Now to get into utilizing the tool itself

Forewarning, the installation of blender doesn't include PistonMiner's ttyd-tools, specifically the blender_io_ttyd (https://github.com/PistonMiner/ttyd-tools/) which is necessary to export the maps from Blender to be useable in Roms and in-game
Running these scripts runs a background operation of Blender so that all of the scripts can be applied to the 3d model in order without risk of something going wrong, as well as being able to set up the blender workspace for easier editing.
Running these also installs PIL into blender's Python directory, this will only affect the version of Py included with the Blender-2.80, and won't install it into other Blender versions or affect your Python installation if you have any versions installed on your PC itself.
PIL is utilized to check for any transparency in model's textures, as these have to be handled differently in terms of mapping materials for use with Piston's exporter, to ensure they meet proper criteria for becoming a working texture in-game.

When running the TTYB.exe file you may get a warning along the lines of "Windows protected your PC", as even I get this warning if I install a new version of it and run it. This is a false report from Windows due to the nature of how part of the script works,
which alters a different script so that the program can use a file dialogue window rather than having to type in the file directory for ease-of-use. Once I get more experienced with writing programs this might be something I can fix, but as it stands I don't know how.


SET-UP
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

1. Download the latest release of StreamLine
2. Run the Blender installation shortcut which will download the windows64 version of Blender-2.80
     (if you're running Win32 my scripts are hardcoded to the Win64 folder name, though you can probably alter `blend.bat` to change the `cd` command to the proper name for the Win32 folder,  I can't guarantee everything will work correctly)
3. Open the Blender zip and move the folder inside `blender-2.80-windows64` into the root of StreamLine
     (ensure not to extract the folder as this can lead to an extra subfolder, which will break directories of the scripts, you can also delete the shortcut that leads to the blender download if you'd like)
4. Run TTYB.exe
     (if it says `Windows protected...` just click `More/View Details` or whatever it says and hit `Run Anyways`)
5. Click ReplaceDir and choose the location of your COLLADA (.dae) model
     (REMINDER - these scripts are currently (as of 8/8/24) based on the exported models from Peardian available at (https://www.models-resource.com/gamecube/papermariothethousandyeardoor/) and are only designed for the map models, listed below)
     (This may change as I work on a different program to parse the data differently, which if made publically available will probably be a branch from this)
6. Click BATCH and a Command Prompt should open up, let it run
     (Regarding any concern, this command prompt isn't actually running any batch code except to start blender, it runs a background process of it (no UI) to run the scripts as mentioned before, the console is just for debugging)
7. Navigate into the `output` folder and you'll find a file named whatever your COLLADA file's name was, but (.blend) in place of (.dae)
8. Open it with blender and edit what you'd like, more specifics on areas are listed below depending on what your intentions are
     (Ensure you open it with Blender 2.80, if you don't have any other versions of blender installed you can ignore this, but Piston's exporter is only properly tested with this version of Blender. Toy with others at your will, but no guarantees on results.)

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

EXPORTING
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

First and foremost, to just export a map in general using Piston's exporter you need 3 collections (collections are visible in the top-right of Blender when in the Layout tab)
Before you can export you need a third collection to use as the Camera data, this collection can be empty, but it needs to exist. Right click in the blank space under the Scene Collection and create new, I would recommend naming it `Cam`
     For more information on creating the Camera Road, keep scrolling
When exporting select the collections that match the title, unless you named the Camera Road collection something else, but Map and Hit should follow suit with the exporter

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

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

TEXTURES
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

To update textures there's a couple ways to do the same thing, while having the versatility of updating multiple maps/objects or just a single one if you want.

COLLADA files don't inherently pack textures into them, so all the texture files will be present in the map folder you downloaded from the Models Resource. If you want to update textures for all maps you can just change these textures and reload Blender if you had it open. They should immediately update when re-opened. This can be nice for updating everything quickly, but bothersome if you want some updated for one map but not another. To separate a map's textures from the ones in the folder, so you can edit them separately, click on `File -> External Data -> Pack Into .blend`

This will increase the size of the .blend file, as it now contains all the textures used in it, but it also makes the file completely portable, without worrying about the directory the original textures

EDITING TEXTURES
To actually edit the textures themselves you can either export them independently from the `UV Editing` menu to edit one-by-one by selecting the object, opening it, and clicking the `UV` dropdown, then clicking `Save as` to edit individually, or you can export the entire set of textures to a new folder to edit as many as you want
The easiest way to export all of them is going to `File -> External Data -> Unpack All Into Files -> Write files to current directory`, this will make a folder named `Textures` inside the folder your `.blend` is in, which if you haven't moved, will just be directly in the `output` folder of StreamLine 
To import the textures back in you'll either have to replace the texture from the source folder or replace the image in the `Shading` menu explained below

REPLACING TEXTURES
To replace a specific texture for ALL objects that use that same texture, go into the `Shading` menu at the top of Blender and select the object that uses the texture you want to replace, and at the bottom of the screen you'll see the Node tree
In the `Base Color` node, the leftmost node with the orange header, it'll list out information about how the texture is wrapped for the material, `Linear`, `Flat`, `Repeat`, `Single Image`, etc.
     Directly above that you'll see a text line that has the name of the texture, with a box to the left that you can use to replace with a texture already in the project
     There's 4 boxes to the right of that text-line, the first one you don't really need to utilize for this unless you know what you're doing, the second one is if you want to create a new image inside Blender, which I wouldn't recommend, the third one is another to ignore unless you know what you're doing.
     The one you're most likely going to use is the 4th one, which lets you get rid of the texture associated with the material. You can then select `Open` to choose a new texture from your computer.

CREATING NEW
Creating a new material you'll have to match the node tree to the NodeExample.png to ensure it's compatible with TTYD's textures

TRANSPARENCY
If you replace a non-transparent texture with something that has transparency, or create a new material with transparency, the easiest way to ensure it's compatible is to make the node tree matches the tree in the NodeTransparentExample.png image

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

ANIMATIONS
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

THIS WILL BE UPDATED WHEN ANIMATION DATA IS PROPERLY ASSESSED

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

ADDING NEW OBJECTS
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

When adding a new object you have to ensure the mesh data for the objects that contains textures is in the `MAP` collection, you  can either clone the object into the `HIT` collection (texture/material data for the Hit collection doesn't get exported, so it's a viable option) but this method can start to make the game laggy if the hitbox object is too complex, so it's recommended to create new hitboxes for complex objects. If the object is relatively simple it can be completely viable to just clone the object to the Hit collection.

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

All of this will (hopefully, granted I remember) be updated in due time, to reflect on future updates if anything drastically changes, or if I remember/learn how to do something.
