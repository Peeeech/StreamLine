# Format mappings
FORMATS = {
    'I4': 'I4', 
    'I8': 'I8', 
    'IA4': 'IA4',
    'IA8': 'IA8',
    'RGB565': 'RGB565',
    'RGB5A3': 'RGB5A3',
    'RGBA32': 'RGBA32',
    'C4': 'C4',
    'C8': 'C8',
    'C14X2': 'C14X2',
    'CMPR': 'CMPR',
}

# Constants for TPL file format
IMG_FMT_I4 = 0x00
IMG_FMT_I8 = 0x01
IMG_FMT_IA4 = 0x02
IMG_FMT_IA8 = 0x03
IMG_FMT_RGB565 = 0x04
IMG_FMT_RGB5A3 = 0x05
IMG_FMT_RGBA32 = 0x06
IMG_FMT_C4 = 0x08
IMG_FMT_C8 = 0x09
IMG_FMT_C14X2 = 0x0A
IMG_FMT_CMPR = 0x0E

# Mapping of image format constants to human-readable names
FORMAT_MAP = {
    IMG_FMT_I4: "I4",
    IMG_FMT_I8: "I8",
    IMG_FMT_IA4: "IA4",
    IMG_FMT_IA8: "IA8",
    IMG_FMT_RGB565: "RGB565",
    IMG_FMT_RGB5A3: "RGB5A3",
    IMG_FMT_RGBA32: "RGBA32",
    IMG_FMT_C4: "C4",
    IMG_FMT_C8: "C8",
    IMG_FMT_C14X2: "C14X2",
    IMG_FMT_CMPR: "CMPR"
}

PAL_FORMAT_MAP = {
    0x00: "I8",
    0x01: "RGB565",
    0x02: "RGB5A3",
}

# -----------------------------------------------------------------------------
#                           HELPER FUNCTIONS
# -----------------------------------------------------------------------------

# Convert a 16-bit RGB565 color to (R,G,B) or (R,G,B,A)
def rgb565_to_rgba(value: int) -> tuple[int, int, int, int]:
    r = (value >> 11) & 0x1F  # 5 bits
    g = (value >> 5 ) & 0x3F  # 6 bits
    b =  value        & 0x1F  # 5 bits

    # Scale to 0–255 with integer rounding
    R = (r * 255) // 31
    G = (g * 255) // 63
    B = (b * 255) // 31

    return (R, G, B, 255)

# ================================ PAL DECOMPRESSION ===========================
    # NOTE: Unused for maps unless a patch is made to use TLUT in TTYD
def decode_palette(raw_data, palette_format, entry_count):
    entries = []

    for i in range(entry_count):
        hi = raw_data[i*2]
        lo = raw_data[i*2 + 1]
        val = (hi << 8) | lo

        if palette_format == "IA8":
            A = (val >> 8) & 0xFF
            I = val & 0xFF
            entries.append((I, I, I, A))

        elif palette_format == "RGB565":
            r = ((val >> 11) & 0x1F) * 255 // 31
            g = ((val >> 5) & 0x3F) * 255 // 63
            b = (val & 0x1F) * 255 // 31
            entries.append((r, g, b, 255))

        elif palette_format == "RGB5A3":
            if val & 0x8000:
                r = ((val >> 10) & 0x1F) * 255 // 31
                g = ((val >> 5) & 0x1F) * 255 // 31
                b = (val & 0x1F) * 255 // 31
                a = 255
            else:
                a = ((val >> 12) & 0x7) * 255 // 7
                r = ((val >> 8) & 0xF) * 255 // 15
                g = ((val >> 4) & 0xF) * 255 // 15
                b = (val & 0xF) * 255 // 15
            entries.append((r, g, b, a))

    return entries

# ================================ I4 DECOMPRESSION ============================
def decode_I4(raw_data, height, width):
    """
    I4 => 4 bits/pixel, stored in 8×8 tiles => 32 bytes per tile.
    top nibble = first pixel, bottom nibble = second pixel
    Expand nibble (0..15) -> intensity (0..255) by multiplying by 17
    """
    tile_w = 8
    tile_h = 8
    bytes_per_tile = 32  # 8×8 => 64 px => 64 * 4 bits => 32 bytes

    tiles_x = (width  + tile_w - 1) // tile_w
    tiles_y = (height + tile_h - 1) // tile_h

    rgba = bytearray(width * height * 4)

    offset = 0
    for ty in range(tiles_y):
        for tx in range(tiles_x):
            # read 1 tile (8×8=64 px => 32 bytes)
            tile_data = raw_data[offset : offset + bytes_per_tile]
            offset += bytes_per_tile

            # unscramble within the tile
            pixel_i = 0
            for row in range(tile_h):
                iy = ty * tile_h + row
                if iy >= height:
                    break
                for col in range(tile_w):
                    ix = tx * tile_w + col
                    if ix >= width:
                        break

                    # each byte has 2 pixels
                    # so pixel_i // 2 => which byte
                    # shift => high nibble or low nibble
                    byte_i = pixel_i // 2
                    shift = 4 if (pixel_i & 1) == 0 else 0
                    val   = (tile_data[byte_i] >> shift) & 0xF
                    pixel_i += 1
                    I = val * 17

                    idx = (iy * width + ix) * 4
                    rgba[idx:idx+4] = (I, I, I, 255)

    return rgba

