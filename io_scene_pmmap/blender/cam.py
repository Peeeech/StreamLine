try:
    import bpy  # type: ignore
except ImportError:
    print("camra: no blenda")

def create_camroad_from_binary(cam_road, context):
    if context is None:
        context = bpy.context

    data = cam_road["data"]

    curvesRaw = data.curves
    curveData = data.curveData

    geometry = data.geometry
    polygons = data.polygons
    vertices = data.vertices
    indices = data.indices

    planes = create_camroad_regions(geometry, polygons, vertices, indices)
    curves = create_camroad_curves(curvesRaw, curveData, planes)

    for plane in planes:
        context.collection.objects.link(plane)

    for curve, bbox in curves:
        context.collection.objects.link(curve)
        context.collection.objects.link(bbox)

def create_camroad_curves(curvesRaw, curveData, planes):
    curves = []

    for curve in curvesRaw:
        bpycurve = bpy.data.curves.new(curve.curveName, type='CURVE')
        bpycurve.dimensions = '3D'

        spline = bpycurve.splines.new('POLY')

        curve_obj = bpy.data.objects.new(curve.curveName, bpycurve)

        attr = curve_obj.ttyd_world_curve

        dataEntries = curve.curve_data_count // 2
        for i in range(dataEntries):
            pos = curveData[curve.curve_data_offset + i]
            param = curveData[curve.curve_data_offset + dataEntries + i]

            entry = attr.localCurveIR.add()
            entry.pos = (pos.x, pos.y, pos.z)
            entry.param = (param.x, param.y, param.z)

        spline.points.add(dataEntries - 1)

        for i in range(dataEntries):
            pos = attr.localCurveIR[i].pos
            spline.points[i].co = (pos[0], pos[1], pos[2], 1)

        attr.wbLockY = curve.wbLockY
        attr.wLockedYVal = curve.wLockedYVal
        attr.bDisabled = curve.bDisabled
        attr.clampStartSegment = curve.clampStartSegment
        attr.clampEndSegment = curve.clampEndSegment
        attr.clampMaxDistanceLeft = curve.clampMaxDistanceLeft
        attr.clampMaxDistanceRight = curve.clampMaxDistanceRight
        attr.clampStartSegmentProgress = curve.clampStartSegmentProgress
        attr.clampEndSegmentProgress = curve.clampEndSegmentProgress
        attr.wCameraToTargetDistance = curve.wCameraToTargetDistance
        attr.camElevationDegrees = curve.camElevationDegrees
        attr.camPitchDegrees = curve.camPitchDegrees
        attr.shiftXRate = curve.shiftXRate
        attr.unk_80 = curve.unk_80
        attr.wbEnableClamping = curve.wbEnableClamping
        attr.bbox_min = (curve.bbox.min.x, curve.bbox.min.y, curve.bbox.min.z)
        attr.bbox_max = (curve.bbox.max.x, curve.bbox.max.y, curve.bbox.max.z)
        attr.curve_data_count = curve.curve_data_count
        attr.geometry_count = curve.geometry_count
        attr.zero = curve.zero
        attr.unk_count = curve.unk_count
        

        # --- create bbox cube ---
        bbox = curve.bbox
        bbox_obj = create_bbox_wireframe(curve.curveName + "_bbox", bbox)

        # parent bbox to curve
        bbox_obj.parent = curve_obj

        # --- parent geometry to curve ---
        geom_slice = planes[
            curve.geometry_offset :
            curve.geometry_offset + curve.geometry_count
        ]

        for plane in geom_slice:
            curve_obj.ttyd_world_curve.Marker = plane
            plane.parent = curve_obj

        curves.append((curve_obj, bbox_obj))

    return curves

def strip_curve_prefix(name):
    if name.startswith("|"):
        parts = [p for p in name.split("|") if p]
        if parts:
            return parts[-1]
    return name

def create_bbox_wireframe(name, bbox):

    clean_name = strip_curve_prefix(name)

    minx, miny, minz = bbox.min.x, bbox.min.y, bbox.min.z
    maxx, maxy, maxz = bbox.max.x, bbox.max.y, bbox.max.z

    verts = [
        (minx,miny,minz),(maxx,miny,minz),(maxx,maxy,minz),(minx,maxy,minz),
        (minx,miny,maxz),(maxx,miny,maxz),(maxx,maxy,maxz),(minx,maxy,maxz)
    ]

    edges = [
        (0,1),(1,2),(2,3),(3,0),
        (4,5),(5,6),(6,7),(7,4),
        (0,4),(1,5),(2,6),(3,7)
    ]

    mesh = bpy.data.meshes.new(clean_name)
    mesh.from_pydata(verts, edges, [])
    mesh.update()

    obj = bpy.data.objects.new(clean_name, mesh)

    obj.display_type = 'WIRE'

    return obj

def build_camroad_mesh(mesh, geom, polygons, vertices, indices, props):

    # polygons belonging to this geometry
    geom_polys = polygons[
        geom.polygon_offset : geom.polygon_offset + geom.polygon_count
    ]

    # vertex slice owned by this geometry
    geom_verts = vertices[
        geom.vertex_offset : geom.vertex_offset + geom.vertex_count
    ]

    props.local_vertices.clear()
    props.local_primitives.clear()

    verts = []
    faces = []

    for poly in geom_polys:

        poly_indices = indices[
            poly.index_offset : poly.index_offset + poly.index_count
        ]

        face_indices = []
        prim_indices = []

        for local_idx in poly_indices:

            # index is LOCAL to geom vertex slice
            v = geom_verts[local_idx]

            pos = (v.x, v.y, v.z)

            # IR vertex
            lv = props.local_vertices.add()
            lv.pos = pos

            # mesh vertex
            verts.append(pos)
            new_index = len(verts) - 1

            face_indices.append(new_index)
            prim_indices.append(new_index)

        # primitive packet
        prim = props.local_primitives.add()
        prim.opcode = 0x80
        prim.indices = ",".join(map(str, prim_indices))

        faces.append(face_indices)

    mesh.from_pydata(verts, [], faces)
    mesh.update()

    props.has_nrm = False
    props.has_uv0 = False
    props.has_uv1 = False
    props.has_col = False
    props.ir_dirty = False
    
def create_camroad_regions(geometry, polygons, vertices, indices):

    planes = []

    for geom in geometry:
        mesh = bpy.data.meshes.new(geom.geomName)
        obj = bpy.data.objects.new(geom.geomName, mesh)

        props = obj.ttyd_world_mesh
        props.isCamRoadRegion = True
        props.bbox_min = (geom.bbox.min.x, geom.bbox.min.y, geom.bbox.min.z)
        props.bbox_max = (geom.bbox.max.x, geom.bbox.max.y, geom.bbox.max.z)

        build_camroad_mesh(mesh, geom, polygons, vertices, indices, props)

        planes.append(obj)

    return planes