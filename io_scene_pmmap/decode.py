import os
import sys
import numpy as np
from PIL import Image

# Global list to store image data as dictionaries
image_data_list = []
filesToDelete = []

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

# -----------------------------------------------------------------------------
#                           HELPER FUNCTIONS
# -----------------------------------------------------------------------------

def save_as_png(image_data, out_name):
    """
    Save a (H,W,4) RGBA NumPy array as a PNG using Pillow.
    """
    pil_img = Image.fromarray(image_data, mode='RGBA')
    pil_img.save(out_name)

def decode_and_save(image, filename, height, width):
    """
    Place common logic for saving the image as PNG.
    """
    output_dir = "tex"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    output_filename = f"{os.path.basename(filename).split('_')[0]}.png"
    output_filepath = os.path.join(output_dir, output_filename)
    save_as_png(image, output_filepath)

# Convert a 16-bit RGB565 color to (R,G,B) or (R,G,B,A)
def rgb565_to_rgba(value):
    r = (value >> 11) & 0x1F  # 5 bits
    g = (value >> 5 ) & 0x3F  # 6 bits
    b =  value        & 0x1F  # 5 bits

    # Scale to 0–255 with integer rounding
    R = (r * 255) // 31
    G = (g * 255) // 63
    B = (b * 255) // 31

    return (R, G, B, 255)

# ================================ I4 DECOMPRESSION ============================
def decode_I4(file, height, width):
    """
    I4 => 4 bits/pixel, stored in 8×8 tiles => 32 bytes per tile.
    top nibble = first pixel, bottom nibble = second pixel
    Expand nibble (0..15) -> intensity (0..255) by multiplying by 17
    """
    raw_data = file.read()
    tile_w = 8
    tile_h = 8
    bytes_per_tile = 32  # 8×8 => 64 px => 64 * 4 bits => 32 bytes

    tiles_x = (width  + tile_w - 1) // tile_w
    tiles_y = (height + tile_h - 1) // tile_h
    expected_size = tiles_x * tiles_y * bytes_per_tile
    if len(raw_data) < expected_size:
        raise ValueError("File too small for I4 tiled data")

    image = np.zeros((height, width, 4), dtype=np.uint8)

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
                    image[iy, ix] = (I, I, I, 255)

    # Save
    decode_and_save(image, file.name, height, width)

# ================================ I8 DECOMPRESSION ============================
def decode_I8(file, height, width):
    """
    I8 => 8 bits/pixel, stored in 8×4 tiles => 8*4=32 px => 32 bytes/tile
    """
    raw_data = file.read()

    tile_w = 8
    tile_h = 4
    bytes_per_tile = tile_w * tile_h  # = 32

    tiles_x = (width  + tile_w - 1) // tile_w
    tiles_y = (height + tile_h - 1) // tile_h
    expected_size = tiles_x * tiles_y * bytes_per_tile
    if len(raw_data) < expected_size:
        raise ValueError("File too small for I8 tiled data")

    image = np.zeros((height, width, 4), dtype=np.uint8)
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
                    image[iy, ix] = (val, val, val, 255)

    decode_and_save(image, file.name, height, width)

# ================================ IA4 DECOMPRESSION ===========================
def decode_IA4(file, height, width):
    """
    Decode IA4 data stored in 8×4 tiles (typical GC/Wii layout).
    Each tile is 8 pixels wide, 4 pixels tall => 32 pixels => 32 bytes.

    IA4 layout in each byte:
      - High nibble = alpha   (0..15 => scale by 17 => 0..255)
      - Low  nibble = intensity (0..15 => scale by 17 => 0..255)
    """

    # Read all raw tile data
    raw_data = file.read()

    # We'll store the final image as RGBA
    image = np.zeros((height, width, 4), dtype=np.uint8)

    # Compute how many tiles horizontally and vertically
    tile_w = 8
    tile_h = 4
    tiles_x = (width  + tile_w - 1) // tile_w   # round up if needed
    tiles_y = (height + tile_h - 1) // tile_h

    # Each tile is 8×4 => 32 bytes for IA4
    tile_size = tile_w * tile_h
    expected_size = tiles_x * tiles_y * tile_size
    if len(raw_data) < expected_size:
        raise ValueError("File too small for IA4 tiled data")

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

                    image[iy, ix] = (I, I, I, A)

    decode_and_save(image, file.name, height, width)

