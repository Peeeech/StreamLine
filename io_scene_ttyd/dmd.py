# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2019 Linus S. (aka PistonMiner)

from collections import defaultdict
import struct
import math
import datetime
from dataclasses import dataclass
from mathutils import Vector #type: ignore

import re
import bpy
import mathutils

from .util import *

def linear_to_srgb(linear):
	# Linear to sRGB conversion excluding alpha channel if present
	out_components = []
	for linear_component in linear[:3]:
		if linear_component <= 0.0031308:
			component = 12.92 * linear_component
		else:
			component = 1.055 * linear_component ** (1/2.4) - 0.055
		out_components.append(component)
	out_components += linear[3:]
	return tuple(out_components)

class DmdLinker(Linker):
	def add_string(self, source_name, source_offset, text, section_name = "strings"):
		# todo-blender_io_ttyd: Investigate effects of string deduplication
		blob_name = "{}:{}".format(section_name, self.get_uid())
		encoded_string = text.encode("shift_jis") + b"\x00"
		self.add_blob(blob_name, encoded_string)
		self.place_blob_in_section(blob_name, section_name)
		self.add_relocation(source_name, source_offset, blob_name)

# DMD vertex attribute IDs
VERTEX_ATTRIBUTE_POSITION_ID = "position"
VERTEX_ATTRIBUTE_NORMAL_ID = "normal"
VERTEX_ATTRIBUTE_TEXCOORD_ID_PREFIX = "texcoord"
VERTEX_ATTRIBUTE_COLOR_ID_PREFIX = "color"

VERTEX_ATTRIBUTE_TEXCOORD_MAX_COUNT = 8
VERTEX_ATTRIBUTE_COLOR_MAX_COUNT = 2 # Technically two but color buffer 1 support is broken

# Order in which indices are packed into the individual vertices
VERTEX_ATTRIBUTE_INDEX_ORDER = []
VERTEX_ATTRIBUTE_INDEX_ORDER.append(VERTEX_ATTRIBUTE_POSITION_ID)
VERTEX_ATTRIBUTE_INDEX_ORDER.append(VERTEX_ATTRIBUTE_NORMAL_ID)
for i in range(VERTEX_ATTRIBUTE_COLOR_MAX_COUNT):
	VERTEX_ATTRIBUTE_INDEX_ORDER.append(VERTEX_ATTRIBUTE_COLOR_ID_PREFIX + str(i))
for i in range(VERTEX_ATTRIBUTE_TEXCOORD_MAX_COUNT):
	VERTEX_ATTRIBUTE_INDEX_ORDER.append(VERTEX_ATTRIBUTE_TEXCOORD_ID_PREFIX + str(i))

# Order in which the data referenced by the indices is packed into the data sections
VERTEX_ATTRIBUTE_DATA_ORDER = []
VERTEX_ATTRIBUTE_DATA_ORDER.append(VERTEX_ATTRIBUTE_POSITION_ID)
VERTEX_ATTRIBUTE_DATA_ORDER.append(VERTEX_ATTRIBUTE_NORMAL_ID)
for i in range(VERTEX_ATTRIBUTE_TEXCOORD_MAX_COUNT):
	VERTEX_ATTRIBUTE_DATA_ORDER.append(VERTEX_ATTRIBUTE_TEXCOORD_ID_PREFIX + str(i))
for i in range(VERTEX_ATTRIBUTE_COLOR_MAX_COUNT):
	VERTEX_ATTRIBUTE_DATA_ORDER.append(VERTEX_ATTRIBUTE_COLOR_ID_PREFIX + str(i))

# Helper to convert blender Hit type into related bytes
def _hit_type_to_flag(obj) -> int:
    try:
        hit_type = obj.ttyd_attributes.hit_type
    except Exception:
        return 0

    if hit_type == 'WATER':
        return 0x00000200
    if hit_type == 'SPIKE':
        return 0x00000800
    if hit_type == 'PLANE':
        return 0x00000020
    if hit_type == 'BOAT':
        return 0x00008000
    return 0

CULL_ENUM_TO_VALUE = {
    'FRONT': 0,
    'BACK': 1,
    'ALL':  2,
    'NONE': 3,
}

class DmdTexture:
	"""DMD Texture reference. Does not store pixel data."""
	def __init__(self):
		self.name = ""
		self.size = (0, 0)
		self.render_order = 0

	def link(self, linker):
		texture_blob_name = "textures:" + self.name
		texture_data = bytearray(0x10)
		linker.add_string(texture_blob_name, 0x0, self.name)

		# Everything past here is actually irrelevant because the game fills it
		# in with data from the TPL in mapBuildTexture, but the original exporter
		# puts accurate data here that gets overwritten later, so we will as well.
		struct.pack_into(">L", texture_data, 0x0, 0) # image format
		struct.pack_into(">B", texture_data, 0x4, self.render_order) #higher = render on top of lower vals
		struct.pack_into(">HH", texture_data, 0x8, self.size[0], self.size[1]) # width/height

		linker.add_blob(texture_blob_name, texture_data)
		linker.place_blob_in_section(texture_blob_name, "texture_data")

	@staticmethod
	def from_blender_image(imageEmpty):
		texture = DmdTexture()
		texProps = imageEmpty.ttyd_world_texture
		texture.name = texProps.name
		texture.render_order = texProps.render_order
		texture.size = (texProps.width, texProps.height)
		return texture

# Seems that Nintendo DMD's have shown to prefer pos-Euler angles. Shouldn't be different theoretically, but preserves fidelity.
def normalize_deg_360(angle):
    angle = angle % 360.0
    if angle < 0:
        angle += 360.0

    # silly numbers don't need to be 360
    if abs(angle - 360.0) < 1e-3:
        angle = 0.0

    return angle

class DmdLight:
	def __init__(self):
		self.name = ""
		self.type = ""
		self.position = (0.0, 0.0, 0.0)
		self.rotation = (0.0, 0.0, 0.0)
		self.scale = (1.0, 1.0, 1.0)
		self.color = (255, 255, 255, 255)
		self.spotAngle = 0
		self.angularAttenuation = 0
		self.distanceAttenuationType = 0 # TODO
		self.wFlags = 0 #currently unknown any flag toggles
		self.wEnableFlagsIf012d60d8 = 19751128 # TODO
		
	def link(self, linker):
		light_blob_name = "lights:{}".format(self.name)
		light_data = bytearray(0x44)

		linker.add_string(light_blob_name, 0x00, self.name)
		
		#lightType, either ambient/point/directional/spot afaik
		linker.add_string(light_blob_name, 0x04, self.type)

		struct.pack_into(">fff", light_data, 0x08, *self.position)

		#hotswap to positive euler angles
		rx, ry, rz = self.rotation
		self.rotation = (
			normalize_deg_360(rx),
			normalize_deg_360(ry),
			normalize_deg_360(rz),
		)

		struct.pack_into(">fff", light_data, 0x14, *self.rotation)
		struct.pack_into(">fff", light_data, 0x20, *self.scale)
		struct.pack_into(">BBBB", light_data, 0x2C, *self.color)

		struct.pack_into(">f", light_data, 0x30, self.spotAngle)
		struct.pack_into(">f", light_data, 0x34, self.angularAttenuation)
		struct.pack_into(">I", light_data, 0x38, self.distanceAttenuationType)
		struct.pack_into(">I", light_data, 0x3C, self.wFlags)
		struct.pack_into(">I", light_data, 0x40, self.wEnableFlagsIf012d60d8) #NOTE: this has always been true in testing

		linker.add_blob(light_blob_name, light_data)
		linker.place_blob_in_section(light_blob_name, "lights")

		return light_blob_name

	@staticmethod
	def from_blender_light(lights, global_matrix): #these are handled as empties to keep data easier to access on the export-side, and just 'simulated' in blender
		dmd_lights = []

		for light in lights.all_objects:
			dmdLight = DmdLight()
			props = light.ttyd_world_light

			dmdLight.name = light.name
			dmdLight.type = props.type #pulled from preset Enum

			#Mimic transform logic from DmdJoint, presumably to keep (-Z)->(Y) consistent
			transform_matrix = light.matrix_local
			if global_matrix is not None:
				transform_matrix = global_matrix @ transform_matrix

			translation, rotation, scale = transform_matrix.decompose()

			dmdLight.position = translation.to_tuple()

			rot = rotation.to_euler()
			dmdLight.rotation = (
				math.degrees(rot.x),
				math.degrees(rot.y),
				math.degrees(rot.z),
			)

			dmdLight.scale = scale.to_tuple()
			dmdLight.color = props.base_color
			dmdLight.spotAngle = props.spotAngle
			dmdLight.angularAttenuation = props.angularAttenuation
			dmdLight.distanceAttenuationType = props.distanceAttenuationType
			dmdLight.wFlags = props.wFlags
			dmdLight.wEnableFlagsIf012d60d8 = props.enableFlags

			dmd_lights.append(dmdLight)

		return dmd_lights

#Material helper classes

@dataclass
class DmdTexCoord:
    translateX: float
    translateY: float
    scaleX: float
    scaleY: float
    rotateZ: float
    warpX: float
    warpY: float

@dataclass
class DmdSampler:
	wrapS: int
	wrapT: int
	unk0a: int
	unk0b: int
	textureName: str
	texCoord: DmdTexCoord

#enum prop conversion
def convertMatSrc(matsrc):
	if matsrc == 'matCol':
		return 0
	elif matsrc == 'vtxCol':
		return 1
	else:
		print(f"matsrc error: {matsrc}")
def convertBlendMode(blendmode):
	if blendmode == 'opaque':
		return 0
	elif blendmode == 'unk':
		return 1
	elif blendmode == 'full':
		return 2
	else:
		print(f"blendmode error: {blendmode}")

