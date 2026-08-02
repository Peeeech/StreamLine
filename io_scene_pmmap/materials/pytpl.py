import os
import sys
import shutil
from .decomp import decode

try:
    from PIL import Image
except Exception:
    print("Failed to import PIL. run `pip install pillow`.")
    sys.exit(1)

try:
    import numpy as np
except Exception:
    print("Failed to import numpy. run `pip install numpy`")
    sys.exit(1)

def clear_directory(path):
    if not os.path.exists(path):
        return

    for item in os.listdir(path):
        item_path = os.path.join(path, item)

        if os.path.isfile(item_path) or os.path.islink(item_path):
            os.unlink(item_path)
        elif os.path.isdir(item_path):
            shutil.rmtree(item_path)

#write helper
def writeImage(dir, i, image):
    format_type = decode.FORMAT_MAP.get(image.format)
    decode_func = decode.get_format_function(format_type)
    path = os.path.abspath(os.path.join(dir, f"i_{i}_{format_type}_{image.width}x{image.height}.png"))
    if not decode_func:
        return
    
    if decode_func not in [decode.decode_C4, decode.decode_C8, decode.decode_C14X2]:
        rgba = decode_func(image.raw_data, image.height, image.width)
        if rgba is None:
            print(f"what the fuck {i} {decode.FORMAT_MAP.get(image.format)}")
            sys.exit(1)

        img = Image.frombytes("RGBA", (image.width, image.height), bytes(rgba))
        img.save(path)

        print(f"Saved: {path}")
    else:
        print(f"Palette format detected: {format_type}")
        
        paletteRaw = image.palette
        palData = paletteRaw.data 
        entryLen = paletteRaw.count
        pal_format_type = decode.PAL_FORMAT_MAP.get(paletteRaw.format)

        palette = decode.decode_palette(palData, pal_format_type, entryLen)
        
        rgba = decode_func(image.raw_data, image.height, image.width, palette)
        if rgba is None:
            print(f"what the fuck {i} {image.format}")
            sys.exit(1)

        img = Image.frombytes("RGBA", (image.width, image.height), bytes(rgba))
        img.save(path)

        print(f"Saved: {path}")