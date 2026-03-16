import struct
from dataclasses import dataclass
import numpy as np
import pprint
import os
import traceback
from typing import List, Dict, Tuple

try:
    from ..classes import tableClasses as mainH, animationH as animH, objectsH as objH, materialH as matH, tuplesH as triH
except ImportError:
    # Fallback to absolute import (when run standalone)
    from classes import tableClasses as mainH, animationH as animH, objectsH as objH, materialH as matH, tuplesH as triH #type: ignore

@dataclass
class PreservedPrimative:
    opcode: int
    vertexCount: int
    pos_indices: list[int]

DEBUG_VCD = False  # flip off when done

#Const vals
VCD_POS  = 1 << 0  # 0x001
VCD_NRM  = 1 << 1  # 0x002
VCD_CLR0 = 1 << 2  # 0x004
VCD_CLR1 = 1 << 3  # 0x008
VCD_TEX0 = 1 << 4  # 0x010
VCD_TEX1 = 1 << 5  # 0x020
VCD_TEX2 = 1 << 6  # 0x040
VCD_TEX3 = 1 << 7  # 0x080
VCD_TEX4 = 1 << 8  # 0x100
VCD_TEX5 = 1 << 9  # 0x200
VCD_TEX6 = 1 << 10 # 0x400
VCD_TEX7 = 1 << 11 # 0x800

SENTINEL = 0xFFFF

#region: helpers
def read_string(f, offset):
    pos = f.tell()
    try:
        f.seek(offset)
        out = bytearray()
        while True:
            b = f.read(1)
            if not b or b == b"\x00":
                break
            out.extend(b)
        try:
            return out.decode("shift_jis")
        except UnicodeDecodeError:
            return out.decode("ascii", errors="replace")
    finally:
        f.seek(pos)

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

def _file_size(f):
    cur = f.tell()
    f.seek(0, os.SEEK_END)
    sz = f.tell()
    f.seek(cur)
    return sz

def _dbg(msg):
    if DEBUG_VCD:
        print(msg)

def _seek_checked(f, abs_off, label):
    sz = _file_size(f)
    _dbg(f"[vcdData] seek {label}: abs=0x{abs_off:08X} (file_size=0x{sz:08X})")
    if abs_off < 0 or abs_off > sz:
        raise ValueError(f"[vcdData] {label}: seek out of range abs=0x{abs_off:X} file_size=0x{sz:X}")
    f.seek(abs_off)

def _read_exact(f, n, label):
    b = f.read(n)
    if len(b) != n:
        raise EOFError(f"[vcdData] {label}: wanted {n} bytes, got {len(b)} at 0x{f.tell():X}")
    return b

#region: main classes
@dataclass
class DMDHeader:
    file_size: int
    offsetTableOffset: int
    offset_count: int
    table_count: int

    def __repr__(self):
        return (
            f"  DMD Header\n\n"
            f"  file_size =  0x{self.file_size:X} \n"
            f"  offsetTableOffset =  0x{self.offsetTableOffset:X} \n"
            f"  offset_count =  0x{self.offset_count:X} \n"
            f"  table_count =  0x{self.table_count:X} \n"
        )

@dataclass
class DMDInfo:
    versionString: str
    sceneGraphRootOffset: int
    sgNodeAString: str
    sgNodeBString: str
    dateString: str

    def __repr__(self):
        return ("\n"
            f"  versionString =  {self.versionString} \n"
            f"  sceneGraphRootOffset =  0x{self.sceneGraphRootOffset:X} \n"
            f"  sgNodeAString =  {self.sgNodeAString} \n"
            f"  sgNodeBString =  {self.sgNodeBString} \n"
            f"  dateString =  {self.dateString}"
        )


#region: functions
def header(f):
    """Parse the header from the filestart"""
    file_size, offsetTableOffset, offset_count, table_count = struct.unpack(">4I", f.read(16))
    return DMDHeader(file_size, offsetTableOffset, offset_count, table_count)

def offsetTable(f, header, offs):
    f.seek(header.offsetTableOffset)
    f.read(offs) # NOTE: some future calls will be offset by the header and the padding for future ref: these are set to a static '32' in pydmd.py
                 #  they will only be re-offset if they restart using an f.seek, which the two tables following the offsTable do *not*

    offsets = struct.unpack(f">{header.offset_count}I", f.read(header.offset_count * 4))
    #NOTE: these are parsed, but i really don't think theres a good reason to, considering they'd only be used if the filesize and everything was consistent.
    #   that being said, i'm gonna leave the logic in-case of future necessity, but i can't see why it would

def table(f, table_count):
    """First grabs the Tables' offsets, which directly follow the offsetTable, then grabs the null-terminated strings that follow directly"""
    tablesStringStart = f.tell() + (8 * table_count)
    tables = mainH.DMDTables()

    # Each table entry = 8 bytes (4 for address, 4 for name offset)
    entries = struct.unpack(f">{2 * table_count}I", f.read(table_count * 8))

    # Split them into pairs (addr, name_off)
    pairs = [(entries[i], entries[i + 1]) for i in range(0, len(entries), 2)]

    # Read all names dynamically
    for addr, name_off in pairs:
        name = read_string(f, tablesStringStart + name_off)
        tables.add_table(addr, name_off, name)

    return tables
   
#region: Tables
#NOTE: to check if a list is empty, use "if not [list]" NOT "if [list] is empty"

def animation_table(f, offs, tables):
    anim_table = tables["animation_table"]
    if anim_table is None:
        return None  # or [], or just skip animation parsing
    animAddr = anim_table.address
    f.seek(offs +animAddr)
    count = r_u32(f)
    offsets = []
    for i in range(count):
        offsets.append(r_u32(f))

    return mainH.OffsetTable(count, offsets)

def curve_table(f, offs, tables):
    curve_table = tables["curve_table"]
    curveAddr = curve_table.address
    f.seek(offs + curveAddr)
    count = r_u32(f)
    offsets = []
    for i in range(count):
        offsets.append(r_u32(f))

    return mainH.OffsetTable(count, offsets)
    
def fog_table(f, offs, tables):
    fog_table = tables["fog_table"]
    fogAddr = fog_table.address
    f.seek(offs + fogAddr)
    wFogEnabled, fogMode = struct.unpack(">2I", f.read(8))
    fogStart, fogEnd = struct.unpack(">2f", f.read(8))
    fogColor = triH.ColorRGBA(*(f.read(4)))

    return mainH.FogTable(wFogEnabled, fogMode, fogStart, fogEnd, fogColor)

def info(f, offs, tables):
    info_table = tables["information"]
    infoAddr = info_table.address
    f.seek(offs + infoAddr)
    versionStringOffs, sceneGraphRootOffset, sgNodeAStringOffs, sgNodeBStringOffs, dateStringOffs = struct.unpack(">5I", f.read(20))

    versionString = read_string(f, offs + versionStringOffs)
    sgNodeAString = read_string(f, offs + sgNodeAStringOffs)
    sgNodeBString = read_string(f, offs + sgNodeBStringOffs)
    dateString = read_string(f, offs + dateStringOffs)
    
    return DMDInfo(versionString, sceneGraphRootOffset, sgNodeAString, sgNodeBString, dateString)

def light_table(f, offs, tables):
    light_table = tables["light_table"]
    lightAddr = light_table.address
    f.seek(offs + lightAddr)
    count = r_u32(f)
    offsets = []

    for i in range(count):
        offsets.append(r_u32(f))

    return mainH.OffsetTable(count, offsets)

