import bpy
import os

bpy.ops.file.pack_all()

# Set the directory path
output_directory = bpy.path.abspath("//../output")

# Get a list of files in the directory
files = os.listdir(output_directory)

# Iterate through the files
for file in files:
    filepath = os.path.join(output_directory, file)
    
    # Check if it's a file without an extension
    if os.path.isfile(filepath) and '.' not in file:
        # Get the name without extension
        file_name = os.path.splitext(file)[0]
        
        # Save the current Blender file with the same name and .blend extension
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(output_directory, f"{file_name}.blend"))
        
        print(f"Saved {file_name}.blend")
        
        # Delete the extensionless file
        os.remove(filepath)
        print(f"Deleted {file}")

print("Script completed.")