# ================================ I8 DECOMPRESSION ============================
def decode_I8(raw_data, height, width):
    """
    I8 => 8 bits/pixel, stored in 8×4 tiles => 8*4=32 px => 32 bytes/tile
    """

    tile_w = 8
    tile_h = 4
    bytes_per_tile = tile_w * tile_h  # = 32

    tiles_x = (width  + tile_w - 1) // tile_w
    tiles_y = (height + tile_h - 1) // tile_h

    rgba = bytearray(width * height * 4)

    offset = 0

    for ty in range(tiles_y):
        for tx in range(tiles_x):
            tile_data = raw_data[offset : offset+bytes_per_tile]
            offset += bytes_per_tile

            pixel_i = 0
            for row in range(tile_h):
                iy = ty*tile_h + row
                if iy >= height:
                    break
                for col in range(tile_w):
                    ix = tx*tile_w + col
                    if ix >= width:
                        break
                    val = tile_data[pixel_i]
                    pixel_i += 1
                    # I => grayscale
                    idx = (iy * width + ix) * 4
                    rgba[idx:idx+4] = (val, val, val, 255)

    return rgba

# ================================ IA4 DECOMPRESSION ===========================
def decode_IA4(raw_data, height, width):
    """
    Decode IA4 data stored in 8×4 tiles (typical GC/Wii layout).
    Each tile is 8 pixels wide, 4 pixels tall => 32 pixels => 32 bytes.

    IA4 layout in each byte:
      - High nibble = alpha   (0..15 => scale by 17 => 0..255)
      - Low  nibble = intensity (0..15 => scale by 17 => 0..255)
    """

    # Read all raw tile data

    # Compute how many tiles horizontally and vertically
    tile_w = 8
    tile_h = 4
    tiles_x = (width  + tile_w - 1) // tile_w   # round up if needed
    tiles_y = (height + tile_h - 1) // tile_h

    # Each tile is 8×4 => 32 bytes for IA4
    tile_size = tile_w * tile_h
    
    rgba = bytearray(width * height * 4)

    offset = 0

    # Loop over each tile in “reading order”
    # tile_y => row of tiles, tile_x => column of tiles
    for ty in range(tiles_y):
        for tx in range(tiles_x):
            # Process one 8×4 tile => 32 bytes
            tile_data = raw_data[offset : offset + tile_size]
            offset += tile_size

            # Write these 8×4 pixels into the final image
            # in row-major order *within* the tile
            pixel_i = 0
            for row in range(tile_h):
                # actual y in the final image
                iy = ty * tile_h + row
                if iy >= height:
                    break  # skip if tile goes beyond image

                for col in range(tile_w):
                    ix = tx * tile_w + col
                    if ix >= width:
                        break

                    val = tile_data[pixel_i]
                    pixel_i += 1

                    # top nibble => alpha
                    a_nib  = (val >> 4) & 0xF  # 0..15
                    # low nibble => intensity
                    i_nib  = val & 0xF        # 0..15

                    A = a_nib * 17
                    I = i_nib * 17

                    idx = (iy * width + ix) * 4
                    rgba[idx:idx+4] = (I, I, I, A)
    
    return rgba