def material_name_table(f, offs, tables):
    material_name_table = tables["material_name_table"]
    matAddr = material_name_table.address
    f.seek(offs + matAddr)
    count = r_u32(f)
    rawMaterialNames = []

    for i in range(count):
        rawMaterialNames.append((r_u32(f), r_u32(f)))
    
    matNames = []
    for name_offset, offset in rawMaterialNames:
        name = read_string(f, offs + name_offset)
        matNames.append(matH.matName(name, offset))

    return mainH.MaterialNameTable(count, matNames)

def texture_table(f, offs, tables):
    texture_table = tables["texture_table"]
    texAddr = texture_table.address
    f.seek(offs + texAddr)
    count = r_u32(f)
    textures = []

    for i in range(count):
        textures.append(read_string(f, (offs + r_u32(f))))

    return mainH.TextureTable(count, textures)

def vcd_table(f, offs, tables):
    vcd_table = tables.get("vcd_table")
    if vcd_table is None:
        return
    vcdAddr = vcd_table.address
    f.seek(offs + vcdAddr)
    textureCoordinateOffset = []
    textureCoordinateQuantizationShift = []

    positionOffset, normalOffset, colorCount, colorOffset0, colorOffset1, textureCoordinateCount = struct.unpack(">6I", f.read(24))
    for i in range(8):
        textureCoordinateOffset.append(r_u32(f))
    unk_38, unk_3C, unk_40, positionQuantizationShift = struct.unpack(">4I", f.read(16))
    for i in range(8):
        textureCoordinateQuantizationShift.append(r_u32(f))

    return mainH.VCDTable(positionOffset, normalOffset, colorCount, 
                                 colorOffset0, colorOffset1, textureCoordinateCount, 
                                 textureCoordinateOffset, unk_38, unk_3C, unk_40,
                                 positionQuantizationShift, textureCoordinateQuantizationShift)

from dataclasses import dataclass
import struct

def _clamp_shift(x: int) -> int:
    try:
        x = int(x)
    except Exception:
        return 0
    # protect against garbage values (your OverflowError case)
    if x < 0 or x > 30:
        return 0
    return x


def _read_counted_block(f, base_off: int, block_off: int, elem_fmt: str):
    """
    Reads a block stored as:
        u32 count
        count * struct(elem_fmt)
    Returns list[tuple].
    """
    if not block_off:
        return None

    pos = f.tell()
    try:
        f.seek(base_off + block_off)
        raw = f.read(4)
        if len(raw) != 4:
            return None
        count = r_u32(f)
        if count == 0:
            return []

        elem_size = struct.calcsize(elem_fmt)
        raw = f.read(count * elem_size)
        if len(raw) != count * elem_size:
            return None

        return [t for t in struct.iter_unpack(elem_fmt, raw)]
    finally:
        f.seek(pos)


def _read_model_vcd_vertex_source(f, base_off: int, model_vcd_off: int, packed: bool) -> mainH.VertexSource:
    """
    Reads the per-mesh 'modelVcdTableOffs' structure that NoClip uses even when the global 'vcd_table' chunk is absent.
    This gives you per-mesh vertex buffers (positions/normals/colors/uv0).
    """
    vs = mainH.VertexSource()

    pos = f.tell()
    try:
        f.seek(base_off + model_vcd_off)

        pos_blk = r_u32(f)   # 0x00
        nrm_blk = r_u32(f)   # 0x04
        _clr_count = r_u32(f)  # 0x08 (redundant if blocks are counted, but exists)
        clr0_blk = r_u32(f)  # 0x0C
        _clr1_blk = r_u32(f) # 0x10
        _tex_count = r_u32(f)  # 0x14
        tex0_blk = r_u32(f)  # 0x18

        # (There are more tex offsets after this; you can add them later if you start supporting tex1/2.)

        # Shifts live deeper in the struct for packed formats (NoClip reads these at +0x44, +0x48, ...)
        if packed:
            try:
                f.seek(base_off + model_vcd_off + 0x44)
                vs.pos_shift = _clamp_shift(r_u32(f))
                vs.tex0_shift = _clamp_shift(r_u32(f))
            except Exception:
                vs.pos_shift = 0
                vs.tex0_shift = 0

        # Version 100 (your “no vcd_table chunk” maps) uses float32 buffers in NoClip.
        # We treat *non-packed* meshes as float32 buffers.
        if not packed:
            vs.pos_is_float = True
            vs.nrm_is_float = True
            vs.uv_is_float = True

        # positions
        if vs.pos_is_float:
            vs.positions = _read_counted_block(f, base_off, pos_blk, ">fff")
        else:
            vs.positions = _read_counted_block(f, base_off, pos_blk, ">hhh")

        # normals
        if vs.nrm_is_float:
            vs.normals = _read_counted_block(f, base_off, nrm_blk, ">fff")
        else:
            vs.normals = _read_counted_block(f, base_off, nrm_blk, ">hhh")

        # colors0
        vs.colors0 = _read_counted_block(f, base_off, clr0_blk, ">BBBB")

        # uv0
        if vs.uv_is_float:
            vs.uvs0 = _read_counted_block(f, base_off, tex0_blk, ">ff")
        else:
            vs.uvs0 = _read_counted_block(f, base_off, tex0_blk, ">hh")

        return vs

    finally:
        f.seek(pos)

def _part_vertex_block_as_polygon(f, base_off: int, vertex_data_off: int):
    """
    Non-packed path: vertex_data_off points to:
        u32 vertexCount
        vertexCount * 0x18 bytes of indices (12 u16 per vertex)
    We emit a polygonData with opcode 0x98 (TRI_STRIP).
    """
    pos = f.tell()
    try:
        f.seek(base_off + vertex_data_off)
        vertexCount = r_u32(f)

        vertices = []
        for _ in range(vertexCount):
            # 12 * u16 = 0x18 bytes
            posIdx  = r_2b(f)  # +0x00
            nrmIdx  = r_2b(f)  # +0x02
            clr0Idx = r_2b(f)  # +0x04
            _clr1   = r_2b(f)  # +0x06 (unused)
            tex0Idx = r_2b(f)  # +0x08
            tex1Idx   = r_2b(f)  # +0x0A
            _tex2   = r_2b(f)  # +0x0C
            _tex3   = r_2b(f)  # +0x0E
            _tex4   = r_2b(f)  # +0x10
            _tex5   = r_2b(f)  # +0x12
            _tex6   = r_2b(f)  # +0x14
            _tex7   = r_2b(f)  # +0x16

            vertices.append(
                mainH.vertice(
                    positionIndex=posIdx,
                    normalIndex=nrmIdx,
                    colorIndex0=clr0Idx,
                    textureCoordinateIndex0=tex0Idx,
                    textureCoordinateIndex1=tex1Idx,
                )
            )

        return mainH.polygon(0x98, vertexCount, vertices)

    finally:
        f.seek(pos)