class DmdMaterial:
	def __init__(self):
		self.name = ""
		self.color = (0.0, 0.0, 0.0, 0.0)
		self.matSrc = 0
		self.unk009 = 0
		self.blendMode = 0
		self.numTextures = 0 # sampler count
		self.texCoordTransforms = []
		self.blendAlphaModulationR = (0.0, 0.0, 0.0, 0.0)
		self.textureSamplers = []
		self.texCoords = []
		self.tev_mode = 0 #simply hardcoding 'tevConfig.tevMode' as other vars are unk right now
		
	def get_referenced_vertex_attributes(self):
		attributes = [
			VERTEX_ATTRIBUTE_POSITION_ID,
			VERTEX_ATTRIBUTE_NORMAL_ID
		]
		for i in range(len(self.color_layers)):
			attributes.append(VERTEX_ATTRIBUTE_COLOR_ID_PREFIX + str(i))
		for i in range(len(self.samplers)):
			attributes.append(VERTEX_ATTRIBUTE_TEXCOORD_ID_PREFIX + str(i))
		return attributes

	def get_uv_layer_names(self):
		layers = []
		for sampler in self.samplers:
			layers.append(sampler["uv_layer"])
		return layers

	def get_color_layer_names(self):
		return self.color_layers

	def link(self, linker):
		material_blob_name = "materials:" + self.name
		material_data = bytearray(0x114)
		linker.add_string(material_blob_name, 0x000, self.name)
		struct.pack_into(
			">BBBB",
			material_data,
			0x004,
			int(self.color[0]),
			int(self.color[1]),
			int(self.color[2]),
			int(self.color[3])
		)
		struct.pack_into(">B", material_data, 0x008, convertMatSrc(self.matSrc))
		struct.pack_into(">B", material_data, 0x009, self.unk009) #seems always true for '_v' and '_v_x' mats
		struct.pack_into(">B", material_data, 0x00a, convertBlendMode(self.blendMode)) # vertex color blend mode
		struct.pack_into(">B", material_data, 0x00b, self.numTextures) # texture count

		# Serialize samplers
		for i, sampler in enumerate(self.textureSamplers):
			# External sampler data
			sampler_blob_name = "samplers:" + str(linker.get_uid())
			sampler_data = bytearray(0xc)

			texture_blob_name = "textures:" + sampler.textureName
			linker.add_relocation(sampler_blob_name, 0x0, texture_blob_name)

			struct.pack_into(">BB", sampler_data, 0x8, sampler.wrapS, sampler.wrapT)
			struct.pack_into(">BB", sampler_data, 0xa, sampler.unk0a, sampler.unk0b)

			linker.add_blob(sampler_blob_name, sampler_data)
			linker.place_blob_in_section(sampler_blob_name, "sampler_data")

			linker.add_relocation(material_blob_name, 0x00c + i * 4, sampler_blob_name)

			# Material-internal transform data
			struct.pack_into(
				">ff",
				material_data,
				0x02c + i * 0x1c + 0x00,
				sampler.texCoord.translateX,
				sampler.texCoord.translateY
			)
			struct.pack_into(
				">ff",
				material_data,
				0x02c + i * 0x1c + 0x08,
				sampler.texCoord.scaleX,
				sampler.texCoord.scaleY
			)
			struct.pack_into(
				">f",
				material_data,
				0x02c + i * 0x1c + 0x10,
				sampler.texCoord.rotateZ
			)
			struct.pack_into(
				">ff",
				material_data,
				0x02c + i * 0x1c + 0x14,
				sampler.texCoord.warpX,
				sampler.texCoord.warpY
			)

		# Fill in default texture coordinate transforms
		for i in range(len(self.textureSamplers), 8):
			struct.pack_into(">f", material_data, 0x02c + i * 0x1c + 0x08, 1.0) # scale X
			struct.pack_into(">f", material_data, 0x02c + i * 0x1c + 0x0c, 1.0) # scale Y

		# blend alpha modulation in red channel
		struct.pack_into(
			">BBBB",
			material_data, 
			0x10c, 
			int(self.blendAlphaModulationR[0]),
			int(self.blendAlphaModulationR[1]),
			int(self.blendAlphaModulationR[2]),
			int(self.blendAlphaModulationR[3])
		)
		# todo-blender_io_ttyd: Investigate additional fields of TEV configuration structure
		tev_config_blob_name = "tev_configs:" + self.name
		tev_config_data = bytearray(0xc)
		struct.pack_into(">B", tev_config_data, 0x00, self.tev_mode)
		linker.add_blob(tev_config_blob_name, tev_config_data)
		linker.place_blob_in_section(tev_config_blob_name, "tev_configs")

		linker.add_relocation(material_blob_name, 0x110, tev_config_blob_name)

		linker.add_blob(material_blob_name, material_data)
		linker.place_blob_in_section(material_blob_name, "materials")
		return material_blob_name

	@staticmethod
	def from_blender_material(ttyd_material_object):
		material = DmdMaterial()
		materialProps = ttyd_material_object.ttyd_world_material
		material.name = materialProps.name
		material.color = materialProps.color
		material.matSrc = materialProps.matSrc
		material.unk009 = materialProps.unk_009
		material.blendMode = materialProps.blendMode
		material.numTextures = materialProps.numTextures
		material.blendAlphaModulationR = materialProps.blendAlphaModulationR
		for i, sampler in enumerate(materialProps.textureSamplers):
			# Skip invalid / disabled samplers
			if not sampler.texture or not sampler.texture.image:
				continue

			tex = sampler.texture
			img = tex.image
			texture_name = tex.name

			dmd_texcoord = DmdTexCoord(
				translateX=sampler.texCoord.translateX,
				translateY=sampler.texCoord.translateY,
				scaleX=sampler.texCoord.scaleX,
				scaleY=sampler.texCoord.scaleY,
				rotateZ=sampler.texCoord.rotateZ,
				warpX=sampler.texCoord.warpX,
				warpY=sampler.texCoord.warpY,
			)

			dmd_sampler = DmdSampler(
				wrapS=sampler.wrapS,
				wrapT=sampler.wrapT,
				unk0a=sampler.unk_0a,
				unk0b=sampler.unk_0b,
				textureName=img.name,
				texCoord=dmd_texcoord
			)

			material.textureSamplers.append(dmd_sampler)
			material.tev_mode = materialProps.tevConfig.tevMode

		return material

class DmdVcdTable:
	def __init__(self):
		self.attribute_data = defaultdict(list)

	def store_attribute_data(self, attribute, data):
		# Try to find an existing instance of the data
		stored_data = self.attribute_data[attribute]
		for i in range(len(stored_data)):
			if stored_data[i] == data:
				return i

		# Did not find existing instance, add.
		stored_data.append(data)
		out_index = len(stored_data) - 1
		assert(out_index < 65536) # Max encodable index
		return out_index

	def link(self, linker):
		# Figure out quantizations
		quantizations = {}
		for attribute_name in self.attribute_data:
			# Color is unquantized
			if attribute_name.startswith(VERTEX_ATTRIBUTE_COLOR_ID_PREFIX):
				continue
			# Normals are quantized at fixed scale
			if attribute_name == VERTEX_ATTRIBUTE_NORMAL_ID:
				continue
			most_extreme_value = 0.0
			for entry in self.attribute_data[attribute_name]:
				for value in entry:
					most_extreme_value = max(abs(value), most_extreme_value)

			# Due to the fact that the positive maximum of a quantized value is
			# one less than the optimal power of two, we have to add this bias
			# in order to choose the next lower quantization in this case.
			most_extreme_value += 1.0

			if most_extreme_value == 0.0:
				# Corner case which would make math.log throw an exception
				max_magnitude = 0
			else:
				max_magnitude = math.ceil(math.log2(most_extreme_value))
			best_quantization = -(max_magnitude - 15)
			quantizations[attribute_name] = best_quantization

		# Serialize data in correct order
		for attribute_name in VERTEX_ATTRIBUTE_DATA_ORDER:
			if attribute_name not in self.attribute_data:
				continue

			attribute_blob_name = "vertex_attribute_data:" + attribute_name

			unsigned = False
			if attribute_name.startswith(VERTEX_ATTRIBUTE_COLOR_ID_PREFIX):
				element_width = 1
				element_count = 4
				quantization = 0
				unsigned = True
			elif attribute_name == VERTEX_ATTRIBUTE_NORMAL_ID:
				element_width = 1
				element_count = 3
				quantization = 6
			elif attribute_name == VERTEX_ATTRIBUTE_POSITION_ID:
				element_width = 2
				element_count = 3
				quantization = quantizations[attribute_name]
			elif attribute_name.startswith(VERTEX_ATTRIBUTE_TEXCOORD_ID_PREFIX):
				element_width = 2
				element_count = 2
				quantization = quantizations[attribute_name]
			else:
				assert(False)

			# Pack data into buffer
			unquantized_data = self.attribute_data[attribute_name]

			quantized_stride = element_width * element_count
			attribute_buffer_size = 4 + quantized_stride * len(unquantized_data)
			attribute_buffer_size = align_up(attribute_buffer_size, 32)
			attribute_buffer = bytearray(attribute_buffer_size)
			struct.pack_into(">L", attribute_buffer, 0x0, len(unquantized_data))

			for data_index, data in enumerate(unquantized_data):
				data_offset = 4 + quantized_stride * data_index
				for element_index, element in enumerate(data):
					element_offset = data_offset + element_width * element_index

					# Avoid unnecessary handling of unquantized data
					if quantization != 0:
						quantized_element = int(round(element * 2.0**quantization))
						#print("DmdVcdTable: Quantizing {}: {} -> {} (factor {})".format(attribute_name, element, quantized_element, 2.0**quantization))
					else:
						quantized_element = element

					# Check for over/underflow
					if quantization != 0:
						max_quantized_magnitude = 2**(8 * element_width - 1)
						if (quantized_element >= max_quantized_magnitude
							or quantized_element < -max_quantized_magnitude):
							print("DmdVcdTable: Unable to quantize {} value {}".format(attribute_name, element))

					# Get right format string
					if element_width == 1:
						format_string = ">B" if unsigned else ">b"
					elif element_width == 2:
						assert(not unsigned)
						format_string = ">h"
					else:
						assert(False)

					# Write the actual data
					struct.pack_into(
						format_string,
						attribute_buffer,
						element_offset,
						quantized_element
					)
			linker.add_blob(attribute_blob_name, attribute_buffer)
			linker.place_blob_in_section(attribute_blob_name, "vertex_attribute_data")

		# Finally create VCD table
		vcd_table_blob_name = "vcd_table"
		vcd_table_data = bytearray(0x68)

		# todo-blender_io_ttyd: Clean up the variable attribute count tracking here.
		color_count = 0
		tc_count = 0
		for attribute_name in self.attribute_data:
			attribute_blob_name = "vertex_attribute_data:" + attribute_name

			if attribute_name == VERTEX_ATTRIBUTE_POSITION_ID:
				struct.pack_into(">l", vcd_table_data, 0x44, quantizations[attribute_name])
				linker.add_relocation(vcd_table_blob_name, 0x00, attribute_blob_name)
			elif attribute_name == VERTEX_ATTRIBUTE_NORMAL_ID:
				linker.add_relocation(vcd_table_blob_name, 0x04, attribute_blob_name)
			elif attribute_name.startswith(VERTEX_ATTRIBUTE_COLOR_ID_PREFIX):
				color_index = int(attribute_name[len(VERTEX_ATTRIBUTE_COLOR_ID_PREFIX):])
				linker.add_relocation(
					vcd_table_blob_name,
					0x0c + color_index * 4,
					attribute_blob_name
				)
				color_count += 1
			elif attribute_name.startswith(VERTEX_ATTRIBUTE_TEXCOORD_ID_PREFIX):
				tc_index = int(attribute_name[len(VERTEX_ATTRIBUTE_TEXCOORD_ID_PREFIX):])
				tc_offset = tc_index * 4
				linker.add_relocation(
					vcd_table_blob_name,
					0x18 + tc_offset,
					attribute_blob_name
				)
				struct.pack_into(
					">l",
					vcd_table_data,
					0x48 + tc_offset,
					quantizations[attribute_name]
				)
				tc_count += 1

		# Store color and texture coordinate counts
		struct.pack_into(">L", vcd_table_data, 0x08, color_count)
		struct.pack_into(">L", vcd_table_data, 0x14, tc_count)

		linker.add_blob(vcd_table_blob_name, vcd_table_data)
		linker.place_blob_in_section(vcd_table_blob_name, "vcd_table")
		return vcd_table_blob_name

