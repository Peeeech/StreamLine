import struct
import os
from typing import List, Tuple, Optional

try:
    from ..classes import tplH
except:
    from classes import tplH


# ------------------------------------------------------------
# Constants
# ------------------------------------------------------------

TPL_MAGIC  = 0x0020AF30
TPLX_MAGIC = 0x54504C78

IMG_FMT_I4      = 0x00
IMG_FMT_I8      = 0x01
IMG_FMT_IA4     = 0x02
IMG_FMT_IA8     = 0x03
IMG_FMT_RGB565  = 0x04
IMG_FMT_RGB5A3  = 0x05
IMG_FMT_RGBA32  = 0x06
IMG_FMT_C4      = 0x08
IMG_FMT_C8      = 0x09
IMG_FMT_C14X2   = 0x0A
IMG_FMT_CMPR    = 0x0E


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def _read_struct(f, fmt):
    size = struct.calcsize(fmt)
    data = f.read(size)
    if len(data) != size:
        raise EOFError("Unexpected EOF while reading TPL")
    return struct.unpack(fmt, data)


def _parse_header(f) -> tplH.TPLHeader:
    magic, count, imgtab_off = _read_struct(f, ">III")

    if magic not in (TPL_MAGIC, TPLX_MAGIC):
        raise ValueError(f"Invalid TPL magic: {hex(magic)}")

    return tplH.TPLHeader(
        magic=magic,
        image_count=count,
        image_table_offset=imgtab_off
    )


def _parse_image_header(f, offset):
    f.seek(offset)
    return _read_struct(
        f,
        ">HHIIIIIIfBBB"
    )
    # height, width, format, data_addr,
    # wrap_s, wrap_t, min_filter, mag_filter,
    # lod_bias, edge_lod_enable, min_lod, max_lod


# ------------------------------------------------------------
# Core parsing logic
# ------------------------------------------------------------

def parse_tpl(path: str) -> Tuple[tplH.TPLHeader, List[tplH.TPLImage]]:
    """
    Parse a single TPL/TPLX file and return (TPLHeader, [TPLImage]).
    """

    with open(path, "rb") as f:
        header = _parse_header(f)

        # Read image table
        f.seek(header.image_table_offset)
        entries = []
        for _ in range(header.image_count):
            img_off, pal_off = _read_struct(f, ">II")
            entries.append((img_off, pal_off))

        images: List[tplH.TPLImage] = []

        for i, (img_off, pal_off) in enumerate(entries):
            (
                height, width, fmt, data_addr,
                wrap_s, wrap_t,
                min_filter, mag_filter,
                lod_bias, edge_lod_enable,
                min_lod, max_lod
            ) = _parse_image_header(f, img_off)

            # Determine data end (MIRROR imageStream: next image's data_addr, not next img header offset)
            if i + 1 < header.image_count:
                # Look ahead: parse the NEXT image header to get its data_addr
                next_img_off, _ = entries[i + 1]
                _, _, _, next_data_addr, *_ = _parse_image_header(f, next_img_off)
                data_end = next_data_addr
            else:
                f.seek(0, os.SEEK_END)
                data_end = f.tell()

            f.seek(data_addr)
            raw_data = f.read(data_end - data_addr)

            images.append(
                tplH.TPLImage(
                    index=i,
                    width=width,
                    height=height,
                    format=fmt,
                    data_addr=data_addr,
                    raw_data=raw_data,
                    wrap_s=wrap_s,
                    wrap_t=wrap_t,
                    min_filter=min_filter,
                    mag_filter=mag_filter,
                    lod_bias=lod_bias,
                    edge_lod_enable=edge_lod_enable,
                    min_lod=min_lod,
                    max_lod=max_lod,
                    palette_addr=None if pal_off == 0 else pal_off,
                    palette_data=None 
                )
            )

        return header, images