#region: Data
def vcdData(f, fileName, offs, tables, versionString: str | None = None):
    """
    Builds scene-wide data object:
      - global VCD buffers (pos/nrm/clr/uv) if global vcd_table exists,
        otherwise empty buffers (version 1.00-style maps).
      - independent tables (lights/anims/materials) always parsed.
    """
    # Determine version (prefer explicit param; fallback to information table)
    if versionString is None:
        try:
            info_tbl = tables.get("information")
            versionString = getattr(getattr(info_tbl, "data", None), "versionString", None)
        except Exception:
            versionString = None

    # ver1.02: global VCD table exists and should be used.
    # ver1.00: no global VCD table chunk; use per-mesh model VCD tables.
    use_global_vcd = (versionString == "ver1.02")

    pos_saved = f.tell()
    try:
        vcd_tbl_entry = tables.get("vcd_table") if use_global_vcd else None
        vcd_data = vcd_tbl_entry.data if (vcd_tbl_entry and vcd_tbl_entry.data) else None

        #print(f"[vcdData] offs(mainData)=0x{offs:08X} vcd_table_entry={'yes' if vcd_data else 'no'}")

        # ---------- Global VCD buffers ----------
        if vcd_data is None:
            # No global vcd_table chunk: keep globals empty.
            # (Meshes should use per-mesh model VCD tables via vertex_src fallback.)
            print("VER1.00: [vcdData] No global vcd_table data -> using empty global buffers.")

            positions = np.zeros((0, 3), dtype=np.int16)
            normals   = np.zeros((0, 3), dtype=np.int8)
            colors    = np.zeros((0, 4), dtype=np.uint8)
            uvs       = np.zeros((0, 2), dtype=np.int16)

            positionData = mainH.VCDDataNP(0, positions)
            normalData   = mainH.VCDDataNP(0, normals)
            colorData    = mainH.VCDDataNP(0, colors)
            textureCoordinateData = mainH.VCDDataNP(0, uvs)

        else:
            # Positions
            try:
                f.seek(offs + vcd_data.positionOffset)
                posCount = r_u32(f)
                #print(f"[vcdData] positions: off=0x{vcd_data.positionOffset:08X} count={posCount}")

                num_vals = posCount * 3
                buf = f.read(num_vals * 2)
                if len(buf) != num_vals * 2:
                    raise EOFError(f"positions buffer short: got={len(buf)} need={num_vals*2}")

                positions = np.frombuffer(buf, dtype=">i2").astype(np.int16).reshape((posCount, 3))
                positionData = mainH.VCDDataNP(posCount, positions)
            except Exception as e:
                raise RuntimeError(
                    f"[vcdData] failed reading positions: offs=0x{offs:08X} "
                    f"posOff=0x{getattr(vcd_data,'positionOffset',0):08X}"
                ) from e

            # Normals
            try:
                f.seek(offs + vcd_data.normalOffset)
                norCount = r_u32(f)
                #print(f"[vcdData] normals: off=0x{vcd_data.normalOffset:08X} count={norCount}")

                num_vals = norCount * 3
                buf = f.read(num_vals)
                if len(buf) != num_vals:
                    raise EOFError(f"normals buffer short: got={len(buf)} need={num_vals}")

                normals = np.frombuffer(buf, dtype=np.int8).reshape((norCount, 3))
                normalData = mainH.VCDDataNP(norCount, normals)
            except Exception as e:
                raise RuntimeError(
                    f"[vcdData] failed reading normals: offs=0x{offs:08X} "
                    f"nrmOff=0x{getattr(vcd_data,'normalOffset',0):08X}"
                ) from e

            # Colors
            try:
                if vcd_data.colorCount == 0 or vcd_data.colorOffset0 == 0:
                    colors = np.zeros((0, 4), dtype=np.uint8)
                    colorData = mainH.VCDDataNP(0, colors)
                    #print("[vcdData] colors: none")
                else:
                    f.seek(offs + vcd_data.colorOffset0)
                    colCount = r_u32(f)
                    #print(f"[vcdData] colors: off=0x{vcd_data.colorOffset0:08X} count={colCount}")

                    buf = f.read(colCount * 4)
                    if len(buf) != colCount * 4:
                        raise EOFError(f"colors buffer short: got={len(buf)} need={colCount*4}")

                    colors = np.frombuffer(buf, dtype=np.uint8).reshape((colCount, 4))
                    colorData = mainH.VCDDataNP(colCount, colors)
            except Exception as e:
                raise RuntimeError(
                    f"[vcdData] failed reading colors: offs=0x{offs:08X} "
                    f"colOff=0x{getattr(vcd_data,'colorOffset0',0):08X}"
                ) from e

                # ---------- Tex Coords ----------
            textureCoordinates = []
            texCoordsUsed = vcd_data.textureCoordinateCount
            for i in range(texCoordsUsed):
                f.seek(offs + vcd_data.textureCoordinateOffset[i])
                txCCount = r_u32(f)

                num_vals = txCCount * 2 # X and Y for each
                buf = f.read(num_vals * 2) #2 bytes per var
                textureCoordinates.append(np.frombuffer(buf, dtype=">i2").astype(np.int16).reshape((txCCount, 2)))

            textureCoordinateData = mainH.VCDData(texCoordsUsed, textureCoordinates)
    except:
        print("awe man")
    """
        Now for the independent data types
    """


        # ---------- Lights ----------
    light_table = tables["light_table"]
    light_data = light_table.data
    
    lights = []
    lightCount = light_data.count

    for i in range(lightCount):
        f.seek(offs + light_data.offsets[i])

        name = (read_string(f, (offs + r_u32(f))))
        type = (read_string(f, (offs + r_u32(f))))
        position = triH.XYZ(*(struct.unpack(">3f", f.read(12))))
        rotation = triH.XYZ(*(struct.unpack(">3f", f.read(12))))
        scale = triH.XYZ(*(struct.unpack(">3f", f.read(12))))
        color = triH.ColorRGBA(*(f.read(4)))
        print(color)
        spotAngleFullDegrees = r_f32(f)
        angularAttenuation = r_f32(f)
        distanceAttenuationType = r_u32(f)
        wFlags = r_u32(f)
        wEnableFlagsIf012d60d8 = r_u32(f)

        light = objH.light(name, type, position, rotation, scale, color, spotAngleFullDegrees, angularAttenuation, distanceAttenuationType, wFlags, wEnableFlagsIf012d60d8)
        lights.append(light)

    lightData = mainH.VCDData(lightCount, lights)

        # ---------- Animations ----------
    animation_table = tables["animation_table"]
    animation_data = animation_table.data

    animations = []

    jointTransformAnimationTable = None
    materialUvAnimationTable = None
    materialBlendAlphaAnimationTable = None
    lightTransformAnimationTable = None
    lightParameterAnimationTable = None

    #NOTE: Piston's DMD (.bt) mentions another type of animation (or 2?), but I haven't found a TTYD map that has one
    #to test implementation/fidelity of variable names (Material Blend Alpha Animations)
    #   NOTE: Presumably these would hook into Material's 'blendAlphaModulationR' values, and animate the alpha color at the blend stage of GX rendering

    animationCount = animation_data.count

    for i in range(animationCount):
        f.seek(offs + animation_data.offsets[i])

        name = (read_string(f, (offs + r_u32(f))))
        unk_04 = r_u32(f)
        lengthFrames = r_f32(f)
        pJointTransformAnimationTable = r_u32(f)
        pMaterialUvAnimationTable = r_u32(f)
        pMaterialBlendAlphaAnimationTable = r_u32(f)
        pLightTransformAnimationTable = r_u32(f)
        pLightParameterAnimationTable = r_u32(f)
        unk_20 = r_u32(f)
        unk_24 = r_u32(f)

        jointTransformAnimationTable = None
        materialUvAnimationTable = None
        materialBlendAlphaAnimationTable = None
        lightTransformAnimationTable = None
        lightParameterAnimationTable = None

        if unk_04 != 0:
            print(f"\n\n{fileName}:\n UNK 04 in {name} {unk_04}")
        if unk_20 != 0:
            print(f"\n\n{fileName}:\n UNK 20 in {name} {unk_20}")
        if unk_24 != 0:
            print(f"\n\n{fileName}:\n UNK 24 {name} {unk_24}")

    # ----- Joint (mesh) Animations
        if pJointTransformAnimationTable != 0:
            f.seek(offs + pJointTransformAnimationTable)
            entryOffsets = []
            tracks = []

            entryCount = r_u32(f)
            for t in range(entryCount):             #Track setup (Could technically be specified by making a new range(len(entryOffsets)) but it'd be redundant                
                trackOffset = r_u32(f)
                entryOffsets.append(trackOffset)

            for t, offset in enumerate(entryOffsets):
                f.seek(offs + offset)
                
                target_name = (read_string(f, (offs + r_u32(f))))
                anim_origin = triH.XYZ(*(struct.unpack(">3f", f.read(12))))
                anim_rotation = triH.XYZ(*(struct.unpack(">3f", f.read(12))))
                anim_scale = triH.XYZ(*(struct.unpack(">3f", f.read(12))))
                obj_pos_delta = triH.XYZ(*(struct.unpack(">3f", f.read(12))))
                
                unk_34 = f.read(12)
                unk_40 = f.read(12)
                unk_4c = f.read(12)
                keyframeCount = r_u32(f)
                
                keyframes = []

                for k in range(keyframeCount):      #Keyframe setup
                    time = r_f32(f)

                    translation = [triH.TangentXY(*struct.unpack(">4fI", f.read(20))) for _ in range(3)]                
                    rotation = [triH.TangentXY(*struct.unpack(">4fI", f.read(20))) for _ in range(3)]
                    scale = [triH.TangentXY(*struct.unpack(">4fI", f.read(20))) for _ in range(3)]

                    unk_b8 = f.read(60)
                    unk_f4 = f.read(60)
                    unk_130 = f.read(60)
                    unk_16c = f.read(60)

                    keyframes.append(animH.jointTransformAnimationKeyframe(time, translation, rotation, scale, unk_b8, unk_f4, unk_130, unk_16c))
                
                tracks.append(animH.jointTransformAnimationTableTrack(target_name, anim_origin, anim_rotation, anim_scale, obj_pos_delta, unk_34, unk_40, unk_4c, keyframeCount, keyframes))

            jointTransformAnimationTable = animH.animationTable(entryCount, entryOffsets, tracks)

    # ----- Material UV Animations
        if pMaterialUvAnimationTable != 0:
            f.seek(offs + pMaterialUvAnimationTable)
            entryOffsets = []
            tracks = []

            entryCount = r_u32(f)
            for t in range(entryCount):             #Track setup (Could technically be specified by making a new range(len(entryOffsets)) but it'd be redundant                
                trackOffset = r_u32(f)
                entryOffsets.append(trackOffset)

            for t, offset in enumerate(entryOffsets):
                f.seek(offs + offset)
                
                material_name = (read_string(f, (offs + r_u32(f))))
                samplerIndex = r_u32(f)
                skewX = r_f32(f)
                skewY = r_f32(f)
                keyframeCount = r_u32(f)

                keyframes = []

                for k in range(keyframeCount):      #Keyframe setup
                    time = r_f32(f)

                    translationX = triH.TangentXY(*struct.unpack(">4fI", f.read(20)))
                    translationY = triH.TangentXY(*struct.unpack(">4fI", f.read(20)))
                    scaleX = triH.TangentXY(*struct.unpack(">4fI", f.read(20)))
                    scaleY = triH.TangentXY(*struct.unpack(">4fI", f.read(20)))
                    rotateZ = triH.TangentXY(*struct.unpack(">4fI", f.read(20)))

                    keyframes.append(animH.materialUvAnimationKeyframe(time, translationX, translationY, scaleX, scaleY, rotateZ))

                tracks.append(animH.materialUvAnimationTableTrack(material_name, samplerIndex, skewX, skewY, keyframeCount, keyframes))

            materialUvAnimationTable = animH.animationTable(entryCount, entryOffsets, tracks)

    # ----- Material Blend Alpha Animations
        if pMaterialBlendAlphaAnimationTable != 0:
            f.seek(offs + pMaterialBlendAlphaAnimationTable)
            entryOffsets = []
            tracks = []

            entryCount = r_u32(f)
            for t in range(entryCount):
                trackOffset = r_u32(f)
                entryOffsets.append(trackOffset)

            for t, offset in enumerate(entryOffsets):
                f.seek(offs + offset)

                material_name = (read_string(f, (offs + r_u32(f))))
                keyframeCount = r_u32(f)

                keyframes = []

                for k in range(keyframeCount):
                    time = r_f32(f)
                    rgbaObjects = [triH.TangentXY(*struct.unpack(">4fI", f.read(20))) for _ in range(4)]

                    keyframes.append(animH.materialBlendAlphaAnimationKeyframe(time, rgbaObjects))
                tracks.append(animH.materialBlendAlphaAnimationTableTrack(material_name, keyframeCount, keyframes))
            materialBlendAlphaAnimationTable = animH.animationTable(entryCount, entryOffsets, tracks)

    # ----- Light (Transform) Animations
        if pLightTransformAnimationTable != 0:
            f.seek(offs + pLightTransformAnimationTable)
            entryOffsets = []
            tracks = []

            entryCount = r_u32(f)
            for t in range(entryCount):             #Track setup (Could technically be specified by making a new range(len(entryOffsets)) but it'd be redundant
                trackOffset = r_u32(f)
                entryOffsets.append(trackOffset)

            for t, offset in enumerate(entryOffsets):
                f.seek(offs + offset)
                
                light_name = (read_string(f, (offs + r_u32(f))))
                keyframeCount = r_u32(f)

                keyframes = []

                for k in range(keyframeCount):      #Keyframe setup
                    time = r_f32(f)

                    translation = [triH.TangentXY(*struct.unpack(">4fI", f.read(20))) for _ in range(3)]
                    rotation = [triH.TangentXY(*struct.unpack(">4fI", f.read(20))) for _ in range(3)]
                    scale = [triH.TangentXY(*struct.unpack(">4fI", f.read(20))) for _ in range(3)]

                    keyframes.append(animH.lightTransformAnimationKeyframe(time, translation, rotation, scale))

                tracks.append(animH.lightTransformAnimationTableTrack(light_name, keyframeCount, keyframes))

            lightTransformAnimationTable = animH.animationTable(entryCount, entryOffsets, tracks)
        
    # ----- Light (Parameter) Animations
        if pLightParameterAnimationTable != 0:
            f.seek(offs + pLightParameterAnimationTable)
            entryOffsets = []
            tracks = []

            entryCount = r_u32(f)
            for t in range(entryCount):             #Track setup (Could technically be specified by making a new range(len(entryOffsets)) but it'd be redundant
                trackOffset = r_u32(f)
                entryOffsets.append(trackOffset)

            for t, offset in enumerate(entryOffsets):
                f.seek(offs + offset)
                
                light_name = (read_string(f, (offs + r_u32(f))))
                keyframeCount = r_u32(f)

                keyframes = []

                for k in range(keyframeCount):      #Keyframe setup
                    time = r_f32(f)

                    color = [triH.TangentXY(*struct.unpack(">4fI", f.read(20))) for _ in range(3)]
                    spotAngle = triH.TangentXY(*struct.unpack(">4fI", f.read(20)))
                    angularAttenuation = triH.TangentXY(*struct.unpack(">4fI", f.read(20)))

                    keyframes.append(animH.lightParameterAnimationKeyframe(time, color, spotAngle, angularAttenuation))

                tracks.append(animH.lightParameterAnimationTableTrack(light_name, keyframeCount, keyframes))

            lightParameterAnimationTable = animH.animationTable(entryCount, entryOffsets, tracks)
        animations.append(
            animH.AnimBundle(
                name=name,
                lengthFrames=lengthFrames,
                joint=jointTransformAnimationTable,
                mat_uv=materialUvAnimationTable,
                mat_alpha=materialBlendAlphaAnimationTable,
                light_xform=lightTransformAnimationTable,
                light_param=lightParameterAnimationTable,
                )
            )
                
    animationData = mainH.VCDData(animationCount, animations)

        # ---------- Materials ----------
    material_name_table = tables["material_name_table"]
    material_data = material_name_table.data

    materials = []

    for m, mat in enumerate(material_data.materialNames):
        f.seek(offs + mat.offset)
        textureSamplerOffsets = []
        textureCoordTransforms = []
        textureSamplers = []

        name = (read_string(f, (offs + r_u32(f))))
        if name != mat.name:
            print(f"\n\nMaterial name mismatch!! Got {name} at idx: {m}.\nThat index in the mat_name_table is {mat.name}!")
        color = triH.ColorRGBA(*(f.read(4)))
        matSrc = r_1b(f)
        unk_009 = r_1b(f)
        blendMode = r_1b(f)
        numTextures = r_1b(f)
        for t in range(8):
            offset = r_u32(f)
            textureSamplerOffsets.append(offset)
        for t in range(8):
            translateX = r_f32(f)
            translateY = r_f32(f)
            scaleX = r_f32(f)
            scaleY = r_f32(f)
            rotateZ = r_f32(f)
            warpX = r_f32(f)
            warpY = r_f32(f)

            textureCoordTransforms.append(matH.texCoordTransforms(translateX, translateY, scaleX, scaleY, rotateZ, warpX, warpY))
        blendAlphaModulationR = triH.ColorRGBA(*(f.read(4)))
        pTevConfig = r_u32(f)
        for s in range(8):
            if textureSamplerOffsets[s] != 0:
                f.seek(offs + textureSamplerOffsets[s])

                textureOffset = r_u32(f)
                unk_04 = f.read(4)
                wrapS, wrapT = struct.unpack(">2B", f.read(2))
                unk_0a = r_1b(f) #Materials can't be transparent without this != 0. unsure of dif b/w 1/2
                unk_0b = r_1b(f)

                f.seek(offs + textureOffset)
                texName = (read_string(f, (offs + r_u32(f))))
                render_order = r_1b(f)
                unk_05 = f.read(1)
                unk_06 = f.read(1)
                unk_07 = f.read(1)
                wWidth, wHeight = struct.unpack(">2H", f.read(4))
                unk_0c = f.read(4)
                texture = matH.Texture(texName, render_order, unk_05, unk_06, unk_07, wWidth, wHeight, unk_0c)

                textureSamplers.append(matH.Sampler(textureOffset, unk_04, wrapS, wrapT, unk_0a, unk_0b, texture))
            else:
                textureSamplers.append(None)  
        f.seek(offs + pTevConfig)
        tevMode = r_1b(f)
        values = [2, 3, 4, 5, 6, 8]
        """if tevMode in values or tevMode > 8:
            print(fileName)
            print(f"tev catch: {name, tevMode}")"""
        unk_01 = f.read(1)
        unk_02 = f.read(1)
        unk_03 = f.read(1)
        unk_04 = f.read(4)
        unk_08 = f.read(4)
        tevConfig = matH.TEV(tevMode, unk_01, unk_02, unk_03, unk_04, unk_08)

        materials.append(objH.Material(mat.offset, name, color, matSrc, unk_009, blendMode, numTextures, textureSamplerOffsets, textureCoordTransforms, blendAlphaModulationR, pTevConfig, textureSamplers, tevConfig))

    materialData = mainH.VCDData(material_data.count, materials)

    return mainH.sceneData(positionData, normalData, colorData, textureCoordinateData, lightData, animationData, materialData)