def _parse_indices(s: str):
    if not s:
        return []
    return [int(i) for i in s.replace(" ", "").split(",")]

class DmdModel:
	"""DMD File Model with one material consisting of triangle strips"""

	def __init__(self):
		self.material_name = ""
		self.attributes = []
		self.polygons = []

	def get_bbox(self):
		# todo-blender_io_ttyd: Use util.get_bbox() instead
		first_vertex = True
		for p in self.polygons:
			opcode, verts = p
			for v in verts:
				position = v[VERTEX_ATTRIBUTE_POSITION_ID]
				if first_vertex:
					first_vertex = False
					bbox_min = list(position)
					bbox_max = list(position)
					continue
				for i in range(3):
					bbox_min[i] = min(bbox_min[i], position[i])
					bbox_max[i] = max(bbox_max[i], position[i])
		if first_vertex:
			return None
		return (tuple(bbox_min), tuple(bbox_max))

	def link(self, linker, vcd_table):
		# Write vertex data into VCD table and get final attribute indices
		out_polygons = []
		for p in self.polygons:
			opcode, verts = p
			out_vertices = []
			for v in verts:
				out_attribute_indices = []
				for attribute_name in VERTEX_ATTRIBUTE_INDEX_ORDER:
					if attribute_name not in v:
						continue
					index = vcd_table.store_attribute_data(attribute_name, v[attribute_name])
					out_attribute_indices.append(index)
				out_vertices.append(out_attribute_indices)
			out_polygons.append((opcode, out_vertices))

		mesh_blob_name = "meshs:" + str(linker.get_uid())

		# Align mesh size upwards to 32 bytes to maintain alignment
		# with Polygons (containing display lists)
		mesh_data_size = align_up(0x10 + 8 * len(out_polygons), 32)
		mesh_data = bytearray(mesh_data_size)
		struct.pack_into(">B", mesh_data, 0x0, 1) # Unknown
		struct.pack_into(">B", mesh_data, 0x3, 1) # bPolygonsAreDisplayLists, always 1 in v1.02
		struct.pack_into(">L", mesh_data, 0x4, len(out_polygons)) # Polygon count

		# Build element mask
		element_mask = 0
		for i, attribute in enumerate(VERTEX_ATTRIBUTE_INDEX_ORDER):
			if attribute in self.attributes:
				element_mask |= (1 << i)
		struct.pack_into(">L", mesh_data, 0x8, element_mask)

		linker.add_relocation(mesh_blob_name, 0xc, "vcd_table")

		# Calculate stride
		vertex_stride = 0
		for attribute in self.attributes:
			if attribute in VERTEX_ATTRIBUTE_INDEX_ORDER:
				vertex_stride += 2

		for polygon_index, (opcode, polygon) in enumerate(out_polygons):
			polygon_blob_name = mesh_blob_name + ":polygons:" + str(polygon_index)

			# polygon is the list of vertices (each vertex is a list of attribute indices)
			vertex_count = len(polygon)
			if opcode == 0x90 and (vertex_count % 3) != 0:
				raise RuntimeError(f"GX_TRIANGLES requires vertex_count % 3 == 0 (got {vertex_count})")

			# Calculate aligned size
			polygon_data_size = align_up(3 + vertex_count * vertex_stride, 32)
			polygon_data = bytearray(polygon_data_size)

			struct.pack_into(">B", polygon_data, 0x0, opcode)        # draw opcode (e.g. 0x90 or 0x98)
			struct.pack_into(">H", polygon_data, 0x1, vertex_count)   # vertex count

			for vertex_index, vertex in enumerate(polygon):
				vertex_offset = 0x3 + vertex_index * vertex_stride
				for attribute_index, attribute in enumerate(vertex):
					attribute_offset = vertex_offset + attribute_index * 2
					struct.pack_into(">H", polygon_data, attribute_offset, attribute)

			linker.add_blob(polygon_blob_name, polygon_data)
			linker.place_blob_in_section(polygon_blob_name, "meshs")

			linker.add_relocation(mesh_blob_name, 0x10 + 8 * polygon_index, polygon_blob_name)
			struct.pack_into(">L", mesh_data, 0x14 + 8 * polygon_index, polygon_data_size)

		linker.add_blob(mesh_blob_name, mesh_data)
		linker.place_blob_in_section(mesh_blob_name, "meshs")
		return mesh_blob_name

	#deprecated, use DmdModel.list_from_local_mesh_ir instead
	@staticmethod
	def list_from_blender_mesh(blender_object, blender_mesh, materials):
		material_data = {}
		for blender_polygon in blender_mesh.polygons:
			# Get appropriate material if this mesh has any and we're not doing collision
			dmd_material = None
			materialEmpty = blender_object.ttyd_world_mesh.emptyMaterial
			for m in materials:
				if m.name == materialEmpty.name:
					dmd_material = m
					material_name = dmd_material.name
					blender_uv_layers = ["UVMap"]
					if "UVMap.001" in blender_mesh.uv_layers:
						blender_uv_layers.append("UVMap.001")
						print("\n\n\n\nDmdModel: Mesh '{}' uses multiple UV layers.\n\n\n\n".format(blender_mesh.name))
					blender_color_layers = ["Col"]
					attributes_to_store = [
						VERTEX_ATTRIBUTE_POSITION_ID,
						VERTEX_ATTRIBUTE_NORMAL_ID,
						VERTEX_ATTRIBUTE_TEXCOORD_ID_PREFIX + "0",
						VERTEX_ATTRIBUTE_COLOR_ID_PREFIX + "0",
					]
					if len(blender_uv_layers) > 1:
						attributes_to_store.append(
							VERTEX_ATTRIBUTE_TEXCOORD_ID_PREFIX + "1"
						)
					break

			if dmd_material == None:
				print("[WARNING] Material created by mesh: This shouldn't happen. Attempting to continue.")
				dmd_material = DmdMaterial.from_blender_material(materialEmpty)
				materials.append(dmd_material)
				material_name = dmd_material.name

				attributes_to_store = [
					VERTEX_ATTRIBUTE_POSITION_ID,
					VERTEX_ATTRIBUTE_NORMAL_ID
				]
				blender_uv_layers = []
				blender_color_layers = []
			# Setup per-material polygon data
			if material_name not in material_data:
				material_data[material_name] = {
					"polygons": [],
					"attributes": attributes_to_store 
				}

			# Tessellate polygons into triangles
			loop_indices = [i for i in blender_polygon.loop_indices]
			polygon_tessellated_loop_indices = []
			if len(loop_indices) == 3:
				polygon_tessellated_loop_indices.append(list(reversed(loop_indices)))
			elif len(loop_indices) > 3:
				# todo-blender_io_ttyd: Tessellate polygons into strips instead
				# of outputting individual triangles
				vertex_positions = []
				for loop_index in loop_indices:
					loop = blender_mesh.loops[loop_index]
					vertex = blender_mesh.vertices[loop.vertex_index]
					vertex_positions.append(vertex.co)
				tessellated_triangles = mathutils.geometry.tessellate_polygon([vertex_positions])
				for tri in tessellated_triangles:
					# todo-blender_io_ttyd: Should blender_polygon.loop_indices
					# not be simply loop_indices here?
					tri_loop_indices = [blender_polygon.loop_indices[i] for i in tri]
					polygon_tessellated_loop_indices.append(tri_loop_indices)

			# Extract attributes
			# We store the raw attribute data; the data is deduplicated when
			# linking in the VCD table

			# Evaluate face normal only once and share index if not smooth shaded
			if (VERTEX_ATTRIBUTE_NORMAL_ID in attributes_to_store
				and not blender_polygon.use_smooth):
				face_normal = tuple(blender_polygon.normal)

			# todo-blender_io_ttyd: Think about removing attribute names from
			# vertices here since they're already stored in the model's field
			for triangle_loop_indices in polygon_tessellated_loop_indices:
				vertices = []
				for loop_index in triangle_loop_indices:
					vertex_attributes = {}
					loop = blender_mesh.loops[loop_index]
					vertex = blender_mesh.vertices[loop.vertex_index]
					assert(VERTEX_ATTRIBUTE_POSITION_ID in attributes_to_store)
					# todo-blender_io_ttyd: Think about flattening this loop
					# into a series of if-statements with loops for
					# colors/texcoords
					for attribute_name in attributes_to_store:
						if attribute_name == VERTEX_ATTRIBUTE_POSITION_ID:
							vertex_attributes[attribute_name] = tuple(vertex.co)
						elif attribute_name == VERTEX_ATTRIBUTE_NORMAL_ID:
							if blender_polygon.use_smooth:
								normal_data = tuple(vertex.normal)
							else:
								normal_data = face_normal

							vertex_attributes[attribute_name] = normal_data
						elif attribute_name.startswith(VERTEX_ATTRIBUTE_TEXCOORD_ID_PREFIX):
							tc_index = int(attribute_name[len(VERTEX_ATTRIBUTE_TEXCOORD_ID_PREFIX):])
							assert(tc_index < VERTEX_ATTRIBUTE_TEXCOORD_MAX_COUNT)

							if tc_index < len(blender_uv_layers):
								tc_layer_name = blender_uv_layers[tc_index]
								tc_layer = blender_mesh.uv_layers[tc_layer_name]
								u, v = tc_layer.data[loop_index].uv
								tc_data = (u, 1.0 - v)
							else:
								# todo-blender_io_ttyd: Figure out if this is a
								# fatal error; probably should be.
								assert(False)
								tc_data = (0.0, 0.0)

							vertex_attributes[attribute_name] = tc_data
						elif attribute_name.startswith(VERTEX_ATTRIBUTE_COLOR_ID_PREFIX):
							color_index = int(attribute_name[len(VERTEX_ATTRIBUTE_COLOR_ID_PREFIX):])
							assert(color_index < VERTEX_ATTRIBUTE_COLOR_MAX_COUNT)

							if color_index < len(blender_color_layers):
								color_layer_name = blender_color_layers[color_index]
								color_layer = blender_mesh.vertex_colors[color_layer_name]

								# No SRGB conversion necessary!
								color_data = tuple(color_layer.data[loop_index].color)

								# todo-blender_io_ttyd: Think about whether
								# this is the best way to handle color
								# quantization.

								# Convert to 0-255 here instead of VCD table as
								# the quantizations there are different in that
								# they multiply by 2**n; for colors however,
								# this does not hold, as 1.0 maps to 255 and
								# not to 256.
								color_data = tuple(int(x * 255) for x in color_data)
							else:
								# todo-blender_io_ttyd: Figure out if this is a
								# probably should be.
								assert(False)
								color_data = (255, 0, 255, 255)

							vertex_attributes[attribute_name] = color_data
					vertices.append(vertex_attributes)
				material_data[material_name]["polygons"].append(vertices)

		# Build final models
		models = []
		for material_name in material_data:
			model = DmdModel()
			model.material_name = material_name
			model.attributes = material_data[material_name]["attributes"]
			#print("MODEL material:", model.material_name, "attrs:", model.attributes)
			model.polygons = material_data[material_name]["polygons"]
			models.append(model)
		return models

	@staticmethod
	def list_from_local_mesh_ir(blender_object, materials, is_hit=False):
		"""
		Build DmdModel list strictly from LocalMeshIR.
		No Blender mesh access. No triangulation.
		Simplifies hit mesh generation to only positions.
		"""

		def _q3(v, eps=1e-6):
			return (round(float(v[0]) / eps) * eps,
					round(float(v[1]) / eps) * eps,
					round(float(v[2]) / eps) * eps)

		props = blender_object.ttyd_world_mesh

		if not props.local_vertices or not props.local_primitives:
			raise RuntimeError(
				f"[TTYD Export] Mesh '{blender_object.name}' has no LocalMeshIR"
			)

		# ------------------------------------------------------------
		# Material resolution (still Blender-side by design)
		# ------------------------------------------------------------
		materialEmpty = props.emptyMaterial
		dmd_material = None

		for m in materials:
			if m.name == materialEmpty.name:
				dmd_material = m
				break

		if dmd_material is None:
			print(f"[WARNING] Material missing for '{blender_object.name}', creating fallback")
			dmd_material = DmdMaterial.from_blender_material(materialEmpty)
			materials.append(dmd_material)

		model = DmdModel()
		model.material_name = dmd_material.name

		# ------------------------------------------------------------
		# Attribute layout (derived from IR presence)
		# ------------------------------------------------------------
		model.attributes = [VERTEX_ATTRIBUTE_POSITION_ID]

		has_nrm = bool(getattr(props, "has_nrm", False))
		has_uv0 = bool(getattr(props, "has_uv0", False))
		has_uv1 = bool(getattr(props, "has_uv1", False))
		has_col = bool(getattr(props, "has_col", False))

		if is_hit:
			# Hit meshes only have position
			has_nrm = False
			has_uv0 = False
			has_uv1 = False
			has_col = False

		if has_nrm:
			model.attributes.append(VERTEX_ATTRIBUTE_NORMAL_ID)
		if has_uv0:
			model.attributes.append(VERTEX_ATTRIBUTE_TEXCOORD_ID_PREFIX + "0")
		if has_uv1:
			model.attributes.append(VERTEX_ATTRIBUTE_TEXCOORD_ID_PREFIX + "1")
		if has_col:
			model.attributes.append(VERTEX_ATTRIBUTE_COLOR_ID_PREFIX + "0")

		# ------------------------------------------------------------
		# Build polygons from IR
		# ------------------------------------------------------------
		model.polygons = []

		for prim in props.local_primitives:
			polygon_vertices = []

			indices = _parse_indices(prim.indices)

			for idx in indices:
				lv = props.local_vertices[idx]
				vtx = {}

				# --- Position ---
				p = (lv.pos[0], lv.pos[1], lv.pos[2])
				if is_hit:
					p = _q3(p)

				vtx[VERTEX_ATTRIBUTE_POSITION_ID] = p

				def _norm3(n):
					l = math.sqrt(n[0]*n[0] + n[1]*n[1] + n[2]*n[2])
					if l == 0.0:
						return (0.0, 0.0, 1.0)
					return (n[0]/l, n[1]/l, n[2]/l)

				# --- Normal ---
				if has_nrm:
					vtx[VERTEX_ATTRIBUTE_NORMAL_ID] = _norm3(lv.nrm)

				# --- UVs ---
				if has_uv0:
					vtx[f"{VERTEX_ATTRIBUTE_TEXCOORD_ID_PREFIX}0"] = (
						lv.uv0[0],
						lv.uv0[1],
					)

				if has_uv1:
					vtx[f"{VERTEX_ATTRIBUTE_TEXCOORD_ID_PREFIX}1"] = (
						lv.uv1[0],
						lv.uv1[1],
					)

				def _f_to_u8(x: float) -> int:
					return int(round(max(0.0, min(1.0, float(x))) * 255.0))

				# --- Color (0–255) ---
				if has_col:
					vtx[f"{VERTEX_ATTRIBUTE_COLOR_ID_PREFIX}0"] = (
						_f_to_u8(lv.col[0]),
						_f_to_u8(lv.col[1]),
						_f_to_u8(lv.col[2]),
						_f_to_u8(lv.col[3]),  # alpha must NOT be gamma corrected
					)

				polygon_vertices.append(vtx)

			model.polygons.append((int(prim.opcode), polygon_vertices))

		return [model]

