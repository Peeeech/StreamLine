from dataclasses import dataclass, field
from typing import Dict, Optional, Any, Union, List
import numpy as np

try:
    from . import tuplesH as t
except ImportError:
    # Fallback to absolute import (when run standalone)
    import tuplesH as t

# ----------- animation table helpers ----------
@dataclass
class animationTable:
    entryCount: int
    entryOffsets: list
    tracks: list #list, populated with 'track' objects
    
    def __repr__(self):
        lines = []
        for i, (off, t) in enumerate(zip(self.entryOffsets, self.tracks)):
            track = (
                getattr(t, "target_name", None)
                or getattr(t, "material_name", None)
                or getattr(t, "light_name", "???")
            )
            lines.append(
                f"      [{i}] offset={hex(off)}  track={track}"
            )

        return (
            f"  <AnimationTable entries={self.entryCount}>\n"
            + "\n".join(lines)
        )

    #----------- track objects:
@dataclass
class jointTransformAnimationTableTrack:
    target_name: str
    anim_origin: list   #list of 3 'TangentXY' objects (One for each Axis)
    anim_rotation: list #^^^^^
    anim_scale: list    #^^^^^
    obj_pos_delta: list 
    unk_34: bytes 
    unk_40: bytes 
    unk_4c: bytes 
    keyframeCount: int
    keyframes: list #list, populated with respective 'keyframe' objects

    def __repr__(self):
        return (
            f"<JointTrack '{self.target_name}' ({self.keyframeCount} keyframes)>\n"
            f"  Origin: {self.anim_origin}\n"
            f"  Rotation: {self.anim_rotation}\n"
            f"  Scale: {self.anim_scale}"
        )

@dataclass
class materialUvAnimationTableTrack:
    material_name: str
    samplerIndex: int
    skewX: float
    skewY: float
    keyframeCount: int
    keyframes: list #list, populated with respective 'keyframe' objects

    def __repr__(self):
        return (
            f"<MaterialUVTrack '{self.target_name}' sampler={self.samplerIndex} "
            f"({self.keyframeCount} keyframes)>"
        )

@dataclass
class materialBlendAlphaAnimationTableTrack:
    material_name: str
    keyframeCount: int
    keyframes: list #list, populated with 'keyframe' objects

@dataclass
class lightTransformAnimationTableTrack:
    light_name: str
    keyframeCount: int
    keyframes: list #list, populated with respective 'keyframe' objects

    def __repr__(self):
        return f"<LightTransformTrack '{self.light_name}' ({self.keyframeCount} keyframes)>"


@dataclass
class lightParameterAnimationTableTrack:
    light_name: str
    keyframeCount: int
    keyframes: list #list, populated with respective 'keyframe' objects

    def __repr__(self):
        col = ", ".join(f"{c.value:.3f}" for c in self.color)
        return (
            f"<LightParamKeyframe t={self.time:.2f}s "
            f"color=[{col}] spot={self.spotAngle.value:.3f} attn={self.angularAttenuation.value:.3f}>"
        )

    #----------- keyframe objects:
@dataclass
class jointTransformAnimationKeyframe:
    time: float
    translation: t.XYZ
    rotation: t.XYZ
    scale: t.XYZ
    unk_b8: bytes
    unk_f4: bytes
    unk_130: bytes
    unk_16c: bytes

@dataclass
class materialUvAnimationKeyframe:
    time: float
    translationX: t.TangentXY
    translationY: t.TangentXY
    scaleX: t.TangentXY
    scaleY: t.TangentXY
    rotateZ: t.TangentXY

@dataclass
class materialBlendAlphaAnimationKeyframe:
    time: float
    rgba: list #appended with 'matBlendAlphaRGBA' TangentXY objects

@dataclass
class lightTransformAnimationKeyframe:
    time: float
    translation: t.XYZ
    rotation: t.XYZ
    scale: t.XYZ

@dataclass
class lightParameterAnimationKeyframe:
    time: int
    color: list #list of 'color' TangentXY values
    spotAngle: t.TangentXY
    angularAttenuation: t.TangentXY
    

@dataclass
class AnimBundle:
    name: str
    lengthFrames: int
    joint: Optional[animationTable] = None
    mat_uv: Optional[animationTable] = None
    mat_alpha: Optional[animationTable] = None
    light_xform: Optional[animationTable] = None
    light_param: Optional[animationTable] = None

    def __repr__(self):
        parts = ["[Animation Group]"]
        def add(label, obj):
            if obj is None:
                parts.append(f"  - {label}: None")
            else:
                parts.append(f"  - {label}:")
                # indent the table nicely
                body = "\n".join("    " + line for line in str(obj).splitlines())
                parts.append(body)
        add("Name", self.name)
        add("Length", self.lengthFrames)
        add("JointMeshAnim", self.joint)
        add("MatUvAnim", self.mat_uv)
        add("MatAlphaBlendAnim", self.mat_alpha)
        add("LightTransAnim", self.light_xform)
        add("LightParamAnim", self.light_param)
        # optional separator after a group:
        parts.append("─" * 60)
        return "\n".join(parts)