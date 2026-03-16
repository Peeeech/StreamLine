import os
import sys
from PIL import Image #type: ignore
import struct
import re
import numpy as np #type: ignore

TPL_FORMATS = {
    "I4": 0x00,
    "I8": 0x01,
    "IA4": 0x02,
    "IA8": 0x03,
    "RGB565": 0x04,
    "RGB5A3": 0x05,
    "RGBA32": 0x06,
    "CMPR": 0x0E,
}

def blender_image_to_pil(bl_img):
    """Convert bpy.types.Image pixels (float 0..1) to a PIL RGBA image."""
    w, h = bl_img.size
    ch = bl_img.channels

    # Blender stores pixels as a flat float array
    arr = np.asarray(bl_img.pixels[:], dtype=np.float32)
    arr = arr.reshape((h, w, ch))

    arr = np.flipud(arr)

    # Expand to RGBA in float space
    if ch == 4:
        rgba = arr
    elif ch == 3:
        a = np.ones((h, w, 1), dtype=np.float32)
        rgba = np.concatenate([arr, a], axis=2)
    elif ch == 2:
        # LA: intensity + alpha -> RGB=intensity, A=alpha
        I = arr[:, :, 0:1]
        A = arr[:, :, 1:2]
        rgb = np.repeat(I, 3, axis=2)
        rgba = np.concatenate([rgb, A], axis=2)
    elif ch == 1:
        I = arr[:, :, 0:1]
        rgb = np.repeat(I, 3, axis=2)
        a = np.ones((h, w, 1), dtype=np.float32)
        rgba = np.concatenate([rgb, a], axis=2)
    else:
        raise ValueError(f"Unsupported channel count: {ch}")

    rgba8 = np.clip(rgba * 255.0 + 0.5, 0, 255).astype(np.uint8)
    return Image.fromarray(rgba8, mode="RGBA")

def detect_format_pil(img_obj):
    """Same intent as detect_format(path), but operates on a PIL RGBA image."""
    img = img_obj.convert("RGBA")
    width, height = img.size
    pixels = list(img.getdata())

    has_alpha = False
    grayscale_values = set()
    alpha_values = set()
    rgb565_safe = True
    rgb5a3_safe = True
    grayscale_detected = True

    for r, g, b, a in pixels:
        if a < 255:
            has_alpha = True
            alpha_values.add(a)

        if r != g or g != b:
            grayscale_detected = False

        if grayscale_detected:
            grayscale_values.add(r)

        if r % 8 != 0 or g % 4 != 0 or b % 8 != 0:
            rgb565_safe = False

        if a < 255:
            if not all(is_close_to(v, 17, tolerance=8) for v in (a, r, g, b)):
                rgb5a3_safe = False
        else:
            if not all(is_close_to(v, 8, tolerance=8) for v in (r, g, b)):
                rgb5a3_safe = False

    if grayscale_detected:
        if has_alpha:
            if any(v % 17 != 0 for v in grayscale_values) or any(a % 17 != 0 for a in alpha_values):
                return "IA8"
            if len(grayscale_values) <= 16 and len(alpha_values) <= 16:
                return "IA4"
            return "IA8"
        else:
            if any(v % 17 != 0 for v in grayscale_values):
                return "I8"
            if len(grayscale_values) <= 16:
                return "I4"
            return "I8"

    if not has_alpha and rgb565_safe:
        return "RGB565"
    if rgb5a3_safe:
        if is_cmpr_compatible(pixels, width, height, debug=False):
            return "CMPR"
        return "RGB5A3"

    return "RGBA32"