# ================================ IA8 DECOMPRESSION ===========================
def decode_IA8(file, height, width):
    raw_data = file.read()

    tile_w = 4
    tile_h = 4
    bpp = 2
    tile_size = tile_w * tile_h * bpp  # 4×4×2=32

    tiles_x = (width  + tile_w - 1) // tile_w
    tiles_y = (height + tile_h - 1) // tile_h
    expected_size = tiles_x * tiles_y * tile_size
    if len(raw_data) < expected_size:
        raise ValueError("File too small for IA8 tiled data")

    image = np.zeros((height, width, 4), dtype=np.uint8)
    offset = 0

    for ty in range(tiles_y):
        for tx in range(tiles_x):
            tile_data = raw_data[offset:offset+tile_size]
            offset += tile_size
            idx = 0
            for row in range(tile_h):
                iy = ty*tile_h + row
                if iy >= height:
                    break
                for col in range(tile_w):
                    ix = tx*tile_w + col
                    if ix >= width:
                        break
                    # read big-endian 16 bits
                    hi = tile_data[idx]
                    lo = tile_data[idx+1]
                    idx += 2
                    val = (hi << 8) | lo
                    # top byte = alpha, low byte = intensity
                    A = (val >> 8) & 0xFF
                    I = val & 0xFF
                    image[iy, ix] = (I, I, I, A)

    decode_and_save(image, file.name, height, width)

# ================================ RGB565 DECOMPRESSION ========================
def decode_RGB565(file, height, width):
    """
    RGB565 in 4×4 tiles => each tile = 16 pixels × 2 bytes = 32 bytes.
    Bits:
      bits 15..11 => R (0..31)
      bits 10..5  => G (0..63)
      bits 4..0   => B (0..31)
    We'll scale 5-bit channels up by (val*255)//31, 6-bit channel by (val*255)//63.
    """

    raw_data = file.read()

    # tile is 4x4 => 16 pixels
    tile_w = 4
    tile_h = 4
    bytes_per_pixel = 2
    tile_size = tile_w * tile_h * bytes_per_pixel  # 16 * 2 = 32

    # how many tiles horizontally and vertically
    tiles_x = (width  + tile_w - 1) // tile_w
    tiles_y = (height + tile_h - 1) // tile_h
    expected_size = tiles_x * tiles_y * tile_size
    if len(raw_data) < expected_size:
        raise ValueError("File too small for tiled RGB565 data")

    image = np.zeros((height, width, 4), dtype=np.uint8)

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
                    image[iy, ix] = (R, G, B, 255)

    # Save result
    decode_and_save(image, file.name, height, width)

# ================================ RGB5A3 DECOMPRESSION ========================
def decode_RGB5A3(file, height, width):
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

    raw_data = file.read()

    tile_w = 4
    tile_h = 4
    bytes_per_pixel = 2
    tile_size = tile_w * tile_h * bytes_per_pixel  # 16 px => 32 bytes

    tiles_x = (width  + tile_w - 1) // tile_w
    tiles_y = (height + tile_h - 1) // tile_h
    expected_size = tiles_x * tiles_y * tile_size
    if len(raw_data) < expected_size:
        raise ValueError("File too small for tiled RGB5A3 data")

    image = np.zeros((height, width, 4), dtype=np.uint8)

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

                    image[iy, ix] = (R, G, B, A)

    decode_and_save(image, file.name, height, width)

