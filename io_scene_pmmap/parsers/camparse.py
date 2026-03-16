import struct
import os
import pprint

try:
    from ..classes import camH
    from ..classes import tuplesH as triH
except:
    from classes import camH
    from classes import tuplesH as triH

# string helper
def read_fixed_string(f, size):
    raw = f.read(size)
    return raw.split(b"\x00", 1)[0].decode("shift_jis", errors="replace")

# read helpers
def r_u32(f):
    return struct.unpack(">I", f.read(4))[0]

def r_f32(f):
    return struct.unpack(">f", f.read(4))[0]

def r_2b(f):
    byte = struct.unpack(">H", f.read(2))[0]
    return byte

def r_1b(f):
    byte = struct.unpack(">B", f.read(1))[0]
    return byte

# main caller
def parse_cam_road(path):
    with open(path, "rb") as f:
        header = parse_cam_road_header(f)
        rawdata = read_cam_road_data(f)
        data = organize_cam_road_data(f, rawdata)

    cam_road = {
        "header": header,
        "rawdata": rawdata,
        "data": data
    }
    return cam_road

# data structures
def parse_cam_road_header(f):
    totalSize = struct.unpack(">I", f.read(4))[0]
    type = read_fixed_string(f, 64)
    version = read_fixed_string(f, 64)
    build_date = read_fixed_string(f, 64)

    print(f"Total Size: {totalSize}")
    print(f"Type: {type}")
    print(f"Version: {version}")
    print(f"Build Date: {build_date}")

    return camH.CamRoadHeader(totalSize, type, version, build_date)

def read_cam_road_data(f):
    cameraParameterCount = r_u32(f)
    curveCount = r_u32(f)
    geometryCount = r_u32(f)
    polygonCount = r_u32(f)
    curveDataCount = r_u32(f)
    vertexCount = r_u32(f)
    indexCount = r_u32(f)
    gCount = r_u32(f)
    hCount = r_u32(f)
    offsetCameraParameters = r_u32(f)
    offsetCurves = r_u32(f)
    offsetGeometry = r_u32(f)
    offsetPolygons = r_u32(f)
    offsetCurveData = r_u32(f)
    offsetVertices = r_u32(f)
    offsetIndices = r_u32(f)
    offsetG = r_u32(f)
    offsetH = r_u32(f)

    return camH.CamRoadDataRaw(
        cameraParametersCount=cameraParameterCount,
        curvesCount=curveCount,
        geometryCount=geometryCount,
        polygonsCount=polygonCount,
        curveDataCount=curveDataCount,
        verticesCount=vertexCount,
        indexCount=indexCount,
        gCount=gCount,
        hCount=hCount,
        offsetCameraParameters=offsetCameraParameters,
        offsetCurves=offsetCurves,
        offsetGeometry=offsetGeometry,
        offsetPolygons=offsetPolygons,
        offsetCurveData=offsetCurveData,
        offsetVertices=offsetVertices,
        offsetIndices=offsetIndices,
        offsetG=offsetG,
        offsetH=offsetH
    )
    
def organize_cam_road_data(f, rawdata):
    cameraParameters = []
    f.seek(rawdata.offsetCameraParameters)
    for i in range(rawdata.cameraParametersCount):
        cameraParameters.append(triH.XYZ(*struct.unpack(">3f", f.read(12))))

    curves = []
    f.seek(rawdata.offsetCurves)
    for i in range(rawdata.curvesCount):
        curves.append(createCurve(f))

    geometry = []
    f.seek(rawdata.offsetGeometry)
    for i in range(rawdata.geometryCount):
        geometry.append(createGeometry(f))

    polygons = []
    f.seek(rawdata.offsetPolygons)
    for i in range(rawdata.polygonsCount):
        polygons.append(createPolygon(f))

    curveData = []
    f.seek(rawdata.offsetCurveData)
    for i in range(rawdata.curveDataCount):
        curveData.append(createCurveData(f))

    vertices = []
    f.seek(rawdata.offsetVertices)
    for i in range(rawdata.verticesCount):
        vertices.append(createVertex(f))

    indices = []
    f.seek(rawdata.offsetIndices)
    for i in range(rawdata.indexCount):
        indices.append(createIndex(f))

    return camH.CamRoadData(
        cameraParameters=cameraParameters,
        curves=curves,
        geometry=geometry,
        polygons=polygons,
        curveData=curveData,
        vertices=vertices,
        indices=indices
    )