def _read_node_common(f, fileName, base_off, node_off, data):
    """Reads the fields all nodes share; returns the relevant dataclass, and keeps file pointer sane."""
    f.seek(base_off + node_off)
    name = read_string(f, base_off + r_u32(f))
    type_ = read_string(f, base_off + r_u32(f))
    parentOffset = r_u32(f)
    childOffset  = r_u32(f)
    nextOffset   = r_u32(f)
    prevOffset   = r_u32(f)

    scale        = triH.XYZ(*struct.unpack(">3f", f.read(12)))
    rotation     = triH.XYZ(*struct.unpack(">3f", f.read(12)))
    translation  = triH.XYZ(*struct.unpack(">3f", f.read(12)))
    min_xyz      = triH.XYZ(*struct.unpack(">3f", f.read(12)))
    max_xyz      = triH.XYZ(*struct.unpack(">3f", f.read(12)))
    bbox         = triH.bbox(min_xyz, max_xyz)

    unk_54       = r_u32(f)
    unk_offset   = r_u32(f)
    meshCount    = r_u32(f)

    # Required “attributes” block
    f.seek(base_off + unk_offset)
    drawMode    = r_1b(f)


    """if drawMode > 3:
        print(fileName)
        print(f"draw catch: {name, drawMode}")"""

    cullMode    = r_1b(f)
    wFlags      = r_1b(f)
    padding     = f.read(1)
    lightMask   = r_u32(f)
    hitAttr     = r_u32(f)
    unk_0c      = f.read(4)
    unk_10      = f.read(4)
    attrs = mainH.attributes(
        drawMode=drawMode, cullMode=cullMode, wFlags=wFlags, padding=padding,
        lightMask=lightMask, hitAttributes=hitAttr, unk_0c=unk_0c, unk_10=unk_10
    )

    return mainH.NodeCommon(
    name=name,
    type=type_,
    parentOffset=parentOffset,
    childOffset=childOffset,
    nextOffset=nextOffset,
    prevOffset=prevOffset,
    scale=scale,
    rotation=rotation,
    translation=translation,
    bbox=bbox,
    unk_54=unk_54,
    unk_offset=unk_offset,
    meshCount=meshCount,
    attrs=attrs,
)

