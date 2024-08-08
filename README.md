Hi! Excited you're interested in using my (VERY) WIP script-set to make editing TTYD maps easier.
This entire process has only been made possible thanks to the efforts of PistonMiner, Jasper (noclip), Jemaroo, Jdaster64, Rain, Peardian, and many others in the Petalburg (https://discord.gg/kGzG2BtsBX), Noclip (https://discord.gg/zGFeKVRv5v), and other discord servers

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
