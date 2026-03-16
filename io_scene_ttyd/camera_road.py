# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright 2019 Linus S. (aka PistonMiner)

import math
import datetime

import bpy
import mathutils

from .util import *

def _parse_indices(s: str):
    if not s:
        return []
    return [int(i) for i in s.replace(" ", "").split(",")]

def polygon_rotations(poly):
    n = len(poly)
    rots = []

    # forward rotations
    for i in range(n):
        rots.append(poly[i:] + poly[:i])

    # reversed rotations
    rev = list(reversed(poly))
    for i in range(n):
        rots.append(rev[i:] + rev[:i])

    return rots

def orient_next_polygon(poly, shared_edge):
    u, v = shared_edge
    for cand in polygon_rotations(poly):
        if len(cand) >= 3 and cand[1] == v and cand[2] == u:
            return cand
    return poly

def orient_prev_polygon(poly, shared_edge):
    u, v = shared_edge
    for cand in polygon_rotations(poly):
        if cand[-2] == u and cand[-1] == v:
            return cand
    return poly
		
def shared_edge(poly1, poly2):
    s2 = set(poly2)
    n1 = len(poly1)
    for i in range(n1):
        u = poly1[i]
        v = poly1[(i + 1) % n1]
        if u in s2 and v in s2:
            return (u, v)
    return None

class CameraRoadMarker:
	def __init__(self):
		self.name = ""
		self.bbox = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
		self.polygons = []
		self.vertex_indices = []
		self.vertex_positions = []

	def link(self, linker):
		marker_blob_name = "markers:" + str(linker.get_uid())
		marker_data = bytearray(0x68)

		struct.pack_into(">64s", marker_data, 0x00, self.name.encode("shift_jis"))

		# Bounding box
		bbox = self.bbox
		assert(bbox != None)
		struct.pack_into(
			">ffffff",
			marker_data,
			0x40,
			bbox[0][0],
			bbox[0][1],
			bbox[0][2],
			bbox[1][0],
			bbox[1][1],
			bbox[1][2]
		)

		vertex_position_base_index = linker.get_section_blob_count("vertex_positions")
		vertex_position_blob_name_prefix = "vertex_positions:{}:".format(linker.get_uid())
		for i, vertex_position in enumerate(self.vertex_positions):
			vertex_position_blob_name = vertex_position_blob_name_prefix + str(i)
			vertex_position_data = bytearray(0xc)
			struct.pack_into(
				">fff",
				vertex_position_data,
				0x0,
				vertex_position[0],
				vertex_position[1],
				vertex_position[2]
			)
			linker.add_blob(vertex_position_blob_name, vertex_position_data)
			linker.place_blob_in_section(vertex_position_blob_name, "vertex_positions")

		struct.pack_into(">L", marker_data, 0x58, vertex_position_base_index)
		struct.pack_into(">L", marker_data, 0x5c, len(self.vertex_positions))

		vertex_index_base_index = linker.get_section_blob_count("vertex_indices")
		vertex_index_blob_name_prefix = "indices:{}:".format(linker.get_uid())
		for i, vertex_index in enumerate(self.vertex_indices):
			vertex_index_blob_name = vertex_index_blob_name_prefix + str(i)
			vertex_index_data = bytearray(0x4)

			struct.pack_into(">L", vertex_index_data, 0x0, vertex_index)

			linker.add_blob(vertex_index_blob_name, vertex_index_data)
			linker.place_blob_in_section(vertex_index_blob_name, "vertex_indices")

		polygon_base_index = linker.get_section_blob_count("polygons")
		polygon_blob_name_prefix = "polygons:{}:".format(linker.get_uid())
		for i, polygon in enumerate(self.polygons):
			polygon_blob_name = polygon_blob_name_prefix + str(i)
			polygon_data = bytearray(0x8)

			polygon_start_index = vertex_index_base_index + polygon[0]
			struct.pack_into(">L", polygon_data, 0x0, polygon_start_index)
			struct.pack_into(">L", polygon_data, 0x4, polygon[1])

			linker.add_blob(polygon_blob_name, polygon_data)
			linker.place_blob_in_section(polygon_blob_name, "polygons")

		struct.pack_into(">L", marker_data, 0x60, polygon_base_index)
		struct.pack_into(">L", marker_data, 0x64, len(self.polygons))

		linker.add_blob(marker_blob_name, marker_data)
		linker.place_blob_in_section(marker_blob_name, "markers")

		return marker_blob_name

	@staticmethod
	def from_blender_object(blender_object, global_matrix = None):
		if blender_object.type != 'MESH':
			return None

		props = blender_object.ttyd_world_mesh

		marker = CameraRoadMarker()

		marker_vertex_positions = []
		marker_vertex_indices = []
		marker_polygons = []
		
		marker.bbox = (props.bbox_min, props.bbox_max)

		vertex_map = {}

		for lv in props.local_vertices:
			pos = mathutils.Vector(lv.pos)

			# quantize to avoid float precision duplicates
			key = (
				round(pos.x, 6),
				round(pos.y, 6),
				round(pos.z, 6)
			)

			if key not in vertex_map:
				vertex_map[key] = len(marker_vertex_positions)
				marker_vertex_positions.append(key)

		prev_poly = None

		for prim in props.local_primitives:
			raw_indices = _parse_indices(prim.indices)

			indices = []
			for idx in raw_indices:
				lv = props.local_vertices[idx]
				pos = mathutils.Vector(lv.pos)
				key = (
					round(pos.x, 6),
					round(pos.y, 6),
					round(pos.z, 6),
				)
				indices.append(vertex_map[key])

			if prev_poly is not None:
				edge = shared_edge(prev_poly, indices)
				if edge is not None:
					prev_poly = orient_prev_polygon(prev_poly, edge)
					indices = orient_next_polygon(indices, edge)

					# rewrite previously emitted polygon if needed
					prev_start, prev_count = marker_polygons[-1]
					marker_vertex_indices[prev_start:prev_start + prev_count] = prev_poly

			prev_poly = indices

			polygon_start = len(marker_vertex_indices)

			for idx in indices:
				marker_vertex_indices.append(idx)

			polygon_size = len(indices)
			marker_polygons.append((polygon_start, polygon_size))

		marker.name = blender_object.name
		marker.vertex_positions = marker_vertex_positions
		marker.vertex_indices = marker_vertex_indices
		marker.polygons = marker_polygons

		return marker