def find_mat_by_offs(data, materialOffset):
    for mat in data.materialData.values:
        if mat.offset == materialOffset:
            return mat

def _read_mesh_bits_if_any(f, base_off, node_off, info, data, tables, versionString: str | None = None):
    """Reads mesh descriptors & meshes if this node is a mesh; returns (mesh_descs, meshes)."""
    pos = f.tell()
    # Determine version (prefer explicit param; fallback to information table)
    if versionString is None:
        try:
            info_tbl = tables.get("information")
            versionString = getattr(getattr(info_tbl, "data", None), "versionString", None)
        except Exception:
            versionString = None

    use_global_vcd = (versionString == "ver1.02")

    try:
        mesh_descs = []
        meshes = []
        if info.type == "mesh" and info.meshCount > 0:
            # Re-seek to the end of the common node block
            f.seek(base_off + node_off + (
                4 + 4 +        # name ptr, type ptr
                4 * 4 +        # parent / child / next / prev
                12 * 3 +       # scale / rotation / translation
                12 * 2 +       # bbox min / max
                4 * 3          # unk_54, unk_offset, meshCount
            ))

            vcd_table = tables.get("vcd_table") if use_global_vcd else None
            vcd_data = vcd_table.data if vcd_table is not None else None

            for _ in range(info.meshCount):
                materialOffset = r_u32(f)
                meshOffset     = r_u32(f)

                material = find_mat_by_offs(data, materialOffset)
                mesh_header = read_mesh_header_and_polygon_table(
                    f, base_off, meshOffset
                )

                # Fallback: if no global vcd_table chunk, read per-mesh VCD table for vertex buffers.
                vertex_src = None
                if vcd_data is None:
                    vertex_src = _read_model_vcd_vertex_source(
                        f,
                        base_off,
                        mesh_header.vcdTableOffset,
                        packed=bool(mesh_header.bPolygonsAreDisplayLists),
                    )

                polygons = map_vcd_table_and_triangulate(
                    mesh_header,
                    data,
                    vcd_table=vcd_data,
                    vertex_src=vertex_src,
                )

                local_ir = build_local_mesh_ir(polygons)

                meshes.append(
                    objH.MeshEntry(
                        meshOffset=meshOffset,
                        material=material,
                        mesh_header=mesh_header,
                        vcd_table=(vcd_table.address if vcd_table is not None else mesh_header.vcdTableOffset),
                        polygons=polygons,
                        local_ir=local_ir,
                    )
                )

                mesh_descs.append(
                    mainH.meshDescriptor(materialOffset, meshOffset)
                )

        return mesh_descs, meshes

    finally:
        f.seek(pos)