class DmdJoint:
	"""DMD File Joint"""

	def __init__(self):
		self.name = ""

		self.children = []
		self.models = []

		self.translation = (0.0, 0.0, 0.0)
		self.rotation = (0.0, 0.0, 0.0)
		self.scale = (1.0, 1.0, 1.0)
		self.anim_delta = (0.0, 0.0, 0.0)

		self.hit_attribute_flags = 0

	def link(self, linker, vcd_table, parent = None, next = None, prev = None):
		blob_name = "joints:{}".format(self.name)
		joint_data = bytearray(0x60 + len(self.models) * 0x8)

		linker.add_string(blob_name, 0x00, self.name)
		linker.add_string(blob_name, 0x04, "mesh" if len(self.models) > 0 else "null")

		if parent:
			linker.add_relocation(blob_name, 0x08, "joints:{}".format(parent.name))
		if len(self.children) > 0:
			linker.add_relocation(blob_name, 0x0c, "joints:{}".format(self.children[0].name))
		if next:
			linker.add_relocation(blob_name, 0x10, "joints:{}".format(next.name))
		if prev:
			linker.add_relocation(blob_name, 0x14, "joints:{}".format(prev.name))
		
		struct.pack_into(
			">fff", joint_data, 0x18,
			self.scale[0], self.scale[1], self.scale[2]
		)
		struct.pack_into(
			">fff", joint_data, 0x24,
			self.rotation[0], self.rotation[1], self.rotation[2]
		)
		struct.pack_into(
			">fff", joint_data, 0x30,
			self.translation[0], self.translation[1], self.translation[2]
		)

		# Compute local-space bounding box
		bbox = None
		for model in self.models:
			model_bbox = model.get_bbox()
			if bbox == None:
				bbox = (list(model_bbox[0]), list(model_bbox[1]))
				continue
			for i in range(3):
				bbox[0][i] = min(bbox[0][i], model_bbox[0][i])
				bbox[1][i] = max(bbox[1][i], model_bbox[1][i])

		# Default to non-zero bounding box imitating original exporter behavior
		if bbox == None:
			bbox = ((-0.1, -0.1, -0.1), (0.1, 0.1, 0.1))
		else:
			bbox = (tuple(bbox[0]), tuple(bbox[1]))

		struct.pack_into(
			">ffffff", joint_data, 0x3c,
			bbox[0][0], bbox[0][1], bbox[0][2],
			bbox[1][0], bbox[1][1], bbox[1][2]
		)
		struct.pack_into(">L", joint_data, 0x54, 0) # unknown

		# todo-blender_io_ttyd: Further investigate drawmode
		if parent != None: # Root node does not have drawmode
			drawmode_blob_name = "drawmodes:{}".format(self.name)
			linker.add_relocation(blob_name, 0x58, drawmode_blob_name)
			
			drawmode_data = bytearray(0x14)
			lightmaskval = getattr(self, "light_mask", 0)
			drawmodeval = getattr(self, "draw_mode", 0)
			cull_enum = getattr(self, "cull_mode", None)
			cull_value = CULL_ENUM_TO_VALUE.get(cull_enum, 1)  # default BACK
			wFlagsval = getattr(self, "wFlags", 0)

			struct.pack_into(">B", drawmode_data, 0x0, drawmodeval)
			struct.pack_into(">B", drawmode_data, 0x1, cull_value)
			struct.pack_into(">B", drawmode_data, 0x2, wFlagsval)
			# padded byte
			struct.pack_into(">L", drawmode_data, 0x4, lightmaskval)
			struct.pack_into(">L", drawmode_data, 0x8, int(self.hit_attribute_flags))

			linker.add_blob(drawmode_blob_name, drawmode_data)
			linker.place_blob_in_section(drawmode_blob_name, "drawmodes")

		struct.pack_into(">L", joint_data, 0x5c, len(self.models))

		for i in range(len(self.models)):
			model = self.models[i]
			mesh_blob_name = model.link(linker, vcd_table)

			# Only link material if there is a material, hit data may not have one
			if model.material_name != "":
				#print(model.material_name) #i added this print to check, and the materials are being properly carried to this point.
				material_blob_name = "materials:{}".format(model.material_name)
				linker.add_relocation(blob_name, 0x60 + i * 8, material_blob_name)

			linker.add_relocation(blob_name, 0x64 + i * 8, mesh_blob_name)

		linker.add_blob(blob_name, joint_data)
		linker.place_blob_in_section(blob_name, "joints")

		for i in range(len(self.children)):
			if i > 0:
				prev_child = self.children[i - 1]
			else:
				prev_child = None
			if i < len(self.children) - 1:
				next_child = self.children[i + 1]
			else:
				next_child = None
			self.children[i].link(linker, vcd_table, self, next_child, prev_child)
		return blob_name

	def map_local_to_blender_vertices(blender_mesh, local_vertices, eps=1e-6):
		mapping = {}
		for li, lv in enumerate(local_vertices):
			lv_vec = Vector((lv.x, lv.y, lv.z))
			for bv in blender_mesh.vertices:
				if (bv.co - lv_vec).length <= eps:
					mapping[li] = bv.index
					break
			else:
				raise RuntimeError(
					f"Local vertex {li} not found in Blender mesh"
				)
		return mapping

	@staticmethod
	def from_blender_object(blender_object, materials, global_matrix = None, is_hit=False):
		
		def _require_local_ir(obj):
			props = obj.ttyd_world_mesh
			if not props.local_vertices or not props.local_primitives:
				raise RuntimeError(
					f"[TTYD Export] Mesh '{obj.name}' has no LocalMeshIR. "
					f"Run 'Build Local Mesh IR' before exporting."
				)

		# --- helpers (minimal / safe) ---
		def _is_fragment(o):
			try:
				return (o.type == "MESH" and hasattr(o, "ttyd_world_mesh") and o.ttyd_world_mesh.meshFragment)
			except Exception:
				return False

		def _is_dmd_parent(o):
			try:
				return (o.type == "EMPTY" and hasattr(o, "ttyd_world_empty") and o.ttyd_world_empty.dmdObject)
			except Exception:
				return False

		joint = DmdJoint()
		joint.name = blender_object.name

		# Build children joints, but SKIP fragment meshes (they get merged into parent)
		joint.children = []
		for c in blender_object.children:
			if _is_fragment(c):
				continue
			joint.children.append(DmdJoint.from_blender_object(c, materials, None, is_hit))

		# Transform
		bpy.context.view_layer.update()

		M = blender_object.matrix_basis.copy()

		# Apply axis conversion consistently, but ONLY if your global_matrix is pure rotation/scale.
		# (If it includes translation, you're introducing systematic offsets.)
		if global_matrix is not None:
			M = global_matrix @ M

		t, r, s = M.decompose()

		joint.translation = (float(t.x), float(t.y), float(t.z))

		e = r.to_euler('XYZ')  # keep this consistent with import
		joint.rotation = (math.degrees(e.x), math.degrees(e.y), math.degrees(e.z))

		joint.scale = (float(s.x), float(s.y), float(s.z))

		#region: unk_data_mand flag prep
		joint.hit_attribute_flags = _hit_type_to_flag(blender_object)
		if joint.hit_attribute_flags == 0:
			joint.hit_attribute_flags = blender_object.ttyd_attributes.hit_val
			if joint.hit_attribute_flags != 0:
				print(f"Hit ATTR not in ENUM; overwritten to {joint.hit_attribute_flags} for {joint.name} (mesh)")

		joint.light_mask = 0
		joint.draw_mode = 0
		joint.cull_mode = None
		joint.wFlags = 0
		try:
			joint.draw_mode = blender_object.ttyd_attributes.draw_mode
		except Exception:
			joint.draw_mode = 0
			print(f"{joint.name} had meshAttributes Error. Defaulting to DrawMode 0")

		try:
			joint.cull_mode = blender_object.ttyd_attributes.cull_mode
		except Exception:
			joint.cull_mode = None
			print(f"{joint.name} had meshAttributes Error. Defaulting to no culling")

		try:
			joint.wFlags = blender_object.ttyd_attributes.wFlags
		except Exception:
			joint.wFlags = 0
			print(f"{joint.name} had meshAttributes Error. Defaulting to wFlags 0")

		try:
			joint.light_mask = blender_object.ttyd_attributes.light_mask
		except Exception:
			joint.light_mask = 0
			print(f"{joint.name} had meshAttributes Error. Defaulting to light mask 0")

				
		# --- models ---
		joint.models = []

		# Normal case: mesh object exports its own models
		if blender_object.type == "MESH":
			_require_local_ir(blender_object)

			joint.models = DmdModel.list_from_local_mesh_ir(blender_object, materials, is_hit)

		# Multi-mesh DMD parent: pull models from fragment meshes and append
		elif _is_dmd_parent(blender_object):
			# Prefer explicit membership list if present, else fallback to scanning children
			fragments = []

			try:
				members = blender_object.ttyd_world_empty.meshMembers
				# if you used a ref.obj PointerProperty:
				for ref in members:
					frag = getattr(ref, "obj", None)
					if frag is not None and _is_fragment(frag):
						fragments.append(frag)
			except Exception:
				pass

			if not fragments:
				print(f"[TTYD Export] WARNING: '{blender_object.name}' is marked dmdObject but has 0 meshMembers")

			for frag in fragments:
				joint.models.extend(DmdModel.list_from_local_mesh_ir(frag, materials, is_hit))
				joint.hit_attribute_flags |= _hit_type_to_flag(frag)
				if joint.hit_attribute_flags == 0:
					joint.hit_attribute_flags = blender_object.ttyd_attributes.hit_val
					if joint.hit_attribute_flags != 0:
						print(f"Hit ATTR not in ENUM; overwritten to {joint.hit_attribute_flags} for {joint.name} (frag)")

		# Parse hit attributes (unchanged)
		hit_attribute_property_name = "hit_attributes"
		if hit_attribute_property_name in blender_object:
			joint.hit_attributes = [n.strip() for n in blender_object[hit_attribute_property_name].split(",")]

		return joint