class CameraRoadCurve:
	def __init__(self):
		self.name = ""
		self.should_lock_y = 0
		self.lock_y_value = 0.0
		self.disabled = 0
		self.clamp_start_segment = 0
		self.clamp_end_segment = 0
		self.clamp_distance_left = 0.0
		self.clamp_distance_right = 0.0
		self.clamp_start_segment_progress = 0.0
		self.clamp_end_segment_progress = 0.0
		self.target_distance = 0.0
		self.elevation_degrees = 0.0
		self.pitch_degrees = 0.0
		self.shift_x_rate = 0.0
		self.unk_80 = 0.0
		self.should_clamp = 0
		self.bbox = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
		self.data_count = 0
		self.geometry_count = 0
		self.markers = []
		self.points = []
		self.params = []

	def link(self, linker):
		curve_blob_name = "curves.{}".format(self.name)
		curve_data = bytearray(0xb8)
		struct.pack_into(">32s", curve_data, 0x00, self.name.encode("shift_jis"))
		struct.pack_into(">L", curve_data, 0x20, self.should_lock_y) # Lock Y?
		struct.pack_into(">f", curve_data, 0x24, self.lock_y_value) # Value to lock Y at
		struct.pack_into(">L", curve_data, 0x28, self.disabled) # Disabled?
		# 20 bytes of padding here

		# Maximum distance the camera is allowed to travel left and right of the curve
		struct.pack_into(">L", curve_data, 0x40, self.clamp_start_segment)
		struct.pack_into(">L", curve_data, 0x44, self.clamp_end_segment)
		struct.pack_into(">f", curve_data, 0x48, self.clamp_distance_left)
		struct.pack_into(">f", curve_data, 0x4c, self.clamp_distance_right)
		# Distance from camera to target
		struct.pack_into(">f", curve_data, 0x50, self.clamp_start_segment_progress)
		struct.pack_into(">f", curve_data, 0x54, self.clamp_end_segment_progress)
		struct.pack_into(">f", curve_data, 0x58, self.target_distance)

		# 8 bytes unk

		# Camera elevation/pitch (degrees)
		struct.pack_into(">f", curve_data, 0x64, self.elevation_degrees)
		# 8 bytes unk
		struct.pack_into(">f", curve_data, 0x70, self.pitch_degrees)

		# Shift X rate (how far/fast the camera slides ahead of the player
		# when traveling on the X-axis)
		struct.pack_into(">f", curve_data, 0x7c, self.shift_x_rate)

		# Enable clamping?
		struct.pack_into(">L", curve_data, 0x84, self.should_clamp)

		# Curve data
		assert len(self.points) == len(self.params)
		assert len(self.points) > 0
		curve_data_name_prefix = "curve_data:{}:".format(linker.get_uid())
		curve_data_base_index = linker.get_section_blob_count("curve_data")
		curve_data_count = 0
		points = self.points
		params = self.params

		# Bounding box (excludes extended points on purpose)
		bbox = self.bbox
		struct.pack_into(
			">ffffff",
			curve_data,
			0x88,
			bbox[0][0], bbox[0][1], bbox[0][2], bbox[1][0], bbox[1][1], bbox[1][2]
		)
		
		# Positions, then tangents
		for point in points:
			curve_data_blob_name = curve_data_name_prefix + str(curve_data_count)
			curve_data_data = bytearray(0xc)

			x, y, z = point

			struct.pack_into(">f", curve_data_data, 0x0, x)
			struct.pack_into(">f", curve_data_data, 0x4, y)
			struct.pack_into(">f", curve_data_data, 0x8, z)

			linker.add_blob(curve_data_blob_name, curve_data_data)
			linker.place_blob_in_section(curve_data_blob_name, "curve_data")

			curve_data_count += 1

		for param in self.params:
			curve_data_blob_name = curve_data_name_prefix + str(curve_data_count)
			curve_data_data = bytearray(0xc)

			x, y, z = param

			struct.pack_into(">f", curve_data_data, 0x0, x)
			struct.pack_into(">f", curve_data_data, 0x4, y)
			struct.pack_into(">f", curve_data_data, 0x8, z)

			linker.add_blob(curve_data_blob_name, curve_data_data)
			linker.place_blob_in_section(curve_data_blob_name, "curve_data")

			curve_data_count += 1

		struct.pack_into(">L", curve_data, 0xa0, curve_data_base_index)
		struct.pack_into(">L", curve_data, 0xa4, curve_data_count)
		
		# Markers
		marker_base_index = linker.get_section_blob_count("markers")
		for marker in self.markers:
			marker.link(linker)
		struct.pack_into(">L", curve_data, 0xa8, marker_base_index)
		struct.pack_into(">L", curve_data, 0xac, len(self.markers))

		linker.add_blob(curve_blob_name, curve_data)
		linker.place_blob_in_section(curve_blob_name, "curves")

		return curve_blob_name

	@staticmethod
	def from_blender_curve(blender_object, global_matrix = None):
		if blender_object.type != 'CURVE':
			return None

		curve = CameraRoadCurve()
		attr = blender_object.ttyd_world_curve

		entries = attr.localCurveIR
		node_count = len(entries)

		curve.points = []
		curve.params = []

		for entry in entries:
			pos = mathutils.Vector(entry.pos)
			param = mathutils.Vector(entry.param)

			curve.points.append((pos.x, pos.y, pos.z))
			curve.params.append((param.x, param.y, param.z))

		curve.name = blender_object.name

		curve.should_lock_y = attr.wbLockY
		curve.lock_y_value = attr.wLockedYVal
		curve.disabled = attr.bDisabled
		curve.clamp_start_segment = attr.clampStartSegment
		curve.clamp_end_segment = attr.clampEndSegment
		curve.clamp_distance_left = attr.clampMaxDistanceLeft
		curve.clamp_distance_right = attr.clampMaxDistanceRight
		curve.clamp_start_segment_progress = attr.clampStartSegmentProgress
		curve.clamp_end_segment_progress = attr.clampEndSegmentProgress
		curve.target_distance = attr.wCameraToTargetDistance
		curve.elevation_degrees = attr.camElevationDegrees
		curve.pitch_degrees = attr.camPitchDegrees
		curve.shift_x_rate = attr.shiftXRate
		curve.unk_80 = attr.unk_80
		curve.should_clamp = attr.wbEnableClamping
		curve.bbox = (attr.bbox_min, attr.bbox_max)
		curve.data_count = node_count * 2
		curve.geometry_count = attr.geometry_count

		curve.markers = []
		marker = CameraRoadMarker.from_blender_object(attr.Marker, global_matrix)
		if marker is None:
			raise Exception(f"No marker found for Curve: {curve.name}")
		curve.markers.append(marker)

		return curve