@dataclass(frozen=True)
class LocalVertex:
    pos: Tuple[float, float, float]
    nrm: Tuple[float, float, float] | None
    uv0: Tuple[float, float] | None
    uv1: Tuple[float, float] | None
    col: Tuple[int, int, int, int] | None
    
@dataclass
class LocalPrimitive:
    opcode: int
    indices: List[int]

@dataclass
class LocalMeshIR:
    positions: list[tuple[float, float, float]]
    normals:   list[tuple[float, float, float] | None]
    colors:    list[tuple[int, int, int, int] | None]
    uv0s:      list[tuple[float, float] | None]
    uv1s:      list[tuple[float, float] | None]
    primitives: list[LocalPrimitive]

def build_local_mesh_ir(geom, eps=1e-6) -> LocalMeshIR:
    def q3(v):
        return (round(v[0]/eps)*eps, round(v[1]/eps)*eps, round(v[2]/eps)*eps)

    def as_uv(u):
        return None if u is None else (float(u[0]), float(u[1]))

    def as_col_u8(c):
        if c is None:
            return None
        # c is (0..1 floats) from prim_colors in your map func
        return tuple(int(round(max(0.0, min(1.0, x)) * 255.0)) for x in c)

    # IMPORTANT: use primitive streams
    src_pos = geom.prim_positions
    src_nrm = getattr(geom, "prim_normals", None)
    src_uv0 = getattr(geom, "prim_uvs0", None)
    src_uv1 = getattr(geom, "prim_uvs1", None)
    src_col = getattr(geom, "prim_colors", None)

    expected = sum(int(p.vertexCount) for p in geom.preserved_primitives)
    if expected != len(src_pos):
        raise RuntimeError(
            f"[LocalIR] Loop cursor mismatch: sum(prim vertexCount)={expected} "
            f"but len(prim_positions)={len(src_pos)}"
        )

    vertex_map: dict[LocalVertex, int] = {}
    positions, normals, colors, uv0s, uv1s = [], [], [], [], []
    primitives_out = []
    loop_cursor = 0

    for prim in geom.preserved_primitives:
        count = int(prim.vertexCount)
        local_indices = []

        for _ in range(count):
            pos = src_pos[loop_cursor]
            if pos is None:
                raise RuntimeError(
                    f"[LocalIR] None position at loop_cursor={loop_cursor} "
                    f"(prim opcode={hex(int(prim.opcode))}, prim vertexCount={count})"
                )
            nrm = src_nrm[loop_cursor] if src_nrm is not None else None
            col = src_col[loop_cursor] if src_col is not None else None
            uv0 = src_uv0[loop_cursor] if src_uv0 is not None else None
            uv1 = src_uv1[loop_cursor] if src_uv1 is not None else None

            key = LocalVertex(
                pos=q3(pos),
                nrm=tuple(nrm) if nrm is not None else None,
                uv0=as_uv(uv0),
                uv1=as_uv(uv1),
                col=as_col_u8(col),
            )

            idx = vertex_map.get(key)
            if idx is None:
                idx = len(positions)
                vertex_map[key] = idx
                positions.append(tuple(pos))
                normals.append(tuple(nrm) if nrm is not None else None)
                colors.append(as_col_u8(col))
                uv0s.append(as_uv(uv0))
                uv1s.append(as_uv(uv1))

            local_indices.append(idx)
            loop_cursor += 1

        assert len(local_indices) == count

        primitives_out.append(LocalPrimitive(opcode=int(prim.opcode), indices=local_indices))

    return LocalMeshIR(
        positions=positions,
        normals=normals,
        colors=colors,
        uv0s=uv0s,
        uv1s=uv1s,
        primitives=primitives_out
    )

def triangulate_resolved_vertices(op, verts):
    n = len(verts)
    tris = []

    def is_degenerate(a, b, c):
        # compare by position index (matches GX behavior)
        return (a.pi == b.pi) or (b.pi == c.pi) or (a.pi == c.pi)

    if op == 0x90:  # TRIANGLES
        for i in range(0, n, 3):
            if i + 2 >= n:
                break
            a, b, c = verts[i], verts[i + 1], verts[i + 2]
            if not is_degenerate(a, b, c):
                tris.append((a, b, c))

    elif op == 0x98:  # STRIP
        for i in range(n - 2):
            if i % 2 == 0:
                a, b, c = verts[i], verts[i + 1], verts[i + 2]
            else:
                a, b, c = verts[i + 1], verts[i], verts[i + 2]
            if not is_degenerate(a, b, c):
                tris.append((a, b, c))

    elif op == 0xA0:  # FAN
        if n < 3:
            return tris
        center = verts[0]
        for i in range(1, n - 1):
            a, b, c = center, verts[i], verts[i + 1]
            if not is_degenerate(a, b, c):
                tris.append((a, b, c))

    elif op == 0xB0:  # QUADS
        for i in range(0, n, 4):
            if i + 3 >= n:
                break
            a, b, c, d = verts[i], verts[i + 1], verts[i + 2], verts[i + 3]
            if not is_degenerate(a, b, c):
                tris.append((a, b, c))
            if not is_degenerate(a, c, d):
                tris.append((a, c, d))

    return tris

