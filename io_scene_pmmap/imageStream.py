import struct
import os
import sys
import subprocess
import numpy as np
import argparse
import tempfile

# Constants for TPL file format
TPL_MAGIC = 0x0020AF30
TPLX_MAGIC = 0x54504c78
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

# Helper function to read and unpack data (always big-endian)
def read_struct(file, fmt):
    size = struct.calcsize(fmt)
    data = file.read(size)
    if len(data) != size:
        raise ValueError(f"Failed to read {size} bytes from file.")
    return struct.unpack(fmt, data)

# Function to parse the TPL file header and extract texture information
def parse_tpl_header(file):
    magic, n_images, imgtab_off = read_struct(file, ">III")
    print(f"Magic number: {magic:08x}")
    print(f"Number of images: {n_images:08x} ({n_images})")
    print(f"Image table offset: {imgtab_off:08x}")
    
    if magic == TPL_MAGIC:
        print("TPL file format.")
    elif magic == TPLX_MAGIC:
        print("TPLx file format.")
    else:
        raise ValueError("Invalid TPL magic number.")
        
    return n_images, imgtab_off

# Function to parse the image header and extract relevant information (Height, Width, Format, etc.)
def parse_image_header(file, img_offset):
    file.seek(img_offset)
    height, width, format, data_addr, wrap_s, wrap_t, min_filter, mag_filter, lod_bias, edge_lod_enable, min_lod, max_lod = read_struct(file, ">HHIIIIIfBBBB")
    return height, width, format, data_addr, wrap_s, wrap_t, min_filter, mag_filter, lod_bias, edge_lod_enable, min_lod, max_lod

# Function to get image data for all images
def get_image_data(file, image_objects, n_images):
    for img_idx in range(n_images):
        current_image = image_objects[img_idx]
        if img_idx + 1 < n_images:
            next_image = image_objects[img_idx + 1]
            data_end = next_image["data_addr"]
        else:
            file.seek(0, os.SEEK_END)
            data_end = file.tell()

        data_addr = current_image["data_addr"]
        file.seek(data_addr)
        image_data = file.read(data_end - data_addr)
        current_image["image_data"] = image_data

        format_name = FORMAT_MAP.get(current_image["format"], "UnknownFormat")

        # Save image data as a new file
        output_filename = f"i-{img_idx + 1 }_{image_objects[img_idx]['height']}_{image_objects[img_idx]['width']}_{format_name}"
        with open(output_filename, "wb") as raw_file:
            #print(' '.join(f'{byte:02x}' for byte in image_data))
            raw_file.write(image_data)

# Main function to extract TPL to PNG
def extract_tpl_to_png(tpl_file):
    image_objects = []  # List to store image objects
    with open(tpl_file, "rb") as file:
        n_images, imgtab_off = parse_tpl_header(file)
        file.seek(imgtab_off)
        for img_idx in range(n_images):
            img_offset, palette_offset = read_struct(file, ">2I")
            #print(f"Image {img_idx + 1} header: {img_offset:08x}")
            
            if palette_offset != 0x00000000:
                print(f"TODO:  Palette header: {palette_offset:08x}")
            
            height, width, format, data_addr, wrap_s, wrap_t, min_filter, mag_filter, lod_bias, edge_lod_enable, min_lod, max_lod = parse_image_header(file, img_offset)
            
            image_objects.append({
                "height": height,
                "width": width,
                "format": format,
                "data_addr": data_addr,
                "wrap_s": wrap_s,
                "wrap_t": wrap_t,
                "min_filter": min_filter,
                "mag_filter": mag_filter,
                "lod_bias": lod_bias,
                "edge_lod_enable": edge_lod_enable,
                "min_lod": min_lod,
                "max_lod": max_lod,
            })
        
            file.seek(imgtab_off + (img_idx + 1) * 8)  # 8 bytes per image entry in the table
        
        get_image_data(file, image_objects, n_images)
        
        subprocess.run(["python", "decode.py"])

# Script execution with argparse
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract images from a TPL file and save as PNGs.")
    parser.add_argument("tpl_file", type=str, help="The TPL file to extract images from.")
    args = parser.parse_args()

    tpl_file = args.tpl_file
    if not os.path.exists(tpl_file):
        print(f"Error: The file {tpl_file} does not exist.")
        sys.exit(1)

    extract_tpl_to_png(tpl_file)
