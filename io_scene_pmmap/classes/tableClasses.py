from dataclasses import dataclass, field
from typing import Dict, Optional, Any, Union, List
import numpy as np

try:
    from . import animationH as a
    from . import materialH as m
    from . import objectsH as o
    from . import tuplesH as t
except ImportError:
    # Fallback to absolute import (when run standalone)
    import animationH as a
    import materialH as m
    import objectsH as o
    import tuplesH as t
    import tplH as tpl

#region: helpers
        #---------------------- EXTRAS ----------------------

#----------- Tables Helper -----------
@dataclass
class Table:
    address: int
    name_offset: int
    name: str
    data: Optional[Any] = None 

@dataclass
class VCDDataNP:
    count: int
    values: np.ndarray

@dataclass
class VCDData:
    count: int
    values: list

    def __repr__(self):
        # flatten one level (in case values contains lists/tuples of tables)
        flat = []
        for v in self.values:
            if isinstance(v, (list, tuple)):
                flat.extend(v)
            else:
                flat.append(v)

        parts = [f"Count: {self.count}", "Values:"]
        for v in flat:
            parts.append(str(v) if v is not None else "None")
            parts.append("")  # blank line between items
        return "\n".join(parts).rstrip()  # trim trailing newline

    
@dataclass
class VCDObjects:
    objects: list

    #---------------------- MAIN ----------------------

#----------- Whole Table Objects -----------
#   Everything Table-related is accesses through the DMDTables 
#    object, returned to pydmd as "Tables"

@dataclass
class DMDTables: 
    tables: Dict[str, Table] = field(default_factory=dict)

    def add_table(self, address, name_offset, name):
        self.tables[name] = Table(address, name_offset, name)

    def add_tableData(self, name: str, data: Any):
        """Attaches a data object to an existing table entry or creates a new one if missing."""
        if name not in self.tables:
            # If the table didn’t exist yet, make a new Table container
            self.tables[name] = Table(address=0, name_offset=0, name=name, data=data)
        else:
            # Otherwise, attach the data to the existing table
            self.tables[name].data = data

    def get(self, key: str, default=None):
        return self.tables.get(key, default)

    def __getitem__(self, key):
        return self.tables[key]

    def __repr__(self):
        out = "  DMD Tables\n   (name offset is in relation to the string table)\n\n"
        for t in self.tables.values():
            out += repr(t) + "\n"
        return out
    
    #----------- Tables Setup -----------
@dataclass
class OffsetTable:
    count: int
    offsets: list

    def __repr__(self):
        out = f"\n  (count={self.count}, offsets={self.offsets})"

        return out

@dataclass
class FogTable:
    wFogEnabled: int
    fogMode: int
    fogStart: float
    fogEnd: float
    fogColor: t.ColorRGBA

    def __repr__(self):
        out = f"\n  (enabled={self.wFogEnabled}, mode={self.fogMode}, start={self.fogStart}, end={self.fogEnd}, color=R:{self.fogColor.r}, G:{self.fogColor.g}, B:{self.fogColor.b}, A:{self.fogColor.a})"

        return out
    
@dataclass
class MaterialNameTable:
    count: int
    materialNames: list

    def __repr__(self):
        names_formatted = ",\n      ".join([repr(name).rstrip() for name in self.materialNames])
        out = f"\n  Count: {self.count}\n  Material Names: [\n  {names_formatted}\n]"
        return out

@dataclass
class TextureTable:
    count: int
    textures: list

    def __repr__(self):
        names_formatted = ",\n    ".join([repr(name).rstrip() for name in self.textures])
        out = f"\n  Count: {self.count}\n  Texture Names: [\n    {names_formatted}\n]"
        return out

@dataclass
class VCDTable:
    positionOffset: int
    normalOffset: int
    colorCount: int
    colorOffset0: int
    colorOffset1: int
    textureCoordinateCount: int
    textureCoordinateOffset: list
    unk_38: bytes
    unk_3C: bytes
    unk_40: bytes
    positionQuantizationShift: int
    textureCoordinateQuantizationShift: list

    def __repr__(self):
        out = (f"\n  Position Offset: {self.positionOffset}"
        f"\n  Normal Offset: {self.normalOffset}"
        f"\n  Color Count: {self.colorCount}"
        f"\n  Color Offset 0: {self.colorOffset0}"
        f"\n  Color Offset 1: {self.colorOffset1}"
        f"\n  Texture Coordinate Count: {self.textureCoordinateCount}"
        f"\n  Texture Coordinate Offset: {self.textureCoordinateOffset}"
        f"\n  Position Quantization Shift: {self.positionQuantizationShift}"
        f"\n  Texture Coordinate Quantization Shift: {self.textureCoordinateQuantizationShift}")
        return out