def map_vcd_table_and_triangulate(mesh, data, vcd_table=None,
                                 vertex_src: mainH.VertexSource | None = None,
                                 debug=False):
    # ---------------- Determine element usage early ----------------
    uses_tex1 = bool(getattr(mesh, "elementMask", 0) & VCD_TEX1)

    # ---------------- Pick sources ----------------
    if vertex_src is not None:
        pos_arr  = vertex_src.positions
        nrm_arr  = vertex_src.normals
        col0_arr = vertex_src.colors0
        uv0_arr  = vertex_src.uvs0
        uv1_arr  = getattr(vertex_src, "uvs1", None)  # if you have it
    else:
        pos_arr  = getattr(data.positionData, "values", None) if getattr(data, "positionData", None) is not None else None
        nrm_arr  = getattr(data.normalData, "values", None) if getattr(data, "normalData", None) is not None else None

        col0_arr = None
        uv0_arr  = None
        uv1_arr  = None

        cd = getattr(data, "colorData", None)
        if cd is not None:
            vals = getattr(cd, "values", None)
            if vals is not None:
                if isinstance(vals, (list, tuple)):
                    col0_arr = vals[0] if len(vals) > 0 else None
                else:
                    col0_arr = vals

        td = getattr(data, "textureCoordinateData", None)
        if td is not None:
            vals = getattr(td, "values", None)
            if vals is not None:
                if isinstance(vals, (list, tuple)):
                    uv0_arr = vals[0] if len(vals) > 0 else None
                    uv1_arr = vals[1] if len(vals) > 1 else None
                    if not uses_tex1:
                        uv1_arr = None
                else:
                    uv0_arr = vals

    # ---------------- Quantization shifts ----------------
    pos_shift = 0
    tex0_shift = 0
    tex1_shift = 0
    if vertex_src is not None:
        pos_shift = _clamp_shift(getattr(vertex_src, "pos_shift", 0) or 0)
        tex0_shift = _clamp_shift(getattr(vertex_src, "tex0_shift", 0) or 0)
        tex1_shift = _clamp_shift(getattr(vertex_src, "tex1_shift", 0) or 0)

        # Float buffers should not be divided
        if getattr(vertex_src, "pos_is_float", False):
            pos_shift = 0
        if getattr(vertex_src, "uv_is_float", False):
            tex0_shift = 0
            tex1_shift = 0

    elif vcd_table is not None:
        pos_shift = _clamp_shift(getattr(vcd_table, "positionQuantizationShift", 0) or 0)
        tex_shifts = getattr(vcd_table, "textureCoordinateQuantizationShift", None)
        if tex_shifts and len(tex_shifts) > 0:
            tex0_shift = _clamp_shift(tex_shifts[0] or 0)
            tex1_shift = _clamp_shift(
            (tex_shifts[1] if len(tex_shifts) > 1 else tex_shifts[0]) or 0
        )

    pos_div = float(1 << pos_shift) if pos_shift > 0 else 1.0
    tex0_div = float(1 << tex0_shift) if tex0_shift > 0 else 1.0
    tex1_div = float(1 << tex1_shift) if tex1_shift > 0 else tex0_div
    # ---------------- Safe reads / decoders ----------------
    def safe_get(arr, idx):
        if arr is None or idx == SENTINEL:
            return None
        try:
            # idx may come in as np scalar
            idx_i = int(idx)
        except Exception:
            return None
        if idx_i < 0 or idx_i >= len(arr):
            return None
        return arr[idx_i]

    def decode_pos(p):
        if p is None:
            return None
        if vertex_src is not None and getattr(vertex_src, "pos_is_float", False):
            return (float(p[0]), float(p[1]), float(p[2]))
        return (float(p[0]) / pos_div, float(p[1]) / pos_div, float(p[2]) / pos_div)

    def decode_nrm(n):
        if n is None:
            return None
        if vertex_src is not None and getattr(vertex_src, "nrm_is_float", False):
            return (float(n[0]), float(n[1]), float(n[2]))

        # Packed / fixedpoint behavior: normalize after scaling
        x = float(n[0]) / 64.0
        y = float(n[1]) / 64.0
        z = float(n[2]) / 64.0
        l = (x*x + y*y + z*z) ** 0.5
        if l > 1e-8:
            x, y, z = x / l, y / l, z / l
        return (x, y, z)

    def decode_col(c):
        if c is None:
            return None
        return (
            float(c[0]) / 255.0,
            float(c[1]) / 255.0,
            float(c[2]) / 255.0,
            float(c[3]) / 255.0,
        )

    def decode_uv0(uv):
        if uv is None:
            return None
        if vertex_src is not None and getattr(vertex_src, "uv_is_float", False):
            return (float(uv[0]), float(uv[1]))
        return (float(uv[0]) / tex0_div, float(uv[1]) / tex0_div)

    def decode_uv1(uv):
        if uv is None:
            return None
        if vertex_src is not None and getattr(vertex_src, "uv_is_float", False):
            return (float(uv[0]), float(uv[1]))
        return (float(uv[0]) / tex1_div, float(uv[1]) / tex1_div)

    # ---------------- LocalIR primitive-order streams ----------------
    prim_positions: list[tuple[float, float, float]] = []
    prim_normals:   list[tuple[float, float, float] | None] = []
    prim_uvs0:      list[tuple[float, float] | None] = []
    prim_uvs1:      list[tuple[float, float] | None] | None = [] if uses_tex1 else None
    prim_colors:    list[tuple[float, float, float, float] | None] = []

    # ---------------- Resolve per-polygon vertices ----------------
    mapped_tris = []
    preserved_primitives = []

    for polyinfo in getattr(mesh, "polygonInfo", []) or []:
        poly = polyinfo.data
        if not poly or not poly.vertices:
            continue

        # IMPORTANT: capture vertexCount exactly as stored
        preserved_primitives.append(
            PreservedPrimative(
                opcode=int(poly.drawOpcode),
                vertexCount=int(poly.vertexCount),
                # pos_indices optional; helpful for debugging only
                pos_indices=[int(v.positionIndex) for v in poly.vertices],
            )
        )

        resolved: list[objH.ResolvedVertex] = []

        for v in poly.vertices:
            if pos_arr is None:
                raise RuntimeError("[map_vcd] pos_arr is None (no position source selected)")
            
            p_raw = safe_get(pos_arr, v.positionIndex)
            if p_raw is None:
                raise RuntimeError(
                    f"[map_vcd] Missing POSITION index={int(v.positionIndex)} "
                    f"(meshOff={getattr(mesh, 'offset', '??')}, draw={hex(int(poly.drawOpcode))})"
                )

            n_raw   = safe_get(nrm_arr,  v.normalIndex)
            c_raw   = safe_get(col0_arr, v.colorIndex0)
            uv0_raw = safe_get(uv0_arr,  v.textureCoordinateIndex0)
            uv1_raw = safe_get(uv1_arr,  v.textureCoordinateIndex1) if (uses_tex1 and uv1_arr is not None) else None

            pos = decode_pos(p_raw)
            if pos is None:
                raise RuntimeError(
                    f"[map_vcd] decode_pos returned None for positionIndex={int(v.positionIndex)} "
                    f"(p_raw={p_raw}, meshOff={getattr(mesh,'offset','??')})"
                )
            nrm = decode_nrm(n_raw)
            clr = decode_col(c_raw)
            uv0 = decode_uv0(uv0_raw)
            uv1 = decode_uv1(uv1_raw) if uses_tex1 else None

            resolved.append(objH.ResolvedVertex(
                pi=int(v.positionIndex),
                pos=pos,
                nrm=nrm,
                clr=clr,
                uvs0=uv0,
                uvs1=uv1
            ))

            # Primitive stream append MUST be in poly.vertex order
            prim_positions.append(pos)
            prim_normals.append(nrm)
            prim_uvs0.append(uv0)
            if uses_tex1 and prim_uvs1 is not None:
                prim_uvs1.append(uv1)
            prim_colors.append(clr)

        tris = triangulate_resolved_vertices(int(poly.drawOpcode), resolved)
        if tris:
            mapped_tris.append(tris)

    # ---------------- Flatten to Blender-ready triangulated buffers ----------------
    # (keep your existing triangulated flatten; unchanged)
    # positions, normals, uvs0_list, uvs1_list, colors, polys, flat_pi

    # ---------------- Flatten to Blender-ready loop buffers ----------------
    positions: list[tuple[float, float, float]] = []
    normals:   list[tuple[float, float, float] | None] = []
    uvs0_list:  list[tuple[float, float] | None] = []
    uvs1_list:  list[tuple[float, float] | None] = [] if uses_tex1 else None
    colors:    list[tuple[float, float, float, float] | None] = []
    polys:     list[tuple[int, int]] = []

    has_real_uv1 = False
    loop_index = 0
    flat_pi: list[int] = []

    for tris in mapped_tris:
        for tri in tris:
            tri_start = loop_index
            for rv in tri:
                positions.append(rv.pos)
                flat_pi.append(rv.pi)
                normals.append(rv.nrm)
                uvs0_list.append(rv.uvs0)

                if uses_tex1:
                    uv1 = rv.uvs1
                    if uv1 is not None:
                        has_real_uv1 = True
                    uvs1_list.append(uv1)

                colors.append(rv.clr)
                loop_index += 1

            polys.append((tri_start, 3))

    # If no real UV1 data was found, drop the array to save space
    if not has_real_uv1:
        uvs1_list = None

    return objH.FlatGeometry(
        positions=positions,
        normals=normals,
        uvs0=uvs0_list,
        uvs1=uvs1_list,
        colors=colors,
        polys=polys,
        preserved_primitives=preserved_primitives,
        flat_pi=flat_pi,

        # ADD THESE:
        prim_positions=prim_positions,
        prim_normals=prim_normals,
        prim_uvs0=prim_uvs0,
        prim_uvs1=prim_uvs1,
        prim_colors=prim_colors,
    )

