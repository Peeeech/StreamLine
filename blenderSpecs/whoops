import bpy
import os

# Set the path to the directory containing the Collada file
collada_directory = r"C:\Users\treyt\Desktop\Rogueport"
collada_file = r"gor_03.dae"
collada_filepath = os.path.join(collada_directory, collada_file)

# Import Collada file
bpy.ops.wm.collada_import(filepath=collada_filepath)

# Create an empty .txt file with the same name as the Collada file
script_directory = os.path.dirname(os.path.abspath(__file__))
output_directory = os.path.join(os.path.dirname(script_directory), 'output')
txt_filename = os.path.splitext(collada_file)[0]
txt_filepath = os.path.join(output_directory, txt_filename)

# Open and close the file to create an empty file
with open(txt_filepath, 'w'):
    pass

print(txt_filepath)