def createCurve(f):
    curveName = read_fixed_string(f, 32)
    wbLockY = r_u32(f)
    wLockedYVal = r_f32(f)
    bDisabled = r_u32(f)
    f.read(20) #padding
    clampStartSegment = r_u32(f)
    clampEndSegment = r_u32(f)
    clampMaxDistanceLeft = r_f32(f)
    clampMaxDistanceRight = r_f32(f)
    clampStartSegmentProgress = r_f32(f)
    clampEndSegmentProgress = r_f32(f)
    wCameraToTargetDistance = r_f32(f)
    f.read(8) #unk
    camElevationDegrees = r_f32(f)
    f.read(8) #unk
    camPitchDegrees = r_f32(f)
    f.read(8) #unk
    shiftXRate = r_f32(f)
    unk_80 = r_f32(f)
    wbEnableClamping = r_u32(f)
    bbox = triH.bbox(triH.XYZ(*struct.unpack(">3f", f.read(12))), triH.XYZ(*struct.unpack(">3f", f.read(12))))
    curve_data_offset = r_u32(f)
    curve_data_count = r_u32(f)
    geometry_offset = r_u32(f)
    geometry_count = r_u32(f)
    zero = r_u32(f) # always 0?
    unk_count = r_u32(f)

    return camH.CamRoadCurve(
        curveName=curveName,
        wbLockY=wbLockY,
        wLockedYVal=wLockedYVal,
        bDisabled=bDisabled,
        clampStartSegment=clampStartSegment,
        clampEndSegment=clampEndSegment,
        clampMaxDistanceLeft=clampMaxDistanceLeft,
        clampMaxDistanceRight=clampMaxDistanceRight,
        clampStartSegmentProgress=clampStartSegmentProgress,
        clampEndSegmentProgress=clampEndSegmentProgress,
        wCameraToTargetDistance=wCameraToTargetDistance,
        camElevationDegrees=camElevationDegrees,
        camPitchDegrees=camPitchDegrees,
        shiftXRate=shiftXRate,
        unk_80=unk_80,
        wbEnableClamping=wbEnableClamping,
        bbox=bbox,
        curve_data_offset=curve_data_offset,
        curve_data_count=curve_data_count,
        geometry_offset=geometry_offset,
        geometry_count=geometry_count,
        zero=zero,
        unk_count=unk_count
    )

def createGeometry(f):
    geomName = read_fixed_string(f, 64)
    bbox = triH.bbox(triH.XYZ(*struct.unpack(">3f", f.read(12))), triH.XYZ(*struct.unpack(">3f", f.read(12))))
    vertex_offset = r_u32(f)
    vertex_count = r_u32(f)
    polygon_offset = r_u32(f)
    polygon_count = r_u32(f)

    return camH.CamRoadGeometry(
        geomName=geomName,
        bbox=bbox,
        vertex_offset=vertex_offset,
        vertex_count=vertex_count,
        polygon_offset=polygon_offset,
        polygon_count=polygon_count
    )

def createPolygon(f):
    index_offset = r_u32(f)
    index_count = r_u32(f)

    return camH.CamRoadPolygon(
        index_offset=index_offset,
        index_count=index_count
    )

def createCurveData(f):
    XYZ = triH.XYZ(*struct.unpack(">3f", f.read(12)))
    return XYZ

def createVertex(f):
    XYZ = triH.XYZ(*struct.unpack(">3f", f.read(12)))
    return XYZ

def createIndex(f):
    index = r_u32(f)
    return index