# ================================ IA8 DECOMPRESSION ===========================
def decode_IA8(raw_data, height, width):

    tile_w = 4
    tile_h = 4
    bpp = 2
    tile_size = tile_w * tile_h * bpp  # 4×4×2=32

    tiles_x = (width  + tile_w - 1) // tile_w
    tiles_y = (height + tile_h - 1) // tile_h
    
    rgba = bytearray(width * height * 4)
    
    offset = 0

    for ty in range(tiles_y):
        for tx in range(tiles_x):
            tile_data = raw_data[offset:offset+tile_size]
            offset += tile_size
            pixel_i = 0
            for row in range(tile_h):
                iy = ty*tile_h + row
                if iy >= height:
                    break
                for col in range(tile_w):
                    ix = tx*tile_w + col
                    if ix >= width:
                        break
                    # read big-endian 16 bits
                    hi = tile_data[pixel_i]
                    lo = tile_data[pixel_i+1]
                    pixel_i += 2
                    val = (hi << 8) | lo
                    # top byte = alpha, low byte = intensity
                    A = (val >> 8) & 0xFF
                    I = val & 0xFF
                    
                    idx = (iy * width + ix) * 4
                    rgba[idx:idx+4] = (I, I, I, A)
    
    return rgba

# ================================ RGB565 DECOMPRESSION ========================
def decode_RGB565(raw_data, height, width):
    """
    RGB565 in 4×4 tiles => each tile = 16 pixels × 2 bytes = 32 bytes.
    Bits:
      bits 15..11 => R (0..31)
      bits 10..5  => G (0..63)
      bits 4..0   => B (0..31)
    We'll scale 5-bit channels up by (val*255)//31, 6-bit channel by (val*255)//63.
    """


    # tile is 4x4 => 16 pixels
    tile_w = 4
    tile_h = 4
    bytes_per_pixel = 2
    tile_size = tile_w * tile_h * bytes_per_pixel  # 16 * 2 = 32

    # how many tiles horizontally and vertically
    tiles_x = (width  + tile_w - 1) // tile_w
    tiles_y = (height + tile_h - 1) // tile_h
    
    rgba = bytearray(width * height * 4)

    offset = 0
    for ty in range(tiles_y):
        for tx in range(tiles_x):
            # read one 4x4 tile => 32 bytes
            tile_data = raw_data[offset : offset + tile_size]
            offset += tile_size

            pixel_i = 0
            for row in range(tile_h):
                iy = ty*tile_h + row
                if iy >= height:
                    break
                for col in range(tile_w):
                    ix = tx*tile_w + col
                    if ix >= width:
                        break

                    # read 16 bits big-endian
                    hi = tile_data[pixel_i]
                    lo = tile_data[pixel_i+1]
                    pixel_i += 2
                    val = (hi << 8) | lo

                    r = (val >> 11) & 0x1F
                    g = (val >> 5)  & 0x3F
                    b =  val        & 0x1F

                    R = (r * 255) // 31
                    G = (g * 255) // 63
                    B = (b * 255) // 31

                    idx = (iy * width + ix) * 4
                    rgba[idx:idx+4] = (R, G, B, 255)
    
    return rgba

# ================================ RGB5A3 DECOMPRESSION ========================
def decode_RGB5A3(raw_data, height, width):
    """
    RGB5A3 in 4×4 tiles => each tile = 16 pixels × 2 bytes = 32 bytes.
    If top bit == 0 => ARGB4444:
       bits 12..15 => alpha (0..15)
       bits  8..11 => red   (0..15)
       bits  4.. 7 => green (0..15)
       bits  0.. 3 => blue  (0..15)
    If top bit == 1 => RGB555:
       bits 10..14 => red   (0..31)
       bits  5.. 9 => green (0..31)
       bits  0.. 4 => blue  (0..31)
       alpha = 255
    """


    tile_w = 4
    tile_h = 4
    bytes_per_pixel = 2
    tile_size = tile_w * tile_h * bytes_per_pixel  # 16 px => 32 bytes

    tiles_x = (width  + tile_w - 1) // tile_w
    tiles_y = (height + tile_h - 1) // tile_h
    
    rgba = bytearray(width * height * 4)

    offset = 0
    for ty in range(tiles_y):
        for tx in range(tiles_x):
            # read 32 bytes for the 4×4 tile
            tile_data = raw_data[offset : offset + tile_size]
            offset += tile_size

            pixel_i = 0
            for row in range(tile_h):
                iy = ty * tile_h + row
                if iy >= height:
                    break
                for col in range(tile_w):
                    ix = tx * tile_w + col
                    if ix >= width:
                        break

                    hi = tile_data[pixel_i]
                    lo = tile_data[pixel_i+1]
                    pixel_i += 2
                    val = (hi << 8) | lo

                    if (val & 0x8000) == 0:
                        # ARGB4444
                        a = (val >> 12) & 0xF
                        r = (val >> 8)  & 0xF
                        g = (val >> 4)  & 0xF
                        b =  val        & 0xF
                        A = a * 17
                        R = r * 17
                        G = g * 17
                        B = b * 17
                    else:
                        # RGB555 => alpha=255
                        r = (val >> 10) & 0x1F
                        g = (val >> 5)  & 0x1F
                        b =  val        & 0x1F
                        A = 255
                        R = (r * 255) // 31
                        G = (g * 255) // 31
                        B = (b * 255) // 31

                    idx = (iy * width + ix) * 4
                    rgba[idx:idx+4] = (R, G, B, A)
    
    return rgba

