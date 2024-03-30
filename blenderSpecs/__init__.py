import bpy
import math

# Clear existing mesh objects in the scene
bpy.ops.wm.read_factory_settings(use_empty=True)

# Specify the bl_idname of the addon operator to enable
addon_bl_idname = "io_scene_ttyd"  # Replace with the actual bl_idname

# Check if the addon is already enabled
if addon_bl_idname not in bpy.context.preferences.addons:
    # Enable the addon
    bpy.ops.preferences.addon_enable(module=addon_bl_idname)

# Save the preferences to make the changes persistent
bpy.ops.wm.save_userpref()

# Iterate through all scenes in the project
for scene in bpy.data.scenes:
    # Set the viewport shader to 'MATERIAL' for each 3D view
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                for space in area.spaces:
                    if space.type == 'VIEW_3D':
                        space.shading.type = 'MATERIAL'
                        break

# Print a message to indicate completion
print("Viewport shader set to 'MATERIAL' for all scenes.")

# List of workspace names to keep
allowed_workspaces = {"Layout", "UV Editing", "Shading", "Animation", "Scripting"}

for ws in bpy.data.workspaces:
    if ws.name not in allowed_workspaces:
        bpy.data.batch_remove(ids=(ws.id_data,))

bpy.ops.file.pack_all()