# ================================ RGBA32 DECOMPRESSION ========================
def decode_RGBA32(file, height, width):
    """
    RGBA32 => 4 bytes per pixel, stored in 4×4 tiles => 16 pixels => 64 bytes.
    We'll assume the layout is [R][G][B][A] in big-endian for each pixel.
    Some docs mention ARGB or other orders, so adjust as needed.
    """

    raw_data = file.read()

    tile_w = 4
    tile_h = 4
    bytes_per_pixel = 4
    tile_size = tile_w * tile_h * bytes_per_pixel  # 16 px => 64 bytes

    tiles_x = (width  + tile_w - 1) // tile_w
    tiles_y = (height + tile_h - 1) // tile_h
    expected_size = tiles_x * tiles_y * tile_size
    if len(raw_data) < expected_size:
        raise ValueError("File too small for tiled RGBA32 data")

    image = np.zeros((height, width, 4), dtype=np.uint8)

    offset = 0
    for ty in range(tiles_y):
        for tx in range(tiles_x):
            # read 64 bytes for one 4×4 tile
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

                    # read RGBA (4 bytes) in big-endian
                    R = tile_data[pixel_i + 0]
                    G = tile_data[pixel_i + 1]
                    B = tile_data[pixel_i + 2]
                    A = tile_data[pixel_i + 3]
                    pixel_i += 4

                    image[iy, ix] = (R, G, B, A)

    decode_and_save(image, file.name, height, width)

# ================================ C4 DECOMPRESSION ============================
def decode_C4(file):
    """
    4-bit color index => requires a separate palette to decode actual colors.
    Not implemented here because the palette is not given in the file alone.
    """
    raise NotImplementedError("C4 decoding requires external palette.")

# ================================ C8 DECOMPRESSION ============================
def decode_C8(file):
    """
    8-bit color index => also requires an external palette.
    """
    raise NotImplementedError("C8 decoding requires external palette.")

# ================================ C14X2 DECOMPRESSION ========================
def decode_C14X2(file):
    """
    14-bit color index => also requires an external palette.
    """
    raise NotImplementedError("C14X2 decoding requires external palette.")

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
    texels_4x4 = []
    for i in range(4):
        row = []
        row_val = color_table[i]
        for j in range(4):
            # extract 2 bits from row_val
            idx_shift = 6 - 2*j
            idx = (row_val >> idx_shift) & 0x03
            row.append(colors[idx])
        texels_4x4.append(row)

    return texels_4x4

def decode_CMPR(file, height, width):
    """
    Decode the Nintendo-style CMPR (similar to DXT1) in '8x8 macro-blocks'.
    Each 8x8 is stored as four sub-blocks of 4x4, each 8 bytes.
    """
    raw_data = file.read()

    # Output image has RGBA: shape=(height, width, 4)
    image = np.zeros((height, width, 4), dtype=np.uint8)

    macro_w = 8
    macro_h = 8
    blocks_wide = width  // macro_w
    blocks_high = height // macro_h

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
                        # Safety check
                        if iy < height and ix < width:
                            image[iy, ix] = block_4x4[row][col]

    decode_and_save(image, file.name, height, width)

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

# Main script
if __name__ == "__main__":
    directory = os.path.dirname(os.path.realpath(__file__))
    files = os.listdir(directory)

    for filename in files:
        if filename.startswith('i') and filename.count('_') == 3:
            parts = filename.split('_')
            if len(parts) == 4:
                img_index = int(parts[0][1:])
                height = int(parts[1])
                width = int(parts[2])
                format_str = parts[3]

                if format_str in FORMATS:
                    decode_func = get_format_function(format_str)
                    
                    if decode_func:
                        file_path = os.path.join(directory, filename)
                        filesToDelete.append(file_path)
                        with open(file_path, "rb") as file:
                            decode_func(file, height, width)
                    else:
                        print(f"No decoder function available for format {format_str}.")
                else:
                    print(f"Invalid format {format_str} found in {filename}.")
    for f in filesToDelete:
        try:
            os.remove(f)
        except OSError as e:
            print(f"Warning: Could not delete {f}: {e}")