def value_keyframe_convert_scalar_to_degrees(value_keyframe):
    # (value, tan_in, tan_out, is_step)
    v, tin, tout, step = value_keyframe
    return (math.degrees(v), math.degrees(tin), math.degrees(tout), step)

class ExportError(RuntimeError):
    pass

def get_action_fcurves(source_object, action):
    # Blender < 5.0
    if hasattr(action, "fcurves"):
        return action.fcurves

    ad = getattr(source_object, "animation_data", None)
    if ad is None:
        return ()

    slot = getattr(ad, "action_slot", None)
    if slot is None:
        return ()

    for layer in action.layers:
        for strip in layer.strips:
            if hasattr(strip, "channelbag"):
                cb = strip.channelbag(slot, ensure=False)
                if cb is not None:
                    return cb.fcurves

    return ()

class DmdAnimation:
	def __init__(self):
		self.name = ""
		self.index = 0
		self.length = 0.0
		self.joint_transform_tracks = []
		self.material_uv_tracks = []
		self.material_blend_tracks = []
		self.light_transform_tracks = []
		self.light_parameter_tracks = []

	def link(self, linker):
		anim_blob_name = f"animations:{self.name}:{self.index}"
		anim_data = bytearray(0x28)

		linker.add_string(anim_blob_name, 0x00, self.name)

		# Length in frames (float)
		struct.pack_into(">f", anim_data, 0x08, self.length)

		# Helper to pack a keyframe tuple
		def pack_keyframe_into(buffer, offset, data):
			# Value, tangent in, tangent out, unk_0c, is_step
			# unk_0c is zero in all animations in all TTYD maps, so we don't
			# bother storing
			struct.pack_into(
				">fffLL", buffer, offset,
				data[0], data[1], data[2], 0, 1 if data[3] else 0
			)

		# Tuples of (track list, offset to track table pointer in animation,
		# header size, components)
		track_type_descriptions = {
			"joint_transform": (
				self.joint_transform_tracks,
				0x0c, # offset to track table ptr in animation
				[
					("translation", 3),
					("rotation", 3),
					("scale", 3),
					("anim_delta1", 3),
					(None, 3), # unk
					("anim_delta2", 3),
					(None, 3), # unk
				],
				0x58 # header size
			),
			"material_uv": (
				self.material_uv_tracks,
				0x10,
				[
					("translation", 2),
					("scale", 2),
					("rotation", 1),
				],
				0x10
			),
			"material_blend": (
				self.material_blend_tracks,
				0x14,
				[
					("color", 4),
				],
				0x4
			),
			"light_transform": (
				self.light_transform_tracks,
				0x18,
				[
					("translation", 3),
					("rotation", 3),
					("scale", 3),
				],
				0x4
			),
			"light_parameters": (
				self.light_parameter_tracks,
				0x1c,
				[
					("color", 3),
					("spot_angle", 1),
					("angular_attenuation", 1),
				],
				0x4
			),
		}

		all_track_type_blob_names = []
		for track_type_name, track_type_description in track_type_descriptions.items():
			track_type_blob_names = []

			track_list = track_type_description[0]
			animation_track_type_table_offset = track_type_description[1]
			track_components = track_type_description[2]
			track_header_size = track_type_description[3]

			if len(track_list) < 1:
				continue

			track_total_component_count = sum([x[1] for x in track_components])
			# All keyframes are time as float header followed by some amount of
			# component keyframes
			track_keyframe_size = 0x4 + track_total_component_count * 0x14

			for track in track_list:
				track_blob_name = "animation_data:tracks:{}".format(linker.get_uid())
				track_data = bytearray(track_header_size + 0x4 + len(track["keyframes"]) * track_keyframe_size)

				if track_type_name == "joint_transform":
					linker.add_string(track_blob_name, 0x00, track["joint_name"])

					# Translation/rotation/scale/delta origin
					struct.pack_into(
						">fff", track_data, 0x04,
						track["translation_origin"][0],
						track["translation_origin"][1],
						track["translation_origin"][2]
					)
					struct.pack_into(
						">fff", track_data, 0x10,
						track["rotation_origin"][0],
						track["rotation_origin"][1],
						track["rotation_origin"][2]
					)
					struct.pack_into(
						">fff", track_data, 0x1c,
						track["scale_origin"][0],
						track["scale_origin"][1],
						track["scale_origin"][2]
					)
					
					

					# Four unused sets, the first and third are sometimes set to
					# 0.408818 on the Y-axis. Presumably these are Maya-specific
					# additional transforms. We do not use this value here since it
					# makes no actual difference and is not consistently used in the
					# original exporter.

					#NOTE: I found where piston got these from :3 these are presumably the 'pivot' values from Maya joints.
					# they essentially act as an additional offset to the joint transforms, and some anims use them as they're "real origin"
					# to separate 'animation position' from 'model position' (apparently likely that (x1, y1) are rotation pivot while (x2, y2) are scale pivot?
					# in testing x1 and x2 have been equal values, while y1 and y2 have been zeroed out.)
					struct.pack_into(
						">fff", track_data, 0x28,
						track["position_delta"][0],
						track["position_delta"][1],
						track["position_delta"][2]
					)
					struct.pack_into(">fff", track_data, 0x34, 0.0, 0.0, 0.0)
					struct.pack_into(
						">fff", track_data, 0x40,
						track["position_delta"][0],
						track["position_delta"][1],
						track["position_delta"][2]
					)
					struct.pack_into(">fff", track_data, 0x4c, 0.0, 0.0, 0.0)
				elif track_type_name == "material_uv":
					linker.add_string(track_blob_name, 0x0, track["material_name"])
					struct.pack_into(">L", track_data, 0x4, track["sampler_index"])

					# Scale-independent translation for alignment, not animatable
					struct.pack_into(">ff", track_data, 0x8, track["align"][0], track["align"][1])
				elif track_type_name == "material_blend":
					linker.add_string(track_blob_name, 0x0, track["material_name"])
				elif track_type_name == "light_transform":
					linker.add_string(track_blob_name, 0x0, track["light_name"])
				elif track_type_name == "light_parameters":
					linker.add_string(track_blob_name, 0x0, track["light_name"])

				# Export the actual keyframes
				struct.pack_into(">L", track_data, track_header_size + 0x0, len(track["keyframes"]))

				for keyframe_index, keyframe in enumerate(track["keyframes"]):
					keyframe_offset = track_header_size + 0x4 + keyframe_index * track_keyframe_size

					struct.pack_into(">f", track_data, keyframe_offset, keyframe["time"])

					component_offset = keyframe_offset + 0x4
					for value_index, value_info in enumerate(track_components):
						value_key = value_info[0]
						value_component_count = value_info[1]
						for component_index in range(value_component_count):
							if value_key != None:
								if value_component_count == 1:
									component_source_data = keyframe[value_key]
								else:
									component_source_data = keyframe[value_key][component_index]
							else:
								component_source_data = (0.0, 0.0, 0.0, 0)
							pack_keyframe_into(
								track_data,
								component_offset,
								component_source_data
							)
							component_offset += 0x14
					assert(component_offset == keyframe_offset + track_keyframe_size)

				# We do not place the blob into a section here to emulate
				# original exporter behavior. The original exporter serializes
				# all data referenced by an animation into one contiguous chunk
				# in a section that follows the serialized animations, with the
				# track table located immediately *before* the tracks it
				# contains. To do this, the track table must be placed in this
				# shared section *after* the tracks themselves have been
				# serialized.
				linker.add_blob(track_blob_name, track_data)
				track_type_blob_names.append(track_blob_name)

			# Serialize track table
			track_table_blob_name = "animation_data:tables:{}".format(linker.get_uid())
			track_table_data = bytearray(0x4 + len(track_type_blob_names) * 4)
			struct.pack_into(">L", track_table_data, 0x0, len(track_type_blob_names))
			for track_index, track_blob_name in enumerate(track_type_blob_names):
				linker.add_relocation(track_table_blob_name, 0x4 + track_index * 4, track_blob_name)
			linker.add_relocation(
				anim_blob_name,
				animation_track_type_table_offset,
				track_table_blob_name
			)
			linker.add_blob(track_table_blob_name, track_table_data)
			linker.place_blob_in_section(track_table_blob_name, "animation_data")

			# Place tracks after their respective table emulating original exporter behavior.
			for track_blob_name in track_type_blob_names:
				linker.place_blob_in_section(track_blob_name, "animation_data")
		
		linker.add_blob(anim_blob_name, anim_data)
		linker.place_blob_in_section(anim_blob_name, "animations")
		return anim_blob_name

	@staticmethod
	def _make_keyframes(source_object, action, keyframe_layout, blender_fcurve_mapping, required_times=None):
		keyframe_times = set()
		fcurves = get_action_fcurves(source_object, action)

		for fcurve in fcurves:
			src = (fcurve.data_path, fcurve.array_index)
			if src not in blender_fcurve_mapping:
				continue
			for kp in fcurve.keyframe_points:
				keyframe_times.add(float(kp.co[0]))

		# Force required times (e.g., 0 and length) to avoid 0-keyframe tracks
		if required_times:
			for t in required_times:
				if t is None:
					continue
				keyframe_times.add(float(t))

		# Absolute minimum safety: ensure at least one keyframe
		if not keyframe_times:
			keyframe_times = {0.0}

		sorted_times = sorted(keyframe_times)
		keyframes = []

		def _safe_slope(y1, x1, y0, x0):
			dx = (x1 - x0)
			return 0.0 if dx == 0 else (y1 - y0) / dx

		for time in sorted_times:
			kf = {"time": time}

			for name, count in keyframe_layout.items():
				kf[name] = None if count == 1 else [None] * count

			for fcurve in fcurves:
				src = (fcurve.data_path, fcurve.array_index)
				if src not in blender_fcurve_mapping:
					continue

				found = None
				for kp in fcurve.keyframe_points:
					if float(kp.co[0]) == time:
						found = kp
						break

				if found is not None:
					value = float(found.co[1])
					tan_in = _safe_slope(found.co[1], found.co[0], found.handle_left[1], found.handle_left[0])
					tan_out = _safe_slope(found.handle_right[1], found.handle_right[0], found.co[1], found.co[0])
					is_step = False
				else:
					delta = 1.0
					value = float(fcurve.evaluate(time))
					prev_value = float(fcurve.evaluate(time - delta))
					next_value = float(fcurve.evaluate(time + delta))
					tan_in = value - prev_value
					tan_out = next_value - value
					is_step = False

				comp = (value, tan_in, tan_out, is_step)
				target_key, target_index = blender_fcurve_mapping[src]
				if target_index is None:
					kf[target_key] = comp
				else:
					kf[target_key][target_index] = comp

			keyframes.append(kf)

		reverse = {v: k for k, v in blender_fcurve_mapping.items()}

		for kf in keyframes:
			for value_key, count in keyframe_layout.items():
				for ci in range(count):
					if count == 1:
						if kf[value_key] is not None:
							continue
						output_path = (value_key, None)
					else:
						if kf[value_key][ci] is not None:
							continue
						output_path = (value_key, ci)

					if output_path not in reverse:
						raise ExportError(f"Missing reverse mapping for {output_path}")

					blender_path, blender_index = reverse[output_path]

					# If we can't resolve, fall back to 0 (or 1 for scale)
					fallback = DmdAnimation._default_missing_value(value_key)
					live_value = DmdAnimation._try_read_live_value(
						source_object=source_object,
						blender_path=blender_path,
						blender_index=blender_index,
						default_value=fallback,
					)

					const = (float(live_value), 0.0, 0.0, False)
					if count == 1:
						kf[value_key] = const
					else:
						kf[value_key][ci] = const

		return keyframes
	
	@staticmethod
	def _try_read_live_value(source_object, blender_path, blender_index, default_value):
		"""
		Read a live scalar for missing components.
		Works for:
		- regular RNA paths via path_resolve()
		- ShaderNodeTree paths like nodes["Mapping"].translation where path_resolve fails in Blender 4.x
		"""
		# 1) Try normal RNA path resolution first
		try:
			prop = source_object.path_resolve(blender_path)
			if blender_index is None:
				return float(prop)
			return float(prop[blender_index])
		except Exception:
			pass

		# 2) Special-case ShaderNodeTree "nodes[...].translation/rotation/scale"
		# Accept both single and double quotes around node name.
		if hasattr(source_object, "nodes"):
			m = re.match(r"^nodes\[(?:\"|')(.+?)(?:\"|')\]\.(translation|rotation|scale)$", blender_path)
			if m:
				node_name, attr = m.group(1), m.group(2)
				node = source_object.nodes.get(node_name)
				if node is None:
					return default_value

				# Prefer real RNA props if they exist (older Blender)
				if hasattr(node, attr):
					vec = getattr(node, attr)
					if blender_index is None:
						return float(vec)
					return float(vec[blender_index])

				# Blender 4.x: Mapping values live on input sockets
				# Mapping node inputs: [0]=Vector, [1]=Location, [2]=Rotation, [3]=Scale
				socket_index = {"translation": 1, "rotation": 2, "scale": 3}.get(attr)
				if socket_index is None:
					return default_value

				try:
					dv = node.inputs[socket_index].default_value
					if blender_index is None:
						return float(dv)
					return float(dv[blender_index])
				except Exception:
					return default_value

		return default_value

	@staticmethod
	def _default_missing_value(value_key):
		# Sensible defaults if we truly cannot read live values
		if value_key == "scale":
			return 1.0
		return 0.0

	@staticmethod
	def from_dmd_animation_collection(emptyAnim, idx):
		anim = DmdAnimation()
		animProps = emptyAnim.ttyd_world_animation

		anim.name = animProps.name
		anim.index = idx
		anim.length = animProps.length

		if animProps.joint:
			DmdAnimation._build_joint_tracks(anim, animProps)

		if animProps.uv:
			DmdAnimation._build_uv_tracks(anim, animProps)

		if animProps.alpha:
			DmdAnimation._build_alpha_tracks(anim, animProps)

		if animProps.lightT:
			DmdAnimation._build_lightT_tracks(anim, animProps)

		if animProps.lightP:
			DmdAnimation._build_lightP_tracks(anim, animProps)

		return anim
	
	@staticmethod
	def _any_keyframes_exist(source_object, action, blender_fcurve_mapping):
		for fcurve in get_action_fcurves(source_object, action):
			src = (fcurve.data_path, fcurve.array_index)
			if src in blender_fcurve_mapping:
				return True
		return False

	@staticmethod
	def build_transform_track_from_action(obj, origin_loc, origin_rot_rad, origin_scl, anim_origin, anim_rotation, anim_scale, anim_delta, action, length=None):
		blender_fcurve_mapping = {
			("location", 0): ("translation", 0),
			("location", 1): ("translation", 1),
			("location", 2): ("translation", 2),
			("rotation_euler", 0): ("rotation", 0),
			("rotation_euler", 1): ("rotation", 1),
			("rotation_euler", 2): ("rotation", 2),
			("scale", 0): ("scale", 0),
			("scale", 1): ("scale", 1),
			("scale", 2): ("scale", 2),
		}

		anim_loc = (origin_loc[0] - anim_delta[0], 
			  		origin_loc[1] - anim_delta[1], 
					origin_loc[2] - anim_delta[2])
		anim_rot = (math.degrees(origin_rot_rad[0]),
					math.degrees(origin_rot_rad[1]),
					math.degrees(origin_rot_rad[2]))
		anim_scl = origin_scl

		# Force time 0, and optionally end time = length to stabilize playback/init
		required_times = [0.0]
		if length is not None:
			required_times.append(float(length))

		keyframes = DmdAnimation._make_keyframes(
			source_object=obj,
			action=action,
			keyframe_layout={"translation": 3, "rotation": 3, "scale": 3},
			blender_fcurve_mapping=blender_fcurve_mapping,
			required_times=required_times,
		)

		# Convert Blender absolute -> engine-friendly relative:
		# - translation: delta from origin (tangents unchanged)
		# - rotation: delta from origin (in radians), then convert to degrees
		# - scale: multiplicative factor relative to origin (values & tangents scaled)
		for kf in keyframes:
			source_translation = obj.location
			# translation
			for i in range(3):
				v, tin, tout, step = kf["translation"][i]
				kf["translation"][i] = (v - anim_origin[i] - source_translation[i], tin, tout, step)

			# rotation (radians -> degrees)
			for i in range(3):
				v, tin, tout, step = kf["rotation"][i]
				kf["rotation"][i] = value_keyframe_convert_scalar_to_degrees((v, tin, tout, step))

			# scale
			for i in range(3):
				v, tin, tout, step = kf["scale"][i]
				kf["scale"][i] = (v, tin, tout, step)

			kf["anim_delta1"] = [(anim_delta[i], 0.0, 0.0, False) for i in range(3)]
			kf["anim_delta2"] = [(anim_delta[i], 0.0, 0.0, False) for i in range(3)]

		track = {
			"joint_name": obj.name,
			"translation_origin": (anim_origin[0], anim_origin[1], anim_origin[2]),
			"rotation_origin": anim_rot,  # degrees (matches keyframes now)
			"scale_origin": anim_scl,
			"position_delta": (anim_delta[0], anim_delta[1], anim_delta[2]),
			"keyframes": keyframes,
		}

		return track

	@staticmethod
	def build_uv_track_from_action(materialName, skew, material, action, sampler_index, mapping_node_name, length=None):
		translation_path = f'nodes["{mapping_node_name}"].inputs[1].default_value'
		rotation_path    = f'nodes["{mapping_node_name}"].inputs[2].default_value'
		scale_path       = f'nodes["{mapping_node_name}"].inputs[3].default_value'

		blender_fcurve_mapping = {
			(translation_path, 0): ("translation", 0),
			(translation_path, 1): ("translation", 1),
			(scale_path, 0): ("scale", 0),
			(scale_path, 1): ("scale", 1),
			(rotation_path, 2): ("rotation", None),
		}

		required_times = [0.0]
		if length is not None:
			required_times.append(float(length))

		node_tree = material.node_tree

		track = {
			"material_name": materialName,
			"sampler_index": sampler_index,
			"align": skew,
			"keyframes": DmdAnimation._make_keyframes(
				source_object=node_tree,
				action=action,
				keyframe_layout={"translation": 2, "scale": 2, "rotation": 1},
				blender_fcurve_mapping=blender_fcurve_mapping,
				required_times=required_times,
			),
		}

		for kf in track["keyframes"]:
			vk = value_keyframe_convert_scalar_to_degrees(kf["rotation"])
			kf["rotation"] = (-vk[0], -vk[1], -vk[2], vk[3])

		return track

	@staticmethod
	def build_alpha_track_from_action(materialName, emptyMat, action, length):
		required_times = [0.0]
		if length is not None:
			required_times.append(float(length))

		rgba_path = f'ttyd_world_material.blendAlphaModulationR'

		blender_fcurve_mapping = {
			(rgba_path, 0): ("color", 0),
			(rgba_path, 1): ("color", 1),
			(rgba_path, 2): ("color", 2),
			(rgba_path, 3): ("color", 3),
		}

		track = {
			"material_name": materialName,
			"keyframes": DmdAnimation._make_keyframes(
				source_object=emptyMat.ttyd_world_material,
				action=action,
				keyframe_layout={"color": 4},
				blender_fcurve_mapping=blender_fcurve_mapping,
				required_times=required_times
			),	
		}

		return track

	@staticmethod
	def build_light_transform_track_from_action(light, action, length=None):
		blender_fcurve_mapping = {
			("location", 0): ("translation", 0),
			("location", 1): ("translation", 1),
			("location", 2): ("translation", 2),
			("rotation_euler", 0): ("rotation", 0),
			("rotation_euler", 1): ("rotation", 1),
			("rotation_euler", 2): ("rotation", 2),
			("scale", 0): ("scale", 0),
			("scale", 1): ("scale", 1),
			("scale", 2): ("scale", 2),
		}

		required_times = [0.0]
		if length is not None:
			required_times.append(float(length))

		keyframes = DmdAnimation._make_keyframes(
			source_object=light,
			action=action,
			keyframe_layout={"translation": 3, "rotation": 3, "scale": 3},
			blender_fcurve_mapping=blender_fcurve_mapping,
			required_times=required_times,
		)

		# Don't need to subtract origin; light-anims are absolute
		for kf in keyframes:
			# translation
			for i in range(3):
				v, tin, tout, step = kf["translation"][i]
				kf["translation"][i] = (v, tin, tout, step)

			# rotation (radians -> delta radians -> degrees)
			for i in range(3):
				v, tin, tout, step = kf["rotation"][i]
				kf["rotation"][i] = value_keyframe_convert_scalar_to_degrees((v, tin, tout, step))

			# scale (absolute -> factor)
			for i in range(3):
				v, tin, tout, step = kf["scale"][i]

				kf["scale"][i] = (v, tin, tout, step)

		track = {
			"light_name": light.name,
			"keyframes": keyframes,
		}

		return track

	@staticmethod
	def build_light_parameter_track_from_action(light, action, length=None):
		color_path = f'ttyd_world_light.multiplier'
		spotAngle_path = f'ttyd_world_light.spotAngle'
		angularAttenuation_path = f'ttyd_world_light.angularAttenuation'

		required_times = [0.0]
		if length is not None:
			required_times.append(float(length))

		blender_fcurve_mapping = {
			(color_path, 0): ("color", 0),
			(color_path, 1): ("color", 1),
			(color_path, 2): ("color", 2),
			(spotAngle_path, 0): ("spot_angle", None),
			(angularAttenuation_path, 0): ("angular_attenuation", None)
		}

		track = {
			"light_name": light.name,
			"keyframes": DmdAnimation._make_keyframes(
				source_object=light.ttyd_world_light,
				action=action,
				keyframe_layout={"color": 3, "spot_angle": 1, "angular_attenuation": 1},
				blender_fcurve_mapping=blender_fcurve_mapping,
				required_times=required_times
			),
		}

		return track

	@staticmethod
	def _build_joint_tracks(anim, animProps):
		for t in animProps.joint_table.tracks:
			if not t.joint or not t.action:
				continue
			origin_loc = (float(t.joint.location.x), float(t.joint.location.y), float(t.joint.location.z))
			origin_rot_rad = (float(t.joint.rotation_euler.x), float(t.joint.rotation_euler.y), float(t.joint.rotation_euler.z))
			origin_scl = (float(t.joint.scale.x), float(t.joint.scale.y), float(t.joint.scale.z))

			tr = DmdAnimation.build_transform_track_from_action(t.joint, origin_loc, origin_rot_rad, origin_scl, t.anim_origin, t.anim_rotation, t.anim_scale, t.anim_delta, t.action, length=anim.length)
			if tr is not None:
				anim.joint_transform_tracks.append(tr)
				
	@staticmethod
	def _build_uv_tracks(anim, animProps):
		for t in animProps.uv_table.tracks:

			mat_obj = None
			matName = t.name
			matSkew = t.skew

			if not t.action:
				raise ExportError(f"UV track '{t.name}' has no action assigned")

			mat_obj = t.mat or t.mat_v or t.mat_v_x
			if not mat_obj:
				export_mat = bpy.data.materials.get(f"[{t.name}]-dummyAnimHandler")

			if mat_obj:
				emptyProps = mat_obj.ttyd_world_material
				# authoritative export material (first ref)
				export_mat = emptyProps.materialRefs[0].material

			if not emptyProps.materialRefs:
				raise ExportError(f"UV track '{t.name}' has no preview material refs")

			# get mapping_node_name + sampler_index
			sampler_index = t.samplerIndex
			nt = export_mat.node_tree
			if nt is None:
				raise ExportError(f"Material '{export_mat.name}' has no node_tree")

			if sampler_index == 0:
				mapping_node = nt.nodes.get("Mapping")
				if mapping_node is None:
					raise ExportError(f"Material '{export_mat.name}' is missing a node named 'Mapping'")

				mapping_node_name = mapping_node.name

			if sampler_index == 1:
				mapping_node = nt.nodes.get("Mapping.001")
				if mapping_node is None:
					raise ExportError(f"Material '{export_mat.name}' is missing a node named 'Mapping'")

				mapping_node_name = mapping_node.name

			tr = DmdAnimation.build_uv_track_from_action(
				materialName=matName,
				skew=matSkew,
				material=export_mat,
				action=t.action,
				sampler_index=sampler_index,
				mapping_node_name=mapping_node_name,
				length=anim.length,
			)
			if tr is not None:
				anim.material_uv_tracks.append(tr)
	
	@staticmethod
	def _build_alpha_tracks(anim, animProps):
		for t in animProps.alpha_table.tracks:
			if not t.action:
				raise ExportError(f"UV track '{t.name}' has no action assigned")
			
			matName = t.name
			mat_obj = t.mat or t.mat_v or t.mat_v_x
			if not mat_obj:
				raise ExportError(f"UV track '{t.name}' has no material assigned")
			
			tr = DmdAnimation.build_alpha_track_from_action(
				materialName=matName,
				emptyMat=mat_obj,
				action=t.action,
				length=anim.length
			)
			if tr is not None:
				anim.material_blend_tracks.append(tr)

	@staticmethod
	def _build_lightT_tracks(anim, animProps):
		for t in animProps.lightT_table.tracks:
			if not t.light or not t.action:
				continue
			
			tr = DmdAnimation.build_light_transform_track_from_action(t.light, t.action, length=anim.length)
			if tr is not None:
				anim.light_transform_tracks.append(tr)

	@staticmethod
	def _build_lightP_tracks(anim, animProps):
		for t in animProps.lightP_table.tracks:
			if not t.light or not t.action:
				continue
			
			tr = DmdAnimation.build_light_parameter_track_from_action(t.light, t.action, length=anim.length)
			if tr is not None:
				anim.light_parameter_tracks.append(tr)

