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
# - Uses correct 1024x512 TGA.CKD header based on the original patch_nx.
# - Automates PNG→DDS→TGA.CKD with texconv (DXT5) and xtx_extract.
# - Generates ACT.CKD by updating name length, name string, and CRC32 from base template.
# - Adds conversion from TGA.CKD back to PNG for GUI display.
# - Uses Pillow (PIL) for image conversion.
# - Centralizes configuration via config.py.
# - Cleans up temporary files and directories more safely.
# - Adds optional progress_callback hooks for cover processing steps.
#
############################################################

import os
import re
import subprocess
import zlib
from pathlib import Path
from PIL import Image
from .. import config

# TGA.CKD Headers
HEADER_1024x512 = b'\x00\x00\x00\x09\x54\x45\x58\x00\x00\x00\x00\x2C\x00\x10\x00\x80\x08\x00\x04\x00\x00\x01\x18\x00\x00\x10\x00\x80\x00\x00\x00\x00\x00\x20\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
#HEADER_1280x720 = b'\x00\x00\x00\x09\x54\x45\x58\x00\x00\x00\x00\x2C\x00\x00\x20\x05\xD0\x02\x01\x00\x00\x01\x18\x00\x00\x00\x20\x05\x00\x00\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\xCC\xCC'

def process_playlist_assets(png_path, output_folder, progress_callback=None):
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

    # 1 - PNG to DDS (always 1024x512, 16-bit RGB565)
    dds_path = input_path.with_suffix(".dds")
    if progress_callback:
        try:
            progress_callback(1, 3, f"PNG→DDS: {input_path.name}")
        except Exception:
            pass
    image_to_dds(input_path, dds_path, progress_callback=progress_callback)
    
    # 2 - DDS to TGA.CKD
    temp_xtx = input_path.with_suffix(".xtx")
    with Image.open(input_path) as img:
        width, height = img.size
    if (width, height) == (1024, 512):
        current_header = HEADER_1024x512
    else:
        raise ValueError(f"Unsupported cover size: {width}x{height}. Expected 1024x512.")

    # Path to the executable from config.py
    exe_path = str(config.XTX_EXTRACT_EXE)

    # Recommendation: use subprocess.run instead of os.system
    # Subprocess handles paths with spaces better
    if progress_callback:
        try:
            progress_callback(2, 3, f"DDS→TGA.CKD: {input_path.name}")
        except Exception:
            pass
    subprocess.run([exe_path, "-o", str(temp_xtx), str(dds_path)], 
                    check=True, 
                    capture_output=True)
    
    with open(tga_output, "wb") as f_out:
        f_out.write(current_header)
        with open(temp_xtx, "rb") as f_in:
            f_out.write(f_in.read())
    
    if temp_xtx.exists(): os.remove(temp_xtx)

    # 3 - ACT.CKD generation
    # Keep existing ACT for known covers (they are unique per cover).
    if not act_output.exists():
        if not config.BASE_ACT_FILE.exists():
            raise FileNotFoundError(f"Missing base ACT file [{config.BASE_ACT_FILE}] on data folder.")

        with open(config.BASE_ACT_FILE, 'rb') as f:
            base_data = f.read()

        new_act_data = _build_act_bytes(base_data, f"{file_name}.tga".encode('ascii'))

        if progress_callback:
            try:
                progress_callback(3, 3, f"ACT.CKD: {input_path.name}")
            except Exception:
                pass
        with open(act_output, 'wb') as f:
            f.write(new_act_data)

def tga_ckd_to_png(input_tga_ckd, output_png, progress_callback=None):
    """Extracts XTX from .tga.ckd and converts to PNG for GUI display."""
    input_path = Path(input_tga_ckd)
    temp_xtx = input_path.with_suffix(".xtx")
    
    try:
        if progress_callback:
            try:
                progress_callback(1, 1, f"TGA.CKD→PNG: {input_path.name}")
            except Exception:
                pass
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

def image_to_dds(input_img_path, output_dds_path, progress_callback=None):
    """Convert PNG/JPG to DDS (DXT5/BC3) using texconv."""

    with Image.open(input_img_path) as img:
        width, height = img.size
        if (width, height) != (1024, 512) and (width, height) != (1280, 720):
            raise ValueError(f"Unsupported cover size: {width}x{height}. Expected 1024x512 or 1280x720.")

    if progress_callback:
        try:
            progress_callback(1, 1, f"DDS: {Path(str(input_img_path)).name}")
        except Exception:
            pass
    texconv = config.TEXCONV_EXE
    if not texconv.exists():
        raise FileNotFoundError(f"Missing texconv.exe at [{texconv}].")

    input_path = Path(input_img_path)
    out_dir = Path(output_dds_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # texconv writes to output directory using input filename
    subprocess.run(
        [str(texconv), "-f", "DXT5", "-m", "1", "-nologo", "-y", "-o", str(out_dir), str(input_path)],
        check=True,
        capture_output=True,
    )

    generated = out_dir / (input_path.stem + ".dds")
    if not generated.exists():
        generated = out_dir / (input_path.stem + ".DDS")
    if not generated.exists():
        raise FileNotFoundError(f"texconv did not generate DDS for [{input_path.name}]")

    target = Path(output_dds_path)
    if generated.resolve() != target.resolve():
        if target.exists():
            target.unlink()
        generated.rename(target)


def _build_act_bytes(base_data: bytes, new_tga_name: bytes) -> bytes:
    """Build ACT data from base by replacing the TGA name and CRC32."""
    if not new_tga_name or b".tga" not in new_tga_name:
        raise ValueError("Invalid TGA name for ACT generation.")

    m = re.search(rb"[A-Za-z0-9_]{3,}\.tga", base_data)
    if not m:
        raise ValueError("Base ACT file does not contain a .tga reference.")

    old_name = m.group(0)
    old_len = len(old_name)
    new_len = len(new_tga_name)

    data = bytearray(base_data)

    # Update length byte (immediately before the name) if needed
    len_pos = m.start() - 1
    if len_pos >= 0 and data[len_pos] == old_len:
        data[len_pos] = new_len

    # Replace name
    data[m.start():m.end()] = new_tga_name

    # Update CRC32 (most ACTs use crc32(name) in little endian)
    old_crc = zlib.crc32(old_name) & 0xFFFFFFFF
    new_crc = zlib.crc32(new_tga_name) & 0xFFFFFFFF
    old_crc_le = old_crc.to_bytes(4, "little")
    new_crc_le = new_crc.to_bytes(4, "little")
    crc_idx = data.find(old_crc_le)
    if crc_idx != -1:
        data[crc_idx:crc_idx + 4] = new_crc_le

    return bytes(data)