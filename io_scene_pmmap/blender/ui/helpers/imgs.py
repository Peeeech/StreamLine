# Helpers from `encode.py` to find optimal format for img datablock creation
from PIL import Image
import numpy as np

TPL_FORMATS = {
    "I4": 0x00,
    "I8": 0x01,
    "IA4": 0x02,
    "IA8": 0x03,
    "RGB565": 0x04,
    "RGB5A3": 0x05,
    "RGBA32": 0x06,
    "C4": 0x08,
    "C8": 0x09,
    "CMPR": 0x0E,
}

def blender_image_to_pil(bl_img, max_size):
    """Convert bpy.types.Image pixels (float 0..1) to a PIL RGBA image."""
    w, h = bl_img.size
    _ = bl_img.pixels[:]
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
    pil_img = Image.fromarray(rgba8, mode="RGBA")

    if max(w, h) > max_size:
        scale = max_size / max(w, h)
        new_w = int(w * scale)
        new_h = int(h * scale)

        pil_img = pil_img.resize((new_w, new_h), Image.Resampling.BILINEAR)
    else:
        scale = 1

    return pil_img, scale


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


def detect_format(image):
    try:
        img = image.convert("RGBA")
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
        print(f"Error checking {img}: {e}")
        return "unknown"