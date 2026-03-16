from dataclasses import dataclass, field
from typing import Dict, Optional, Any, Union, List
import numpy as np

#----------- Tuples -----------
@dataclass
class ColorRGBA:
    r: int
    g: int
    b: int
    a: int

@dataclass
class XYZ:
    x: float
    y: float
    z: float

@dataclass
class TangentXY:
    value: float
    tangentIn: float
    tangentOut: float
    unk_0c: float
    bStep: int

@dataclass
class bbox:
    min: XYZ
    max: XYZ