def encode_pil_image(img_obj, fmt, idx, quality=False):    
    """
    Return encoded TPL image bytes for a PIL image.
    This is a refactor of your encode(...) branches without file IO.
    """

    img_path = None  # no file path; keep only if needed for debugging
    img = img_obj

    # ------------------------------------------------------------------
    # I4  (4‑bit intensity, 8×8 tiled, 32 bytes per tile)
    # ------------------------------------------------------------------
    if fmt == "I4":
        print(idx, img, fmt)
        img_obj = img.convert("L")   # 8‑bit grayscale
        width, height = img_obj.size
        gray_pixels = list(img_obj.getdata())

        tile_w, tile_h = 8, 8
        tiles_x = (width  + tile_w - 1) // tile_w
        tiles_y = (height + tile_h - 1) // tile_h

        encoded = bytearray()

        for ty in range(tiles_y):
            for tx in range(tiles_x):
                for row in range(tile_h):
                    iy = ty * tile_h + row
                    if iy >= height:
                        break
                    for col in range(0, tile_w, 2):          # 2 pixels per byte
                        ix0 = tx * tile_w + col
                        ix1 = ix0 + 1
                        if ix0 >= width:
                            break

                        # First pixel (high nibble)
                        I0 = gray_pixels[iy * width + ix0] if ix0 < width else 0
                        nib0 = max(0, min(15, round(I0 / 17)))   # 0‑15

                        # Second pixel (low nibble)
                        if ix1 < width and iy < height:
                            I1 = gray_pixels[iy * width + ix1]
                            nib1 = max(0, min(15, round(I1 / 17)))
                        else:
                            nib1 = 0

                        encoded.append((nib0 << 4) | nib1)

    # ------------------------------------------------------------------
    # I8  (8-bit intensity, 8×4 tiled, 32 bytes per tile)
    # ------------------------------------------------------------------
    elif fmt == "I8":
        print(idx, img, fmt)
        img_obj = img.convert("L")   # 8-bit grayscale
        width, height = img_obj.size
        gray_pixels = list(img_obj.getdata())

        tile_w, tile_h = 8, 4
        tiles_x = (width  + tile_w - 1) // tile_w
        tiles_y = (height + tile_h - 1) // tile_h

        encoded = bytearray()

        for ty in range(tiles_y):
            for tx in range(tiles_x):
                base_x = tx * tile_w
                base_y = ty * tile_h

                for row in range(tile_h):
                    iy = base_y + row
                    if iy >= height:
                        continue
                    for col in range(tile_w):
                        ix = base_x + col
                        if ix >= width:
                            break

                        # Raw grayscale 0–255
                        I = gray_pixels[iy * width + ix] if ix < width else 0
                        encoded.append(I)

    elif fmt == "IA4":
        print(idx, img, fmt)
        img_obj = img.convert("LA")
        width, height = img_obj.size
        gray_alpha_pixels = list(img_obj.getdata())

        tile_w, tile_h = 8, 4
        tiles_x = (width + tile_w - 1) // tile_w
        tiles_y = (height + tile_h - 1) // tile_h

        encoded = bytearray()
        for ty in range(tiles_y):
            for tx in range(tiles_x):
                for row in range(tile_h):
                    iy = ty * tile_h + row
                    if iy >= height:
                        break
                    for col in range(tile_w):
                        ix = tx * tile_w + col
                        if ix >= width:
                            break
                        I, A = gray_alpha_pixels[iy * width + ix]
                        i4 = max(0, min(15, round(I / 17)))
                        a4 = max(0, min(15, round(A / 17)))
                        encoded.append((a4 << 4) | i4)

    elif fmt == "IA8":
        print(idx, img, fmt)
        img_obj = img.convert("LA")
        width, height = img_obj.size
        pixels = img_obj.load()

        tile_w, tile_h = 4, 4
        tiles_x = (width + tile_w - 1) // tile_w
        tiles_y = (height + tile_h - 1) // tile_h

        encoded = bytearray()

        for ty in range(tiles_y):
            for tx in range(tiles_x):
                for row in range(tile_h):
                    iy = ty * tile_h + row
                    if iy >= height:
                        break
                    for col in range(tile_w):
                        ix = tx * tile_w + col
                        if ix >= width:
                            break
                        I, A = pixels[ix, iy]  # ← this is important: x, y
                        encoded.append(A)
                        encoded.append(I)

    elif fmt == "RGB5A3":
        print(idx, img, fmt)
        img_obj = img.convert("RGBA")
        width, height = img_obj.size
        rgba_pixels = list(img_obj.getdata())

        tile_w, tile_h = 4, 4
        tiles_x = (width + tile_w - 1) // tile_w
        tiles_y = (height + tile_h - 1) // tile_h

        encoded = bytearray()
        for ty in range(tiles_y):
            for tx in range(tiles_x):
                for row in range(tile_h):
                    iy = ty * tile_h + row
                    if iy >= height:
                        break
                    for col in range(tile_w):
                        ix = tx * tile_w + col
                        if ix >= width:
                            break
                        r, g, b, a = rgba_pixels[iy * width + ix]
                        if a < 255:
                            a4 = round(a / 17) & 0xF
                            r4 = round(r / 17) & 0xF
                            g4 = round(g / 17) & 0xF
                            b4 = round(b / 17) & 0xF
                            val = (a4 << 12) | (r4 << 8) | (g4 << 4) | b4
                        else:
                            r5 = round(r * 31 / 255) & 0x1F
                            g5 = round(g * 31 / 255) & 0x1F
                            b5 = round(b * 31 / 255) & 0x1F
                            val = 0x8000 | (r5 << 10) | (g5 << 5) | b5
                        encoded += struct.pack(">H", val)

    elif fmt == "CMPR":
        print(idx, img, fmt)
        img_obj = img.convert("RGBA")
        width, height = img_obj.size
        pixels = img_obj.load()

        encoded = bytearray()

        for by in range(0, height, 8):
            for bx in range(0, width, 8):
                for subblock_y in range(2):
                    for subblock_x in range(2):
                        block = []
                        for y in reversed(range(4)):
                            row = []
                            for x in reversed(range(4)):
                                px = bx + subblock_x * 4 + x
                                py = by + subblock_y * 4 + y
                                if px < width and py < height:
                                    row.append(pixels[px, py])
                                else:
                                    row.append((0, 0, 0, 0))  # transparent pad
                            block.append(row)
                        encoded += encode_cmpr_block(block, quality)

    elif fmt == "RGB565":
        print(idx, img, fmt)
        img_obj = img.convert("RGB")
        width, height = img_obj.size
        rgb_pixels = list(img_obj.getdata())

        tile_w, tile_h = 4, 4
        tiles_x = (width + tile_w - 1) // tile_w
        tiles_y = (height + tile_h - 1) // tile_h

        encoded = bytearray()
        for ty in range(tiles_y):
            for tx in range(tiles_x):
                for row in range(tile_h):
                    iy = ty * tile_h + row
                    if iy >= height:
                        break
                    for col in range(tile_w):
                        ix = tx * tile_w + col
                        if ix >= width:
                            break
                        r, g, b = rgb_pixels[iy * width + ix]
                        r5 = (r * 31 + 127) // 255
                        g6 = (g * 63 + 127) // 255
                        b5 = (b * 31 + 127) // 255
                        val = (r5 << 11) | (g6 << 5) | b5
                        encoded += struct.pack(">H", val)

    elif fmt == "RGBA32":
        print(idx, img, fmt)
        img_obj = img.convert("RGBA")
        width, height = img_obj.size
        rgba_pixels = list(img_obj.getdata())

        tile_w, tile_h = 4, 4
        tiles_x = (width + tile_w - 1) // tile_w
        tiles_y = (height + tile_h - 1) // tile_h

        encoded = bytearray()
        for ty in range(tiles_y):
            for tx in range(tiles_x):
                # GX RGBA32 stores a 4x4 tile as:
                # 16 pixels of (A,R) 16-bit words, then 16 pixels of (G,B) 16-bit words
                ar = bytearray()
                gb = bytearray()
                for row in range(tile_h):
                    iy = ty * tile_h + row
                    if iy >= height:
                        break
                    for col in range(tile_w):
                        ix = tx * tile_w + col
                        if ix >= width:
                            break
                        r, g, b, a = rgba_pixels[iy * width + ix]
                        ar += struct.pack(">BB", a, r)
                        gb += struct.pack(">BB", g, b)
                encoded += ar + gb

    else:
        print(f"\n\n{img}\n\n")
        return None
    
    return bytes(encoded)

