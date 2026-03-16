from dataclasses import dataclass

try:
    from ..classes import tuplesH as triH
except:
    from classes import tuplesH as triH

@dataclass
class CamRoadHeader:
    size: int
    type: str
    version: str
    build_date: str

@dataclass
class CamRoadDataRaw:
    cameraParametersCount: int
    curvesCount: int
    geometryCount: int
    polygonsCount: int
    curveDataCount: int
    verticesCount: int
    indexCount: int
    gCount: int
    hCount: int
    offsetCameraParameters: int
    offsetCurves: int
    offsetGeometry: int
    offsetPolygons: int
    offsetCurveData: int
    offsetVertices: int
    offsetIndices: int
    offsetG: int
    offsetH: int

@dataclass
class CamRoadData:
    cameraParameters: list # of triH.XYZ
    curves: list # of CamRoadCurve's
    geometry: list
    polygons: list
    curveData: list # of triH.XYZ
    vertices: list # of triH.XYZ
    indices: list # of int
    #g_data: list - deprecated(?)
    #h_data: list - deprecated(?)

@dataclass
class CamRoadCurve:
    curveName: str
    wbLockY: int
    wLockedYVal: float
    bDisabled: int
    #pad (20 bytes)
    clampStartSegment: int
    clampEndSegment: int
    clampMaxDistanceLeft: float
    clampMaxDistanceRight: float
    clampStartSegmentProgress: float
    clampEndSegmentProgress: float
    wCameraToTargetDistance: float
    #pad (8 bytes)
    camElevationDegrees: float
    #pad (8 bytes)
    camPitchDegrees: float
    #pad (8 bytes)
    shiftXRate: float
    unk_80: float
    wbEnableClamping: int
    bbox: triH.bbox
    curve_data_offset: int
    curve_data_count: int
    geometry_offset: int
    geometry_count: int
    zero: int
    unk_count: int

@dataclass
class CamRoadGeometry:
    geomName: str
    bbox: triH.bbox
    vertex_offset: int
    vertex_count: int
    polygon_offset: int
    polygon_count: int

@dataclass
class CamRoadPolygon:
    index_offset: int
    index_count: int