#region: scene

    # ---------- Scene Graph Helpers ----------

@dataclass
class attributes:
    drawMode: int
    cullMode: int
    wFlags: bytes
    padding: bytes
    lightMask: int
    hitAttributes: int
    unk_0c: bytes
    unk_10: bytes

@dataclass
class meshDescriptor:
    materialOffset: int
    meshOffset: int

@dataclass
class vertice:
    positionIndex: int
    normalIndex: int
    colorIndex0: int
    textureCoordinateIndex0: int
    textureCoordinateIndex1: int

@dataclass
class polygon:
    drawOpcode: int
    vertexCount: int
    vertices: list #appended with 'vertice' objects

@dataclass
class polygonInfo:
    offset: int
    size: int
    data: polygon

@dataclass
class mesh:
    unk_00: bytes
    unk_01: bytes
    unk_02: bytes
    bPolygonsAreDisplayLists: bool
    polygonCount: int
    elementMask: int
    vcdTableOffset: int
    polygonInfo: list #appended with 'polygonInfo' objects

    # ---------- Scene Graph Main ----------

@dataclass
class sceneData:
    positionData: Optional[VCDData] = None
    normalData: Optional[VCDData] = None
    colorData: Optional[VCDData] = None
    textureCoordinateData: Optional[VCDData] = None
    lightData: list = field(default_factory=list)
    animationData: list = field(default_factory=list)
    materialData: list = field(default_factory=list)

@dataclass
class sceneGraphRoot:
    name: str
    type: str
    parentOffset: int
    childOffset: int
    nextOffset: int
    prevOffset: int
    scale: t.XYZ
    rotation: t.XYZ
    translation: t.XYZ
    bbox: t.bbox
    unk_54: int
    unk_offset: int
    meshCount: int
    child: list #appended with all direct children, 
                #which are appended with their children
                #to allow for recursive scene construction

@dataclass
class childNull:
    name: str
    type: str
    parentOffset: int
    childOffset: int
    nextOffset: int
    prevOffset: int
    scale: t.XYZ
    rotation: t.XYZ
    translation: t.XYZ
    bbox: t.bbox
    unk_54: int
    unk_offset: int
    meshCount: int
    unk_data_mandatory: attributes
    children: List["Node"] = field(default_factory=list)  # filled by parser

@dataclass
class childMesh:
    name: str
    type: str
    parentOffset: int
    childOffset: int
    nextOffset: int
    prevOffset: int
    scale: t.XYZ
    rotation: t.XYZ
    translation: t.XYZ
    bbox: t.bbox
    unk_54: int
    unk_offset: int
    meshCount: int
    meshDescriptors: list
    unk_data_mandatory: attributes
    meshes: list
    children: List["Node"] = field(default_factory=list)  # filled by parser

Node = Union[childNull, childMesh]

@dataclass
class NodeCommon:
    name: str
    type: str
    parentOffset: int
    childOffset: int
    nextOffset: int
    prevOffset: int

    scale: t.XYZ
    rotation: t.XYZ
    translation: t.XYZ
    bbox: t.bbox

    unk_54: int
    unk_offset: int
    meshCount: int

    attrs: attributes

@dataclass
class VertexSource:
    positions: list | None = None   # [(x,y,z), ...]
    normals: list | None = None     # [(x,y,z), ...]
    colors0: list | None = None     # [(r,g,b,a), ...]
    uvs0: list | None = None        # [(u,v), ...]
    uvs1: Optional[list] | None = None

    # decoding behavior
    pos_is_float: bool = False
    nrm_is_float: bool = False
    uv_is_float: bool = False

    # quant shifts (only meaningful for non-float packed formats)
    pos_shift: int = 0
    tex0_shift: int = 0
    tex1_shift: Optional[int] = 0