# ================================ RGBA32 DECOMPRESSION ========================
def decode_RGBA32(raw_data, height, width):
    """
    GameCube/Wii RGBA32 (RGBA8) (GX_TF_RGBA8)

    Stored as 4x4 tiles (64 bytes each):

        First 32 bytes:
            A0 R0  A1 R1  ...

        Second 32 bytes:
            G0 B0  G1 B1  ...

    """

    tile_w = 4
    tile_h = 4
    tile_size = 64

    tiles_x = (width  + tile_w - 1) // tile_w
    tiles_y = (height + tile_h - 1) // tile_h

    rgba = bytearray(width * height * 4)

    offset = 0

    for ty in range(tiles_y):
        for tx in range(tiles_x):

            tile = raw_data[offset:offset + tile_size]
            offset += tile_size

            ar = tile[:32]
            gb = tile[32:]

            pixel = 0

            for row in range(tile_h):
                iy = ty * tile_h + row
                if iy >= height:
                    break

                for col in range(tile_w):
                    ix = tx * tile_w + col
                    if ix >= width:
                        break

                    A = ar[pixel * 2 + 0]
                    R = ar[pixel * 2 + 1]

                    G = gb[pixel * 2 + 0]
                    B = gb[pixel * 2 + 1]

                    idx = (iy * width + ix) * 4
                    rgba[idx:idx+4] = (R, G, B, A)

                    pixel += 1

    return rgba

# ================================ C4 DECOMPRESSION ============================
def decode_C4(raw_data, height, width, palette):
    tile_w = 8
    tile_h = 8
    tile_size = 32  # 8×8×4bpp = 32 bytes

    tiles_x = (width  + tile_w - 1) // tile_w
    tiles_y = (height + tile_h - 1) // tile_h

    rgba = bytearray(width * height * 4)

    offset = 0

    for ty in range(tiles_y):
        for tx in range(tiles_x):

            tile_data = raw_data[offset:offset + tile_size]
            offset += tile_size

            pixel_i = 0  # index into tile_data

            for row in range(tile_h):
                iy = ty * tile_h + row
                if iy >= height:
                    break

                for col in range(0, tile_w, 2):  # 2 pixels per byte
                    ix = tx * tile_w + col
                    if ix >= width:
                        break

                    byte = tile_data[pixel_i]
                    pixel_i += 1

                    # extract nibbles
                    hi = (byte >> 4) & 0xF
                    lo = byte & 0xF

                    # --- first pixel (high nibble) ---
                    idx0 = (iy * width + ix) * 4
                    if ix < width:
                        r, g, b, a = palette[hi]
                        rgba[idx0:idx0+4] = (r, g, b, a)

                    # --- second pixel (low nibble) ---
                    if ix + 1 < width:
                        idx1 = (iy * width + (ix + 1)) * 4
                        r, g, b, a = palette[lo]
                        rgba[idx1:idx1+4] = (r, g, b, a)

    return rgba

# ================================ C8 DECOMPRESSION ============================
def decode_C8(raw_data, height, width, palette):
    """
    8-bit color index => requires external palette.
    """
    tile_w = 8
    tile_h = 4
    tile_size = 32  # 8×4×1 byte = 32 bytes

    tiles_x = (width  + tile_w - 1) // tile_w
    tiles_y = (height + tile_h - 1) // tile_h

    rgba = bytearray(width * height * 4)

    offset = 0

    for ty in range(tiles_y):
        for tx in range(tiles_x):

            tile_data = raw_data[offset:offset + tile_size]
            offset += tile_size

            pixel_i = 0

            for row in range(tile_h):
                iy = ty * tile_h + row
                if iy >= height:
                    break

                for col in range(tile_w):
                    ix = tx * tile_w + col
                    if ix >= width:
                        break

                    index = tile_data[pixel_i]
                    pixel_i += 1

                    r, g, b, a = palette[index]

                    idx = (iy * width + ix) * 4
                    rgba[idx:idx+4] = (r, g, b, a)

    return rgba

# ================================ C14X2 DECOMPRESSION ========================
def decode_C14X2(raw_data, height, width, palette):
    """
    14-bit color index => also requires an external palette.
    """
    raise NotImplementedError("C14X2 not implemented. Why are you using this?")