def encode_blender_image(bl_img, idx, fmt=None, quality=False):
    """Primary entry point for Blender: returns (fmt_name, encoded_bytes)."""
    pil = blender_image_to_pil(bl_img)
    fmt_name = fmt or detect_format_pil(pil)
    encoded = encode_pil_image(pil, fmt_name, idx, quality=quality)
    return fmt_name, encoded

def natural_sort_key(text):
    return [int(t) if t.isdigit() else t.lower() for t in re.split(r'(\d+)', text)]

def is_close_to(val, step, tolerance=4): 
    """Lower tolerance assumes exact quantization logic; source tpl's will often result in this, 
    but custom images that weren't originally part of tpl's will likely cause problems without some leniency
    """
    return any(abs(val - (i * step)) <= tolerance for i in range(256 // step + 1))

def is_cmpr_compatible(pixels, width, height, debug):
    # CMPR encodes in 4x4 blocks, each with max 4 colors (2 base + 2 interpolated)
    for y in range(0, height, 4):
        for x in range(0, width, 4):
            colors = set()
            for j in range(4):
                for i in range(4):
                    ix = x + i
                    iy = y + j
                    if ix >= width or iy >= height:
                        continue
                    r, g, b, a = pixels[iy * width + ix]

                    # Alpha must be 0 or 255 in CMPR
                    if a not in (0, 255):
                        if debug:
                            print(f"\nBlock at ({x},{y}) failed: alpha={a} not 0 or 255\n")
                        return False

                    # Convert to RGB565 to determine uniqueness in CMPR space
                    rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                    colors.add(rgb565)

                    if len(colors) > 4:
                        if debug:
                            print(f"\nBlock at ({x},{y}) failed: {len(colors)} unique RGB565 colors\n")
                        return False
    return True


def detect_format(img_path):
    try:
        img = Image.open(img_path).convert("RGBA")
        width, height = img.size
        pixels = img.getdata()

        has_alpha = False
        grayscale_values = set()
        alpha_values = set()
        rgb565_safe = True
        rgb5a3_safe = True
        grayscale_detected = True

        for r, g, b, a in pixels:
            if a < 255:
                has_alpha = True
                alpha_values.add(a)

            if r != g or g != b:
                grayscale_detected = False

            if grayscale_detected:
                grayscale_values.add(r)

            if r % 8 != 0 or g % 4 != 0 or b % 8 != 0:
                rgb565_safe = False

            if a < 255:
                if not all(is_close_to(v, 17, tolerance=8) for v in (a, r, g, b)):
                    rgb5a3_safe = False
            else:
                if not all(is_close_to(v, 8, tolerance=8) for v in (r, g, b)):
                    rgb5a3_safe = False

        if grayscale_detected:
            if has_alpha:
                if any(v % 17 != 0 for v in grayscale_values) or any(a % 17 != 0 for a in alpha_values):
                    return "IA8"
                if len(grayscale_values) <= 16 and len(alpha_values) <= 16:
                    return "IA4"
                return "IA8"
            else:
                if any(v % 17 != 0 for v in grayscale_values):
                    return "I8"
                if len(grayscale_values) <= 16:
                    return "I4"
                return "I8"

        if not has_alpha and rgb565_safe:
            return "RGB565"
        if rgb5a3_safe:
            # Check CMPR after RGB5A3
            if is_cmpr_compatible(pixels, width, height, debug=False): #turn debug to True to make console prints for why an image didn't pass the CMPR check
                return "CMPR" #temp CMPR patch
            else:
                return "RGB5A3"

        return "RGBA32"

    except Exception as e:
        print(f"Error checking {img_path}: {e}")
        return "unknown"


def prep(folder_path, quality):
    data = []
    if not os.path.isdir(folder_path):
        print(f"Error: '{folder_path}' is not a valid directory.")
        return

    png_files = sorted(
        [f for f in os.listdir(folder_path) if f.lower().endswith('.png')],
        key=natural_sort_key
    )

    if not png_files:
        print("No .png files found in the directory.")
        return

    print(f"Found {len(png_files)} .png file(s):")
    for img in png_files:
        finalImage = None
        file_path = os.path.join(folder_path, img)
        fmt = detect_format(file_path)
        #print(img, fmt)

        finalImage = encode(img, fmt, folder_path, quality)
        if finalImage: 
            data.append(finalImage)

    return data

def encode(img, fmt, folder_path, quality):
    img_path = os.path.join(folder_path, img)

    # ------------------------------------------------------------------
    # I4  (4‑bit intensity, 8×8 tiled, 32 bytes per tile)
    # ------------------------------------------------------------------
    if fmt == "I4":
        print(img, fmt)
        img_obj = Image.open(img_path).convert("L")   # 8‑bit grayscale
        width, height = img_obj.size
        gray_pixels = list(img_obj.getdata())

        tile_w, tile_h = 8, 8
        tiles_x = (width  + tile_w - 1) // tile_w
        tiles_y = (height + tile_h - 1) // tile_h

        encoded = bytearray()

        for ty in range(tiles_y):
            for tx in range(tiles_x):
                for row in range(tile_h):
                    iy = ty * tile_h + row
                    if iy >= height:
                        break
                    for col in range(0, tile_w, 2):          # 2 pixels per byte
                        ix0 = tx * tile_w + col
                        ix1 = ix0 + 1
                        if ix0 >= width:
                            break

                        # First pixel (high nibble)
                        I0 = gray_pixels[iy * width + ix0] if ix0 < width else 0
                        nib0 = max(0, min(15, round(I0 / 17)))   # 0‑15

                        # Second pixel (low nibble)
                        if ix1 < width and iy < height:
                            I1 = gray_pixels[iy * width + ix1]
                            nib1 = max(0, min(15, round(I1 / 17)))
                        else:
                            nib1 = 0

                        encoded.append((nib0 << 4) | nib1)

    # ------------------------------------------------------------------
    # I8  (8-bit intensity, 8×4 tiled, 32 bytes per tile)
    # ------------------------------------------------------------------
    elif fmt == "I8":
        print(img, fmt)
        img_obj = Image.open(img_path).convert("L")   # 8-bit grayscale
        width, height = img_obj.size
        gray_pixels = list(img_obj.getdata())

        tile_w, tile_h = 8, 4
        tiles_x = (width  + tile_w - 1) // tile_w
        tiles_y = (height + tile_h - 1) // tile_h

        encoded = bytearray()

        for ty in range(tiles_y):
            for tx in range(tiles_x):
                base_x = tx * tile_w
                base_y = ty * tile_h

                for row in range(tile_h):
                    iy = base_y + row
                    if iy >= height:
                        continue
                    for col in range(tile_w):
                        ix = base_x + col
                        if ix >= width:
                            break

                        # Raw grayscale 0–255
                        I = gray_pixels[iy * width + ix] if ix < width else 0
                        encoded.append(I)

    elif fmt == "IA4":
        print(img, fmt)
        img_obj = Image.open(img_path).convert("LA")
        width, height = img_obj.size
        gray_alpha_pixels = list(img_obj.getdata())

        tile_w, tile_h = 8, 4
        tiles_x = (width + tile_w - 1) // tile_w
        tiles_y = (height + tile_h - 1) // tile_h

        encoded = bytearray()
        for ty in range(tiles_y):
            for tx in range(tiles_x):
                for row in range(tile_h):
                    iy = ty * tile_h + row
                    if iy >= height:
                        break
                    for col in range(tile_w):
                        ix = tx * tile_w + col
                        if ix >= width:
                            break
                        I, A = gray_alpha_pixels[iy * width + ix]
                        i4 = max(0, min(15, round(I / 17)))
                        a4 = max(0, min(15, round(A / 17)))
                        encoded.append((a4 << 4) | i4)

    elif fmt == "IA8":
        print(img, fmt)
        img_obj = Image.open(img_path).convert("LA")
        width, height = img_obj.size
        pixels = img_obj.load()

        tile_w, tile_h = 4, 4
        tiles_x = (width + tile_w - 1) // tile_w
        tiles_y = (height + tile_h - 1) // tile_h

        encoded = bytearray()

        for ty in range(tiles_y):
            for tx in range(tiles_x):
                for row in range(tile_h):
                    iy = ty * tile_h + row
                    if iy >= height:
                        break
                    for col in range(tile_w):
                        ix = tx * tile_w + col
                        if ix >= width:
                            break
                        I, A = pixels[ix, iy]  # ← this is important: x, y
                        encoded.append(A)
                        encoded.append(I)

    elif fmt == "RGB5A3":
        print(img, fmt)
        img_obj = Image.open(img_path).convert("RGBA")
        width, height = img_obj.size
        rgba_pixels = list(img_obj.getdata())

        tile_w, tile_h = 4, 4
        tiles_x = (width + tile_w - 1) // tile_w
        tiles_y = (height + tile_h - 1) // tile_h

        encoded = bytearray()
        for ty in range(tiles_y):
            for tx in range(tiles_x):
                for row in range(tile_h):
                    iy = ty * tile_h + row
                    if iy >= height:
                        break
                    for col in range(tile_w):
                        ix = tx * tile_w + col
                        if ix >= width:
                            break
                        r, g, b, a = rgba_pixels[iy * width + ix]
                        if a < 255:
                            a4 = round(a / 17) & 0xF
                            r4 = round(r / 17) & 0xF
                            g4 = round(g / 17) & 0xF
                            b4 = round(b / 17) & 0xF
                            val = (a4 << 12) | (r4 << 8) | (g4 << 4) | b4
                        else:
                            r5 = round(r * 31 / 255) & 0x1F
                            g5 = round(g * 31 / 255) & 0x1F
                            b5 = round(b * 31 / 255) & 0x1F
                            val = 0x8000 | (r5 << 10) | (g5 << 5) | b5
                        encoded += struct.pack(">H", val)

    elif fmt == "CMPR":
        print(img, fmt)
        img_obj = Image.open(img_path).convert("RGBA")
        width, height = img_obj.size
        pixels = img_obj.load()

        encoded = bytearray()

        for by in range(0, height, 8):
            for bx in range(0, width, 8):
                for subblock_y in range(2):
                    for subblock_x in range(2):
                        block = []
                        for y in reversed(range(4)):
                            row = []
                            for x in reversed(range(4)):
                                px = bx + subblock_x * 4 + x
                                py = by + subblock_y * 4 + y
                                if px < width and py < height:
                                    row.append(pixels[px, py])
                                else:
                                    row.append((0, 0, 0, 0))  # transparent pad
                            block.append(row)
                        encoded += encode_cmpr_block(block, quality)

    elif fmt == "RGB565":
        img_obj = img.convert("RGB")
        width, height = img_obj.size
        rgb_pixels = list(img_obj.getdata())

        tile_w, tile_h = 4, 4
        tiles_x = (width + tile_w - 1) // tile_w
        tiles_y = (height + tile_h - 1) // tile_h

        encoded = bytearray()
        for ty in range(tiles_y):
            for tx in range(tiles_x):
                for row in range(tile_h):
                    iy = ty * tile_h + row
                    if iy >= height:
                        break
                    for col in range(tile_w):
                        ix = tx * tile_w + col
                        if ix >= width:
                            break
                        r, g, b = rgb_pixels[iy * width + ix]
                        r5 = (r * 31 + 127) // 255
                        g6 = (g * 63 + 127) // 255
                        b5 = (b * 31 + 127) // 255
                        val = (r5 << 11) | (g6 << 5) | b5
                        encoded += struct.pack(">H", val)

    elif fmt == "RGBA32":
        img_obj = img.convert("RGBA")
        width, height = img_obj.size
        rgba_pixels = list(img_obj.getdata())

        tile_w, tile_h = 4, 4
        tiles_x = (width + tile_w - 1) // tile_w
        tiles_y = (height + tile_h - 1) // tile_h

        encoded = bytearray()
        for ty in range(tiles_y):
            for tx in range(tiles_x):
                # GX RGBA32 stores a 4x4 tile as:
                # 16 pixels of (A,R) 16-bit words, then 16 pixels of (G,B) 16-bit words
                ar = bytearray()
                gb = bytearray()
                for row in range(tile_h):
                    iy = ty * tile_h + row
                    if iy >= height:
                        break
                    for col in range(tile_w):
                        ix = tx * tile_w + col
                        if ix >= width:
                            break
                        r, g, b, a = rgba_pixels[iy * width + ix]
                        ar += struct.pack(">BB", a, r)
                        gb += struct.pack(">BB", g, b)
                encoded += ar + gb

    else:
        print(f"\n\n{img}\n\n")
        return None

    # --- TPL image header ---
    image_header = struct.pack(
    ">HHIIIIIIfBBBB",
    height,
    width,
    TPL_FORMATS[fmt],  # format
    0,                 # data_addr (placeholder, fill later)
    1, 1,              # wrap_s, wrap_t
    1, 1,              # min_filter, mag_filter
    0.0,               # lod_bias
    0, 0, 0,         # edge_lod_enable, min_lod, max_lod
    0               # unused padding byte
)



    return fmt, image_header, encoded

def rgb888_to_rgb565(r, g, b):
    r5 = (r * 31 + 127) // 255
    g6 = (g * 63 + 127) // 255
    b5 = (b * 31 + 127) // 255
    return (r5 << 11) | (g6 << 5) | b5

def rgb565_to_rgb888(rgb):
    r5 = (rgb >> 11) & 0x1F
    g6 = (rgb >> 5) & 0x3F
    b5 = rgb & 0x1F
    r = (r5 * 255 + 15) // 31
    g = (g6 * 255 + 31) // 63
    b = (b5 * 255 + 15) // 31
    return (r, g, b)


def encode_cmpr_block(block, quality):
    flat = [block[y][x] for y in range(4) for x in range(4)]

    # Fully transparent block
    if all(p[3] < 128 for p in flat):
        color0 = rgb888_to_rgb565(0, 0, 0)
        color1 = rgb888_to_rgb565(0, 0, 1)
        return struct.pack(">HHI", color0, color1, 0xFFFFFFFF)  # all index 3

    # Separate opaque & transparent
    opaque_pixels = [p[:3] for p in flat if p[3] >= 128]
    transparent_pixels_exist = any(p[3] < 128 for p in flat)

    if not opaque_pixels:
        opaque_pixels = [(0, 0, 0)]

    # Pick endpoints
    if quality:
        rgb565_colors = [rgb888_to_rgb565(*p) for p in opaque_pixels]
        rgb888_colors = [rgb565_to_rgb888(c) for c in rgb565_colors]
        max_dist = -1
        color0 = color1 = rgb565_colors[0]
        for i in range(len(rgb888_colors)):
            for j in range(i + 1, len(rgb888_colors)):
                dist = np.sum((np.array(rgb888_colors[i]) - np.array(rgb888_colors[j])) ** 2)
                if dist > max_dist:
                    max_dist = dist
                    color0 = rgb565_colors[i]
                    color1 = rgb565_colors[j]
    else:
        r_vals, g_vals, b_vals = zip(*opaque_pixels)
        max_rgb = (max(r_vals), max(g_vals), max(b_vals))
        min_rgb = (min(r_vals), min(g_vals), min(b_vals))
        color0 = rgb888_to_rgb565(*max_rgb)
        color1 = rgb888_to_rgb565(*min_rgb)

    # Force transparent mode if any pixel is transparent
    force_transparent_mode = transparent_pixels_exist
    if force_transparent_mode:
        if color0 >= color1:
            color0, color1 = color1, color0
    else:
        if color0 <= color1:
            color0, color1 = color1, color0

    # Build palette
    c0 = np.array(rgb565_to_rgb888(color0))
    c1 = np.array(rgb565_to_rgb888(color1))
    if color0 > color1:
        palette = [c0, c1, (2 * c0 + c1) // 3, (c0 + 2 * c1) // 3]
    else:
        palette = [c0, c1, (c0 + c1) // 2, np.array([0, 0, 0])]  # index 3 is transparent

    # Assign indices
    indices = 0
    for i, (r, g, b, a) in enumerate(flat):
        if a < 128:
            index = 3  # force index 3 if any transparency is in block
        else:
            color = np.array([r, g, b])
            dists = [np.sum((color - p) ** 2) for p in palette]
            index = int(np.argmin(dists))

            # Prevent accidentally assigning index 3 to opaque
            if color0 < color1 and index == 3:
                index = 0
        indices |= (index & 0x3) << (2 * i)

    return struct.pack(">HHI", color0, color1, indices)

def write_tpl(data, filename):
    output = bytearray()

    image_count = len(data)
    header_size = 0x0C
    table_size = image_count * 8
    image_headers_size = image_count * 0x24
    unaligned_offset = header_size + table_size + image_headers_size
    image_data_offset = (unaligned_offset + 0x1F) & ~0x1F  # align to next 0x20

    output += struct.pack(">I", 0x0020AF30)  # magic
    output += struct.pack(">I", image_count)
    output += struct.pack(">I", header_size)

    table_entries = []
    header_data = bytearray()
    image_data_blocks = []
    offset = image_data_offset

    for fmt, image_header, img_data in data:
        # Patch in correct data address offset
        patched_header = bytearray(image_header)
        struct.pack_into(">I", patched_header, 0x08, offset)
        header_data += patched_header

        # Image table entry: (header offset, palette offset = 0)
        table_entries.append(struct.pack(">II", header_size + table_size + len(header_data) - 0x24, 0))

        # Image data
        if fmt in ("I4", "I8", "IA4", "IA8", "RGB5A3", "CMPR", "RGB565", "RGBA32"):
            image_data_blocks.append(img_data)
        else:
            print(f"⚠️ Skipping unsupported format image data: {fmt}")
            ValueError(f"Unsupported format: {fmt}")

        offset += len(image_data_blocks[-1])

    # Add image table
    for entry in table_entries:
        output += entry

    # Add header data
    output += header_data

    # ✅ Padding between header section and image data
    padding_len = image_data_offset - len(output)
    output += b"\x00" * padding_len

    # Add image data
    for block in image_data_blocks:
        output += block

    with open(filename, "wb") as f:
        f.write(output)

    print(f"✅ Wrote {filename} with {image_count} image(s)")

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print("Usage: python detect_format.py <folder_path>")
        sys.exit(1)

    folder_path = sys.argv[1]
    raw_filename = folder_path
    quality  = False
    if len(sys.argv) == 3:
        raw_filename = sys.argv[2]

    if len(sys.argv) == 4:
        raw_filename = sys.argv[2]
        quality = sys.argv[3].lower() in ("true", "1", "yes")
        
    filename = raw_filename[:-1] if raw_filename.endswith("f") else raw_filename
    data = prep(folder_path, quality)
    write_tpl(data, filename)

    # ✅ Rename the folder to 'tex' after writing the TPL
    if os.path.basename(folder_path) != "tex":
        target = os.path.join(os.path.dirname(folder_path), "tex")
        try:
            if os.path.exists(target):
                print(f"⚠️ Folder 'tex' already exists. Skipping rename.")
            else:
                os.rename(folder_path, target)
                print(f"📁 Renamed '{folder_path}' → 'tex'")
        except Exception as e:
            print(f"❌ Failed to rename folder to 'tex': {e}")
