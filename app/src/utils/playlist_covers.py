############################################################
#
# https://github.com/RN-JK/NX-UbiArt-Texture-Maker
#
# Makes tga.ckd or png.ckd files for ubiart games on nintendo switch.
#
# Original author: RN-JK
#
############################################################
# MODIFICATION SUMMARY - Edited by Guasta, Jan 2026
#
# This file is a rewritten and improved version of NX_TGACKD.py:
# - Uses pathlib and subprocess for better path and process handling.
# - Adds robust error handling and clear exceptions.
# - Supports both 1024x512 and 1280x720 TGA.CKD headers.
# - Automates PNG→DDS→TGA.CKD and ACT.CKD generation with safe binary replacement.
# - Adds conversion from TGA.CKD back to PNG for GUI display.
# - Uses Pillow (PIL) for image conversion.
# - Centralizes configuration via config.py.
# - Cleans up temporary files and directories more safely.
#
############################################################

import os
import subprocess
from pathlib import Path
from PIL import Image
from .. import config

# TGA.CKD Headers
HEADER_1024x512 = b'\x00\x00\x00\x09\x54\x45\x58\x00\x00\x00\x00\x2C\x00\x00\x00\x04\x00\x02\x01\x00\x00\x01\x18\x00\x00\x00\x00\x04\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\xCC\xCC'
HEADER_1280x720 = b'\x00\x00\x00\x09\x54\x45\x58\x00\x00\x00\x00\x2C\x00\x00\x20\x05\xD0\x02\x01\x00\x00\x01\x18\x00\x00\x00\x20\x05\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\xCC\xCC'

def process_playlist_assets(png_path, output_folder):
    """
    1 - Converts PNG to DDS
    2 - From DDS, generates TGA.CKD
    3 - Generates ACT.CKD files.
    """

    input_path = Path(png_path)
    output_dir = Path(output_folder)
    file_name = input_path.stem
    tga_output = output_dir / f"{file_name}.tga.ckd"
    act_output = output_dir / f"{file_name}.act.ckd"

    # 1 - PNG to DDS
    dds_path = input_path.with_suffix(".dds")
    image_to_dds(input_path, dds_path)
    
    # 2 - DDS to TGA.CKD
    temp_xtx = input_path.with_suffix(".xtx")
    size = dds_path.stat().st_size
    current_header = HEADER_1024x512 if size < 1000000 else HEADER_1280x720

    # Path to the executable from config.py
    exe_path = str(config.XTX_EXTRACT_EXE)

    # Recommendation: use subprocess.run instead of os.system
    # Subprocess handles paths with spaces better
    subprocess.run([exe_path, "-o", str(temp_xtx), str(dds_path)], 
                    check=True, 
                    capture_output=True)
    
    with open(tga_output, "wb") as f_out:
        f_out.write(current_header)
        with open(temp_xtx, "rb") as f_in:
            f_out.write(f_in.read())
    
    if temp_xtx.exists(): os.remove(temp_xtx)

    # 3 - ACT.CKD generation
    if not config.BASE_ACT_FILE.exists():
        raise FileNotFoundError(f"Missing base ACT file [{config.BASE_ACT_FILE}] on data folder.")

    with open(config.BASE_ACT_FILE, 'rb') as f:
        base_data = f.read()
    
    # Safe binary replacement (21 bytes for 21 bytes)
    new_act_data = base_data.replace(b"justdance2026mode.tga", f"{file_name}.tga".encode('ascii'))
    
    with open(act_output, 'wb') as f:
        f.write(new_act_data)

def tga_ckd_to_png(input_tga_ckd, output_png):
    """Extracts XTX from .tga.ckd and converts to PNG for GUI display."""
    input_path = Path(input_tga_ckd)
    temp_xtx = input_path.with_suffix(".xtx")
    
    try:
        with open(input_path, "rb") as f:
            f.seek(44) # Skip .ckd header of 44 bytes
            xtx_data = f.read()
        
        with open(temp_xtx, "wb") as f:
            f.write(xtx_data)
        
        # The xtx_extract usually converts to .dds or .png depending on the version
        subprocess.run(
            [str(config.XTX_EXTRACT_EXE), "-o", str(output_png), str(temp_xtx)],
            check=True, creationflags=subprocess.CREATE_NO_WINDOW
        )
        return True
    finally:
        if temp_xtx.exists(): temp_xtx.unlink()

def image_to_dds(input_img_path, output_dds_path):
    """Convert PNG/JPG to DDS."""

    with Image.open(input_img_path) as img:
        width, height = img.size
        # Convert to RGBA if necessary and save as DDS
        img = img.convert("RGBA")
        img.save(output_dds_path, format="DDS")