class CameraRoadFile:
	def __init__(self):
		self.curves = []
		pass

	@staticmethod
	def from_blender_scene(blender_scene, settings):
		file = CameraRoadFile()

		root = settings["cam_root"]

		if "axis_conversion_matrix" in settings:
			global_matrix = settings["axis_conversion_matrix"]
		else:
			global_matrix = None

		file.curves = []
		for object in settings["cam_root"].all_objects:
			if object.type == "CURVE":
				DMDcurve = CameraRoadCurve.from_blender_curve(
					object,
					global_matrix
				)
				file.curves.append(DMDcurve)

		return file

	def serialize(self):
		linker = Linker()

		header_blob_name = "header"
		header_data = bytearray(0x10c)
		struct.pack_into(">64s", header_data, 0x004, "MarioSt_CameraRoadExport".encode())
		struct.pack_into(">64s", header_data, 0x044, "1.01".encode()) # version
		date_text = datetime.datetime.utcnow().strftime("%Y/%m/%d")
		struct.pack_into(">64s", header_data, 0x084, date_text.encode())

		camera_parameter_blob_name = "camera_parameters"
		camera_parameter_data = bytearray(0xc)
		# fov/near/far
		# These values don't change the actual camera parameters, but at least
		# the FoV is used in camera shift calculations to figure out how much
		# to shift the camera, so these should be correct. TTYD uses 25 degree
		# FoV.
		struct.pack_into(">f", camera_parameter_data, 0x0, 25.0)
		struct.pack_into(">f", camera_parameter_data, 0x4, 0.01)
		struct.pack_into(">f", camera_parameter_data, 0x8, 1000.0)
		linker.add_blob(camera_parameter_blob_name, camera_parameter_data)
		linker.place_blob_in_section(camera_parameter_blob_name, "camera_parameters")

		for curve in self.curves:
			curve_blob_name = curve.link(linker)

		# Place sections apart from header now so addresses are available
		linker.place_section_at("camera_parameters", len(header_data))
		linker.place_section("curves")
		linker.place_section("markers")
		linker.place_section("polygons")
		linker.place_section("curve_data")
		linker.place_section("vertex_positions")
		linker.place_section("vertex_indices")

		# Finish header
		header_data_section_names = [
			"camera_parameters",
			"curves",
			"markers",
			"polygons",
			"curve_data",
			"vertex_positions",
			"vertex_indices"
		]
		for i, section_name in enumerate(header_data_section_names):
			entry_count = linker.get_section_blob_count(section_name)
			struct.pack_into(">L", header_data, 0xc4 + i * 4, entry_count)
			section_address = linker.get_section_address(section_name)
			struct.pack_into(">L", header_data, 0xe8 + i * 4, section_address)

		linker.add_blob(header_blob_name, header_data)
		linker.place_blob_in_section(header_blob_name, "header")

		# Finalize data
		linker.place_section_at("header", 0x0)
		assert(linker.resolve_relocations())
		linked_data = linker.serialize()

		# Fill size field
		struct.pack_into(">L", linked_data, 0x0, len(linked_data))

		return linked_data