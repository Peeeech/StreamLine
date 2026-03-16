# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2019 Linus S. (aka PistonMiner)

import os

import bpy

from . import dmd
from . import tpl
from . import camera_road

def export(context, settings, world_name=None):
	# Generate main DMD
	dmd_file = dmd.DmdFile.from_blender_scene(
		context.scene,
		settings,
		world_name
	)
	dmd_data = dmd_file.serialize(world_name)
	dmd_path = os.path.join(settings["root_path"], "d")
	with open(dmd_path, "wb") as f:
		f.write(dmd_data)
	print("Wrote DMD to {}".format(dmd_path))

	# Generate TPL
	tpl_file = tpl.TplFile()

	tex_col = settings["texture_root"]
	tex_objs = [obj for obj in tex_col.objects if obj.type == 'EMPTY']

	# Sort by index prop if present
	def _tex_index(obj):
		p = getattr(obj, "ttyd_world_texture", None)
		return getattr(p, "index", 0)

	tex_objs.sort(key=_tex_index)

	for idx, obj in enumerate(tex_objs):
		p = obj.ttyd_world_texture

		img = bpy.data.images.get(p.name) or bpy.data.images.get(obj.name)
		if img is None:
			raise RuntimeError(f"Missing Blender image for texture empty '{obj.name}' (props.name='{p.name}')")

		quality = bool(settings.get("cmpr_quality", False))

		tpl_texture = tpl.TplTexture.from_world_texture_props(
			img, p, idx, quality=quality
		)
		tpl_file.textures.append(tpl_texture)

	tpl_data = tpl_file.serialize()
	tpl_path = os.path.join(settings["root_path"], "t")
	with open(tpl_path, "wb") as f:
		f.write(tpl_data)
	print("Wrote TPL to {}".format(tpl_path))

	camera_road_file = camera_road.CameraRoadFile.from_blender_scene(
		context.scene,
		settings
	)
	camera_road_data = camera_road_file.serialize()
	camera_road_path = os.path.join(settings["root_path"], "c")
	with open(camera_road_path, "wb") as f:
		f.write(camera_road_data)
	print("Wrote camera road data to {}".format(camera_road_path))

	return {'FINISHED'}