# ================================ CMPR DECOMPRESSION ==============================

def decompress_cmpr_block(block):
    """
    Decompress a single 8-byte CMPR sub-block (4x4) into a 4x4 array of RGBA values.
    Uses standard DXT1 logic:
      - If c0 <= c1, the 4th color is fully transparent.
      - Otherwise (c0 > c1), you get 4 opaque colors.
    """
    c0 = int.from_bytes(block[:2], 'big')
    c1 = int.from_bytes(block[2:4], 'big')
    color_table = block[4:]

    # Decode the base colors
    rgba0 = rgb565_to_rgba(c0)  # (r,g,b,255)
    rgba1 = rgb565_to_rgba(c1)  # (r,g,b,255)
    #print(hex(c0), hex(c1), rgba0, rgba1)
    #print(hex(int.from_bytes(color_table, "big")))

    # Build the color palette for this block
    colors = [rgba0, rgba1]

    if c0 > c1:
        # 4 opaque colors
        # third color = 2/3 * col0 + 1/3 * col1
        # fourth color = 1/3 * col0 + 2/3 * col1
        colors.append((
            (2*rgba0[0] + rgba1[0]) // 3,
            (2*rgba0[1] + rgba1[1]) // 3,
            (2*rgba0[2] + rgba1[2]) // 3,
            255
        ))
        colors.append((
            (rgba0[0] + 2*rgba1[0]) // 3,
            (rgba0[1] + 2*rgba1[1]) // 3,
            (rgba0[2] + 2*rgba1[2]) // 3,
            255
        ))
    else:
        # c0 <= c1 => 3rd color = average of col0 & col1; 4th color = fully transparent
        colors.append((
            (rgba0[0] + rgba1[0]) // 2,
            (rgba0[1] + rgba1[1]) // 2,
            (rgba0[2] + rgba1[2]) // 2,
            255
        ))
        colors.append((0, 0, 0, 0))  # fully transparent

    # Now decode 4 rows of 2-bit indices
    # color_table[i] has 4 indices (2 bits each) for row i
    indices = int.from_bytes(color_table, "big")

    texels_4x4 = []
    for i in range(4):
        row = []
        for j in range(4):
            pixel_index = i * 4 + j
            shift = 30 - (pixel_index * 2)
            idx = (indices >> shift) & 0x03
            row.append(colors[idx])
        texels_4x4.append(row)

    return texels_4x4

def decode_CMPR(raw_data, height, width):
    """
    Decode the Nintendo-style CMPR (similar to DXT1) in '8x8 macro-blocks'.
    Each 8x8 is stored as four sub-blocks of 4x4, each 8 bytes.
    """
    import math

    rgba = bytearray(width * height * 4)

    macro_w = 8
    macro_h = 8
    blocks_wide = math.ceil(width / macro_w)
    blocks_high = math.ceil(height / macro_h)

    offset = 0
    # For each 8x8 macro-block
    for by in range(blocks_high):
        for bx in range(blocks_wide):
            # 4 sub-blocks in each 8x8
            for subb in range(4):
                sub_data = raw_data[offset : offset+8]
                offset += 8
                # Decompress the 4x4 block to RGBA
                block_4x4 = decompress_cmpr_block(sub_data)

                # subb=0 => top-left; subb=1 => top-right
                # subb=2 => bottom-left; subb=3 => bottom-right
                sub_y = (subb // 2) * 4
                sub_x = (subb % 2)  * 4

                # Place in final image
                top = by * macro_h
                left = bx * macro_w
                for row in range(4):
                    for col in range(4):
                        iy = top + sub_y + row
                        ix = left + sub_x + col
                        r, g, b, a = block_4x4[row][col]

                        idx = (iy * width + ix) * 4

                        if iy < height and ix < width:
                            idx = (iy * width + ix) * 4
                            rgba[idx:idx+4] = (r, g, b, a)

    return rgba

# ================================ ================= ==============================
# ================================ DECOMPRESSION END ==============================
# ================================ ================= ==============================

def get_format_function(format_str):
    # Return the decoding function based on the format string
    format_function_map = {
        'I4': decode_I4,
        'I8': decode_I8,
        'IA4': decode_IA4,
        'IA8': decode_IA8,
        'RGB565': decode_RGB565,
        'RGB5A3': decode_RGB5A3,
        'RGBA32': decode_RGBA32,
        'C4': decode_C4,
        'C8': decode_C8,
        'C14X2': decode_C14X2,
        'CMPR': decode_CMPR
    }

    return format_function_map.get(format_str)