class DmdFile:
	def __init__(self):
		self.root_joint = None

		self.map_joint = None
		self.hit_joint = None

		self.lights = []
		self.materials = []
		self.textures = []
		self.animations = []

	@staticmethod
	def from_blender_scene(scene, settings, world_name):
		file = DmdFile()
		file.root_joint = DmdJoint()
		file.root_joint.name = "world_root"

		global_matrix = mathutils.Matrix.Identity(4)
		if "axis_conversion_matrix" in settings:
			global_matrix = settings["axis_conversion_matrix"]

		file.materials = []
		file.textures = []

		file.collapse_hit = settings["collapse_hit"]

		file.texture_collection = settings["texture_root"]
		for emptyTex in file.texture_collection.objects:
			texture = DmdTexture.from_blender_image(emptyTex)
			file.textures.append(texture)

		file.material_collection = settings["material_root"]
		for emptyMat in file.material_collection.objects:
			dmd_material = DmdMaterial.from_blender_material(emptyMat)
			file.materials.append(dmd_material)

		hit_root = settings["hit_root"].objects.get("A")
		map_root = settings["map_root"].objects.get("S")

		file.map_joint = DmdJoint.from_blender_object(
			map_root,
			file.materials,
			global_matrix,
			False
		)
		file.hit_joint = DmdJoint.from_blender_object(
			hit_root,
			file.materials,
			global_matrix,
			True if file.collapse_hit else False
		)
		file.lights = DmdLight.from_blender_light(
			settings["light_root"],
			global_matrix
		)

		if world_name:
			file.hit_joint.name = f"{world_name}_A"
			file.map_joint.name = f"{world_name}_S"
		else:
			file.hit_joint.name = "A"
			file.map_joint.name = "S"

		file.root_joint.children = [
			file.hit_joint,
			file.map_joint
		]


		file.animation_collection = settings["anim_root"]
		for idx, animBundle in enumerate(file.animation_collection.objects):
			animationGroup = DmdAnimation.from_dmd_animation_collection(animBundle, idx)
			if animationGroup is not None:
				file.animations.append(animationGroup)

		return file

	def serialize(self, world_name):

		# Helper function to write a table containing references to other elements
		def link_reference_table(linker, blob_name, section_name, references):
			table_data = bytearray(0x4 + len(references) * 0x4)
			struct.pack_into(">L", table_data, 0x0, len(references)) # Element count
			for i, reference in enumerate(references):
				linker.add_relocation(blob_name, 0x4 + i * 0x4, reference)
			linker.add_blob(blob_name, table_data)
			linker.place_blob_in_section(blob_name, section_name)

		linker = DmdLinker()

		vcd_table = DmdVcdTable()
		root_joint_blob_name = f"joints:{self.root_joint.name}"
		
		# Information table
		information_table_blob_name = "information"
		information_table_data = bytearray(0x14)

		linker.add_string(information_table_blob_name, 0x00, "ver1.02") # Version string
		linker.add_relocation(information_table_blob_name, 0x04, root_joint_blob_name) # World root
		
		if world_name:
			linker.add_string(information_table_blob_name, 0x08, f"{world_name}_S")
			linker.add_string(information_table_blob_name, 0x0c, f"{world_name}_A")
		else:
			linker.add_string(information_table_blob_name, 0x08, f"S")
			linker.add_string(information_table_blob_name, 0x0c, f"A")

		date_text = datetime.datetime.utcnow().strftime("%y/%m/%d %H:%M:%S")
		linker.add_string(information_table_blob_name, 0x10, date_text)

		linker.add_blob(information_table_blob_name, information_table_data)
		linker.place_blob_in_section(information_table_blob_name, "information")

		# Animation table
		animation_blob_names = [a.link(linker) for a in self.animations]
		link_reference_table(linker, "animation_table", "animation_table", animation_blob_names)

		# Curve table (legacy, always empty)
		link_reference_table(linker, "curve_table", "curve_table", [])

		# Fog table
		# todo-blender_io_ttyd: Expose fog settings to user
		fog_table_blob_name = "fog_table"
		fog_table_data = bytearray(0x14)
		struct.pack_into(">L", fog_table_data, 0x00, 0) # Fog enabled
		struct.pack_into(">L", fog_table_data, 0x04, 0) # Fog mode
		struct.pack_into(">f", fog_table_data, 0x08, 0) # Fog start
		struct.pack_into(">f", fog_table_data, 0x0c, 1000) # Fog end
		struct.pack_into(">L", fog_table_data, 0x10, 0x000000FF) # Fog color
		linker.add_blob(fog_table_blob_name, fog_table_data)
		linker.place_blob_in_section(fog_table_blob_name, "fog_table")

		# Texture table
		texture_table_blob_name = "texture_table"
		texture_table_data = bytearray(0x4 + len(self.textures) * 0x4)
		struct.pack_into(">L", texture_table_data, 0x0, len(self.textures)) # Texture count
		for i, texture in enumerate(self.textures):
			linker.add_string(texture_table_blob_name, 0x4 + i * 0x4, texture.name)
		linker.add_blob(texture_table_blob_name, texture_table_data)
		linker.place_blob_in_section(texture_table_blob_name, "texture_table")

		# Material name table
		material_name_table_blob_name = "material_name_table"
		material_name_table_data = bytearray(4 + len(self.materials) * 8)
		struct.pack_into(">L", material_name_table_data, 0x0, len(self.materials))
		for i, material in enumerate(self.materials):
			linker.add_string(
				material_name_table_blob_name,
				0x4 + i * 8,
				material.name
			)
			material_blob_name = "materials:" + material.name
			linker.add_relocation(
				material_name_table_blob_name,
				0x8 + i * 8,
				material_blob_name
			)
		linker.add_blob(material_name_table_blob_name, material_name_table_data)
		linker.place_blob_in_section(material_name_table_blob_name, "material_name_table")

		# Light table #NOTE: peech :3
		light_blob_names = [a.link(linker) for a in self.lights]
		link_reference_table(linker, "light_table", "light_table", light_blob_names)

		self.root_joint.link(linker, vcd_table)
		vcd_table.link(linker)

		# Serialize referenced materials
		for material in self.materials:
			material.link(linker)

		# Serialize referenced textures
		for texture in self.textures:
			texture.link(linker)

		# Place sections and finalize linked data.
		linker.place_section("information")
		linker.place_section("texture_data")
		linker.place_section("sampler_data")
		linker.place_section("vertex_attribute_data", 32) # Align by 32 for vertex cache efficiency
		linker.place_section("materials")
		linker.place_section("lights")
		linker.place_section("meshs", 32) # Align by 32 since this contains display lists
		linker.place_section("joints")
		linker.place_section("vcd_table")
		linker.place_section("material_name_table")
		linker.place_section("light_table")
		linker.place_section("fog_table")
		linker.place_section("texture_table")
		linker.place_section("curve_table")
		linker.place_section("animation_table")
		linker.place_section("animations")
		linker.place_section("animation_data")
		linker.place_section("drawmodes")
		linker.place_section("tev_configs")
		linker.place_section("strings")

		# Generate final data
		assert(linker.resolve_relocations())
		linked_data = linker.serialize()
		#print(linker.dump_map())

		# Pad out to multiple of 32 bytes
		linked_data += (align_up(len(linked_data), 32) - len(linked_data)) * b"\x00"

		# Build table infos
		# These appear alphabetically sorted, presumably this was done
		# dynamically by the original exporter. This data is not created using
		# the offset table, but instead hardcoded offsets into the file
		table_order = [
			"animation_table",
			"curve_table",
			"fog_table",
			"information",
			"light_table",
			"material_name_table",
			"texture_table",
			"vcd_table"
		]

		table_info_data = bytearray(len(table_order) * 8)
		table_name_data = bytearray()
		for i, table_name in enumerate(table_order):
			struct.pack_into(
				">L",
				table_info_data,
				0x0 + i * 8,
				linker.get_blob_address(table_name)
			)
			struct.pack_into(">L", table_info_data, 0x4 + i * 8, len(table_name_data)) # Name offset
			encoded_table_name = table_name.encode("shift_jis") + b"\x00"
			table_name_data += encoded_table_name

		# Build offset table
		offsets = []
		for source_name, source_offset, target_name in linker.resolved_relocations:
			offset = linker.get_blob_address(source_name) + source_offset
			offsets.append(offset)

		# Offsets appears sorted in ascending order in table
		offsets.sort()

		# Build final data
		offset_table_data = bytearray(len(offsets) * 4)
		for i, offset in enumerate(offsets):
			struct.pack_into(">L", offset_table_data, i * 4, offset)

		# Build file header
		header_data = bytearray(0x20)
		struct.pack_into(">L", header_data, 0x4, len(linked_data))
		struct.pack_into(">L", header_data, 0x8, len(offsets))
		struct.pack_into(">L", header_data, 0xc, len(table_order))

		# Assemble final file
		# This order is important as only the location of the offset table is
		# encoded in the header and the game assumes the table infos follow.
		final_data = bytearray()
		final_data += header_data
		final_data += linked_data
		final_data += offset_table_data
		final_data += table_info_data
		final_data += table_name_data

		# Add final file size
		struct.pack_into(">L", final_data, 0x0, len(final_data))

		return final_data