def read_mesh_header_and_polygon_table(f, base_off, mesh_off):
    pos = f.tell()
    try:
        f.seek(base_off + mesh_off)

        unk_00 = r_1b(f)
        unk_01 = r_1b(f)
        unk_02 = r_1b(f)
        bPolygonsAreDisplayLists = r_1b(f)

        polygonInfo = []

        if bPolygonsAreDisplayLists:
            # Packed display list table:
            # u32 polygonCount
            # u32 elementMask
            # u32 vcdTableOffset
            # polygonCount * (u32 offs, u32 size)
            polygonCount = r_u32(f)
            elementMask = r_u32(f)
            vcdTableOffset = r_u32(f)

            for _ in range(polygonCount):
                offs = r_u32(f)
                size = r_u32(f)
                poly = polyRead(f, base_off, offs, size, elementMask)
                polygonInfo.append(mainH.polygonInfo(offset=offs, size=size, data=poly))

        else:
            # Non-packed / part-table path (what your no-vcd_table map is using)
            # u32 partTableCount
            # u32 partTableCount2 (usually equal)
            # u32 vcdTableOffset (per mesh)
            # partTableCount * (u32 vertexDataOffs)
            partTableCount = r_u32(f)
            partTableCount2 = r_u32(f)
            vcdTableOffset = r_u32(f)

            # If these mismatch, we still try to continue safely.
            partCount = min(partTableCount, partTableCount2) if partTableCount2 else partTableCount

            for _ in range(partCount):
                vertexDataOffs = r_u32(f)
                poly = _part_vertex_block_as_polygon(f, base_off, vertexDataOffs)
                # size is deterministic here
                size = 4 + (poly.vertexCount * 0x18)
                polygonInfo.append(mainH.polygonInfo(offset=vertexDataOffs, size=size, data=poly))

            polygonCount = partCount
            elementMask = 0  # not used in this path

        return mainH.mesh(
            unk_00,
            unk_01,
            unk_02,
            bPolygonsAreDisplayLists,
            polygonCount,
            elementMask,
            vcdTableOffset,
            polygonInfo,
        )

    finally:
        f.seek(pos)

def polyRead(f, base_off, polyOffs, polySize, elementMask=None):
    """
    Safe polygon reader:
      - uses VCD elementMask to know which indices exist per-vertex
      - consumes any extra enabled attributes to keep stream aligned
    """
    if elementMask is None:
        elementMask = 0

    order = [
        (VCD_POS,  "pos"),
        (VCD_NRM,  "nrm"),
        (VCD_CLR0, "col0"),
        (VCD_CLR1, "col1"),
        (VCD_TEX0, "tex0"),
        (VCD_TEX1, "tex1"),
        (VCD_TEX2, "tex2"),
        (VCD_TEX3, "tex3"),
        (VCD_TEX4, "tex4"),
        (VCD_TEX5, "tex5"),
        (VCD_TEX6, "tex6"),
        (VCD_TEX7, "tex7"),
    ]

    pos_saved = f.tell()
    try:
        start = base_off + polyOffs
        f.seek(start)

        drawOpcode  = r_1b(f)
        vertexCount = r_2b(f) 

        vertices = []
        for _ in range(vertexCount):
            # Read all enabled indices (u16 each), in a stable order
            idx = {k: SENTINEL for _, k in order}
            for bit, key in order:
                if elementMask & bit:
                    idx[key] = r_2b(f)

            # Store only what vertice dataclass supports; discard the rest
            vertices.append(
                mainH.vertice(
                    positionIndex=idx["pos"],
                    normalIndex=idx["nrm"],
                    colorIndex0=idx["col0"],
                    textureCoordinateIndex0=idx["tex0"],
                    textureCoordinateIndex1=idx["tex1"]
                )
            )

        # Jump to the end of this polygon blob (handles padding safely)
        f.seek(start + polySize)

        return mainH.polygon(drawOpcode=drawOpcode, vertexCount=vertexCount, vertices=vertices)

    finally:
        f.seek(pos_saved)

def _read_node_recursive(f, fileName, base_off, node_off, data, tables, versionString: str | None = None):
    """Reads a node, then recurses its children (following the nextOffset chain)."""
    info = _read_node_common(f, fileName, base_off, node_off, data)

    mesh_descs, meshes = _read_mesh_bits_if_any(f, base_off, node_off, info, data, tables, versionString=versionString)

     # Walk children by following the nextOffset chain starting at childOffset
    children = []
    child_off = info.childOffset
    while child_off != 0:
        child_node = _read_node_recursive(f, fileName, base_off, child_off, data, tables, versionString=versionString)
        children.append(child_node)

        # advance via the child's own nextOffset
        child_off = child_node.nextOffset

    if info.type == "mesh":
        node = mainH.childMesh(
            name=info.name,
            type=info.type,
            parentOffset=info.parentOffset,
            childOffset=info.childOffset,
            nextOffset=info.nextOffset,
            prevOffset=info.prevOffset,
            scale=info.scale,
            rotation=info.rotation,
            translation=info.translation,
            bbox=info.bbox,
            unk_54=info.unk_54,
            unk_offset=info.unk_offset,
            meshCount=info.meshCount,
            meshDescriptors=mesh_descs,
            unk_data_mandatory=info.attrs,
            meshes=meshes,
        )
    else:
        node = mainH.childNull(
            name=info.name,
            type=info.type,
            parentOffset=info.parentOffset,
            childOffset=info.childOffset,
            nextOffset=info.nextOffset,
            prevOffset=info.prevOffset,
            scale=info.scale,
            rotation=info.rotation,
            translation=info.translation,
            bbox=info.bbox,
            unk_54=info.unk_54,
            unk_offset=info.unk_offset,
            meshCount=info.meshCount,
            unk_data_mandatory=info.attrs,
        )

    # Expose nextOffset so the parent loop can advance
    node.nextOffset = info.nextOffset
    node.children = children

    return node

def sceneGraph(f, fileName, offs, tables, data, versionString: str | None = None):
    root_off = tables["information"].data.sceneGraphRootOffset
    root = _read_node_recursive(f, fileName, offs, root_off, data, tables, versionString=versionString)
    return root