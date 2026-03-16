from dataclasses import dataclass, field
from typing import Optional, Any, Tuple, List
import numpy as np

try:
    from . import tuplesH as t
    from . import animationH as a
    from . import materialH as m
except ImportError:
    # Fallback to absolute import (when run standalone)
    import tuplesH as t
    import animationH as a
    import materialH as m

@dataclass
class light:
    name: str
    type: str
    position: t.XYZ
    rotation: t.XYZ
    scale: t.XYZ
    color: t.ColorRGBA
    spotAngleFullDegrees: float
    angularAttenuation: float
    distanceAttenuationType: int
    wFlags: int
    wEnableFlagsIf012d60d8: int #i'm presuming flags are enabled if the value is that..? --named from Piston's .bt

    def __repr__(self):
        return (
            f"  Light '{self.name}'     ({self.type})\n"
            f"  Position: ({self.position.x:.3f}, {self.position.y:.3f}, {self.position.z:.3f})\n"
            f"  Rotation: ({self.rotation.x:.3f}, {self.rotation.y:.3f}, {self.rotation.z:.3f})\n"
            f"  Scale:    ({self.scale.x:.3f}, {self.scale.y:.3f}, {self.scale.z:.3f})\n"
            f"  Color:    (R={self.color.r}, G={self.color.g}, B={self.color.b}, A={self.color.a})\n"
            f"  Spot Angle: {self.spotAngleFullDegrees:.2f}°\n"
            f"  Angular Attenuation: {self.angularAttenuation:.3f}\n"
            f"  Distance Attenuation Type: {self.distanceAttenuationType}\n"
            f"  wFlags: {hex(self.wFlags)}\n"
            f"  wEnableFlagsIf012d60d8: {hex(self.wEnableFlagsIf012d60d8)}"
        )
    
@dataclass
class Animation:
    name: str
    unk_04: bytes
    lengthFrames: float
    pJointTransformAnimationTable: int
    pMaterialUvAnimationTable: int
    #TODO: pMaterialBlendAlphaAnimationTable:
    pLightTransformAnimationTable: int
    pLightParameterAnimationTable: int

    jointTransformAnimationTable: Optional[a.animationTable] = None    #passed with object populated by specific animTable type
    materialUvAnimationTable: Optional[a.animationTable] = None        #^^^^^
    #TODO: materialBlendAlphaAnimationTable:
    lightTransformAnimationTable: Optional[a.animationTable] = None    #^^^^^
    lightParameterAnimationTable: Optional[a.animationTable] = None    #^^^^^

    def __repr__(self):
        lines = [f"\n<AnimationTable entries={self.entryCount}>"]
        for i, (off, track) in enumerate(zip(self.entryOffsets, self.tracks)):
            name = getattr(track, "target_name", None) or getattr(track, "light_name", None) or "???"
            lines.append(f"  [{i}] offset={hex(off):<10} track={name}\n")
        return "\n".join(lines) + "─" * 60 + "\n"
    
@dataclass
class Material:
    offset: int
    name: str
    color: t.ColorRGBA
    matSrc: int #0: Use Material's RGBA color, 1: Use Vertex color baked into mesh data
    unk_009: bytes
    blendMode: int #0: Opaque, 1: Alpha 'BLEND'? 2: Alpha 'CLIP'?
    numTextures: int
    textureSamplerOffsets: list
    textureCoordTransforms: list #appended with ' textureCoord' objects
    blendAlphaModulationR: t.ColorRGBA
    pTevConfig: int
    textureSamplers: list #appended with 'sampler' objects
    tevConfig: m.TEV

@dataclass
class MeshEntry:
    meshOffset: int
    material: Any
    mesh_header: Any
    vcd_table: int
    polygons: dict
    local_ir: Any

@dataclass
class ResolvedVertex:
    pi: int
    pos: Tuple[float, float, float]
    nrm: Tuple[float, float, float]
    clr: Optional[Tuple[int, int, int, int]]
    uvs0: Optional[Tuple[float, float]]
    uvs1: Optional[Tuple[float, float]]

@dataclass
class FlatGeometry:
    positions: List[Tuple[float, float, float]]
    normals:   List[Optional[Tuple[float, float, float]]]
    uvs0:       List[Optional[Tuple[float, float]]]
    uvs1:       List[Optional[Tuple[float, float]]]
    colors:    List[Optional[Tuple[float, float, float, float]]]
    polys:     List[Tuple[int, int]]  # (start, count)
    preserved_primitives: List[Any]
    flat_pi:   List[int]  # Flattened position indices for all vertices
    prim_positions: List[Tuple[float, float, float]]
    prim_normals:   List[Optional[Tuple[float, float, float]]]
    prim_uvs0:       List[Optional[Tuple[float, float]]]
    prim_uvs1:       List[Optional[Tuple[float, float]]]
    prim_colors:    List[Optional[Tuple[float, float, float, float]]]