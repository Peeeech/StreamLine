from dataclasses import dataclass, field
from typing import Dict, Optional, Any, Union, List
import numpy as np

@dataclass
class matName:
    name: str
    offset: int

@dataclass
class texCoordTransforms:
    translateX: float
    translateY: float
    scaleX: float
    scaleY: float
    rotateZ: float
    warpX: float
    warpY: float

@dataclass
class Texture:
    name: str
    render_order: int
    unk_05: bytes
    unk_06: bytes
    unk_07: bytes
    wWidth: int
    wHeight: int
    unk_0c: bytes

@dataclass
class Sampler:
    textureOffset: int
    unk_04: bytes
    wrapS: int
    wrapT: int
    unk_0a: bytes
    unk_0b: bytes
    texture: Texture

@dataclass
class TEV:
    tevMode: int
    unk_01: bytes
    unk_02: bytes
    unk_03: bytes
    unk_04: bytes
    unk_08: bytes