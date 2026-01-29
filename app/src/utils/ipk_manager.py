############################################################
#
# https://github.com/PartyService/Ubiart-Archive-Tools
#
# UbiArt Archive Tools (IPK) is an useful scripts to extract or pack an .ipk
# 
# Original authors: Party Team, just gemer, Planedec50, leamsii, XpoZed, InvoxiPlayGames
#
############################################################
# MODIFICATION SUMMARY - Edited by Guasta, Jan 2026
#
# This file merges and improves the original ipk_packer.py and ipk_unpacker.py scripts:
# - Combines packing and extracting IPK into a single utility.
# - Standardizes headers, offsets, compression, and configuration.
# - Allows command-line usage for both operations.
# - Centralizes configuration and error handling.
# - Uses pathlib for better portability.
# - Removes code duplication and increases robustness.
#
############################################################

import numpy as np
import os
import sys
import struct
import zlib
import lzma
import json
import math
import re
from pathlib import PureWindowsPath, Path

# Define endianness as big endian
ENDIANNESS = '>'

# Define structure signs for various sizes
STRUCT_SIGNS = {
    1: 'c',
    2: 'H',
    4: 'I',
    8: 'Q'
}

# Define the structure of the IPK file header
IPK_HEADER = {
    'magic': 1357648570,      # Decimal integer value for b'\x50\xEC\x12\xBA'
    'version': 0,             # The Version of .ipks
    'platformsupported': 8,   # idk what this var is for
    'base_offset': 0,         # Initial raw file offset value (set to 0)
    'num_files': 0,           # Initialize the count of files (set to 0)
    'compressed': 0,          # is whole ipk compressed maybe??
    'binaryscene': 0,         # Set to 0
    'binarylogic': 0,         # Bundlelogic maybe??
    'datasignature': 0,       # Maybe For crc32 checksum?
    'enginesignature': 0,     # Game ID, to identify the games
    'engineversion': 0,       # Engine Version Of The game
    'num_files2': 0,          # idk why it's doubled?
}

DEFAULT_CONFIG = {
    'version': 5,
    'gameid': 490359856,
    'engineversion': 253653,
    'switchTitle': False,
    'compress': ['.dtape.ckd', '.fx.fxb', '.m3d.ckd', '.png.ckd', '.tga.ckd'],
    'method': 'zlib'
}


def _exit(msg, code=1):
    print(msg)
    sys.exit(code)


def unpack(_bytes):
    return struct.unpack(ENDIANNESS + STRUCT_SIGNS[len(_bytes)], _bytes)[0]


def get_file_header():
    return {
        'numOffset': {'size': 4},
        'size': {'size': 4},
        'compressed_size': {'size': 4},
        'time_stamp': {'size': 8},
        'offset': {'size': 8},
        'name_size': {'size': 4},
        'file_name': {'size': 0},
        'path_size': {'size': 4},
        'path_name': {'size': 4},
        'checksum': {'size': 4},
        'flag': {'size': 4}
    }


def shifter(a, b, c):
    d = np.uint32(0)
    a = np.uint32((a - b - c) ^ (c >> 0xd))
    b = np.uint32((b - a - c) ^ (a << 0x8))
    c = np.uint32((c - a - b) ^ (b >> 0xd))
    a = np.uint32((a - c - b) ^ (c >> 0xc))
    d = np.uint32((b - a - c) ^ (a << 0x10))
    c = np.uint32((c - a - d) ^ (d >> 0x5))
    a = np.uint32((a - c - d) ^ (c >> 0x3))
    b = np.uint32((d - a - c) ^ (a << 0xa))
    c = np.uint32((c - a - b) ^ (b >> 0xf))
    return a, b, c


def crc(data):
    np.seterr(all="ignore")
    a = np.uint32(0x9E3779B9)
    b = np.uint32(0x9E3779B9)
    c = np.uint32(0)
    length = len(data)

    if length > 0xc:
        i = 0
        while i < math.floor(length / 0xc):
            a += np.uint32((((((data[i * 0xc + 0x3] << 8) + data[i * 0xc + 0x2]) << 8) + data[i * 0xc + 0x1]) << 8) + data[i * 0xc])
            b += np.uint32((((((data[i * 0xc + 0x7] << 8) + data[i * 0xc + 0x6]) << 8) + data[i * 0xc + 0x5]) << 8) + data[i * 0xc + 0x4])
            c += np.uint32((((((data[i * 0xc + 0xb] << 8) + data[i * 0xc + 0xa]) << 8) + data[i * 0xc + 0x9]) << 8) + data[i * 0xc + 0x8])
            i += 1
            a, b, c = shifter(a, b, c)

    c += np.uint32(length)
    i = np.uint32(length - (length % 0xc))

    decide = (length % 0xc) - 1
    if decide >= 0xa:
        c += np.uint32(data[i + 0xa] << 0x18)
    if decide >= 0x9:
        c += np.uint32(data[i + 0x9] << 0x10)
    if decide >= 0x8:
        c += np.uint32(data[i + 0x8] << 0x8)
    if decide >= 0x7:
        b += np.uint32(data[i + 0x7] << 0x18)
    if decide >= 0x6:
        b += np.uint32(data[i + 0x6] << 0x10)
    if decide >= 0x5:
        b += np.uint32(data[i + 0x5] << 0x8)
    if decide >= 0x4:
        b += np.uint32(data[i + 0x4])
    if decide >= 0x3:
        a += np.uint32(data[i + 0x3] << 0x18)
    if decide >= 0x2:
        a += np.uint32(data[i + 0x2] << 0x10)
    if decide >= 0x1:
        a += np.uint32(data[i + 0x1] << 0x8)
    if decide >= 0x0:
        a += np.uint32(data[i + 0x0])

    a, b, c = shifter(a, b, c)

    return int(np.uint32(c))


# ============================================================================
# EXTRACT FUNCTION
# ============================================================================

def extract(target_file, output_dir=None):
    """
    Extract files from an IPK archive.
    
    Args:
        target_file: Path to the IPK file to extract
        output_dir: Output directory (optional, defaults to file stem)
    """
    with open(target_file, 'rb') as file:
        # Get file header information
        header = {}
        for k, v in enumerate(IPK_HEADER):
            size = 4  # IPK_HEADER values are always 4 bytes
            header[v] = file.read(size)

        # Check if this is a proper IPK file
        magic = struct.unpack(ENDIANNESS + STRUCT_SIGNS[4], header['magic'])[0]
        assert magic == 1357648570, "Invalid IPK file magic number"

        num_files = unpack(header['num_files'])
        print(f"Log: Found {num_files} files..")

        # Go through the file and collect the data
        file_chunks = []
        for _ in range(num_files):
            fHeader = get_file_header()
            for k, v in enumerate(fHeader):
                _size = fHeader[v]['size']

                if v == 'path_name':
                    _size = unpack(fHeader['path_size']['value'])
                if v == 'file_name':
                    _size = unpack(fHeader['name_size']['value'])

                fHeader[v]['value'] = file.read(_size)

            file_chunks.append(fHeader)

        # Create the directory for the extracted folders
        if output_dir:
            outputDir = Path(output_dir)
            outputDir.mkdir(exist_ok=True)
        else:
            outputDir = Path(target_file).stem if isinstance(target_file, str) else target_file.stem
            outputDir = Path(outputDir)
            outputDir.mkdir(exist_ok=True)

        print(f"Log: Extracting data to {outputDir.name} in {Path.cwd()}..")
        base_offset = unpack(header['base_offset'])

        for k, v in enumerate(file_chunks):
            # File raw data
            offset = unpack(file_chunks[k]['offset']['value'])
            data_size = unpack(file_chunks[k]['size']['value'])

            # File names and creation
            path_ori = file_chunks[k]['path_name']['value'].decode()
            if os.path.basename(path_ori) == path_ori:
                # Handling ipk v3, this applies to Just Dance 2014, Raymans Origins, Etc
                file_path = outputDir / file_chunks[k]['file_name']['value'].decode()
                file_name = file_chunks[k]['path_name']['value'].decode()
            else:
                # Handling ipk v4?? v5+, this applies to Just Dance 2015-2022, Child Of Lights, Etc
                file_path = outputDir / file_chunks[k]['path_name']['value'].decode()
                file_name = file_chunks[k]['file_name']['value'].decode()

            file.seek(offset + base_offset)

            # Make the sub directories
            file_path.mkdir(parents=True, exist_ok=True)

            # Inside the loop where you extract files
            with open(file_path / file_name, 'wb') as ff:
                readedFile = file.read(data_size)

                try:
                    # Try to decompress with zlib
                    decompressed_data = zlib.decompress(readedFile)
                    print(f"zlib: decompressing {file_name}    ", end="\r")
                except zlib.error:
                    try:
                        # Try to decompress with lzma
                        decompressed_data = lzma.decompress(readedFile)
                        print(f"lzma: decompressing {file_name}    ", end="\r")
                    except:
                        # If neither zlib nor lzma decompression works, use the original data
                        decompressed_data = readedFile

                ff.write(decompressed_data)

        print("\nLog: Extraction completed.")


# ============================================================================
# PACK FUNCTION
# ============================================================================

def pack(target_folder, output_ipk, config_data=None):
    """
    Pack files from a folder into an IPK archive.
    
    Args:
        target_folder: Path to the folder to pack
        output_ipk: Output IPK file path
        config_data: Configuration dictionary (optional, loads from config_ipk_packer.json if not provided)
    """
    if config_data is None:
        try:
            from .. import config
            config_path = config.CONFIG_IPK_PACKER
        except Exception:
            config_path = None

        if config_path and Path(config_path).exists():
            with open(config_path, 'r') as f:
                config_data = json.load(f)
        else:
            name = Path(config_path).name if config_path else "config_ipk_packer.json"
            print(f"Warning: {name} not found. Using internal defaults.")
            config_data = DEFAULT_CONFIG

    print(f"Packing {target_folder} using config: {config_data['method']}")

    # Collect file information
    file_info = []
    raw_data = b''
    offset = 0  # Initial offset value
    num_files = 0  # Initialize the count of files

    for root, _, files in os.walk(target_folder):
        for file_name in files:
            full_path = os.path.normpath(os.path.join(root, file_name))
            rel_path = os.path.normpath(os.path.relpath(root, target_folder))
            file_size = os.path.getsize(full_path)
            last_modified = int(os.path.getmtime(full_path))

            # If getmtime returns 0, use getctime instead
            if last_modified == 0:
                last_modified = int(os.path.getctime(full_path))

            if os.path.sep == '\\':
                rel_path = PureWindowsPath(rel_path).as_posix()

            if not rel_path.endswith('/') and rel_path != '':
                rel_path += '/'

            if rel_path == './':
                rel_path = ''

            if config_data.get('switchTitle') == True:
                tmp_path = rel_path
                tmp_name = file_name
                file_name = tmp_path
                rel_path = tmp_name
                
            with open(full_path, 'rb') as file:
                readedFile = file.read()
                if any(file_name.endswith(substring) for substring in config_data.get('compress', [])):
                    if config_data.get('method') == "lzma":
                        print(f"lzma: Compressing: {file_name}  ", end="\r")
                        file_data = lzma.compress(readedFile)
                    else:
                        print(f"zlib: Compressing: {file_name}  ", end="\r")
                        file_data = zlib.compress(readedFile)
                    origin_size = len(readedFile)
                    compressed_size = len(file_data)
                else:
                    file_data = readedFile
                    origin_size = len(readedFile)
                    compressed_size = 0
                raw_data += file_data

            flags = 0
            if file_name.endswith('.ckd'):
                flags = 2
            
            # Calculate name and path sizes
            name_size = len(file_name.encode())
            path_size = len(rel_path.encode())
            crcpath = f'{rel_path}{file_name}'.upper()
            stringID = crc(crcpath.encode())

            file_info.append({
                'file_name': file_name.encode(),
                'path_name': rel_path.encode(),
                'file_size': origin_size,
                'compressed_size': compressed_size,
                'time_stamp': last_modified,
                'offset': offset,
                'name_size': name_size,
                'path_size': path_size,
                'checksum': stringID,
                'flags': flags
            })

            # Update offset for the next file
            offset += len(file_data)
            num_files += 1

    # Calculate the total size of header and file info
    header_size = len(IPK_HEADER) * 4

    file_info_size = 0
    for file_data in file_info:
        file_info_size += 4  # Size of num_offset
        file_info_size += 4  # Size of file_size
        file_info_size += 4  # Size of compressed_size
        file_info_size += 8  # Size of time_stamp
        file_info_size += 8  # Size of offset
        file_info_size += 4  # Size of name_size
        file_info_size += len(file_data['file_name'])
        file_info_size += 4  # Size of path_size
        file_info_size += len(file_data['path_name'])
        file_info_size += 4  # Size of checksum
        file_info_size += 4  # Size of flag

    # Update header values
    header_values = IPK_HEADER.copy()
    header_values['base_offset'] = header_size + file_info_size
    header_values['num_files'] = num_files
    header_values['num_files2'] = num_files
    header_values['version'] = config_data.get('version', DEFAULT_CONFIG['version'])
    header_values['enginesignature'] = config_data.get('gameid', DEFAULT_CONFIG['gameid'])
    header_values['engineversion'] = config_data.get('engineversion', DEFAULT_CONFIG['engineversion'])

    with open(output_ipk, 'wb') as ipk_file:
        # Write the header
        for k, v in header_values.items():
            ipk_file.write(struct.pack(ENDIANNESS + STRUCT_SIGNS[4], v))

        # Write file chunks
        for file_data in file_info:
            ipk_file.write(struct.pack(ENDIANNESS + STRUCT_SIGNS[4], 1))
            ipk_file.write(struct.pack(ENDIANNESS + STRUCT_SIGNS[4], file_data['file_size']))
            ipk_file.write(struct.pack(ENDIANNESS + STRUCT_SIGNS[4], file_data['compressed_size']))
            ipk_file.write(struct.pack(ENDIANNESS + STRUCT_SIGNS[8], file_data['time_stamp']))
            ipk_file.write(struct.pack(ENDIANNESS + STRUCT_SIGNS[8], file_data['offset']))
            ipk_file.write(struct.pack(ENDIANNESS + STRUCT_SIGNS[4], file_data['name_size']))
            ipk_file.write(file_data['file_name'])
            ipk_file.write(struct.pack(ENDIANNESS + STRUCT_SIGNS[4], file_data['path_size']))
            ipk_file.write(file_data['path_name'])
            ipk_file.write(struct.pack(ENDIANNESS + STRUCT_SIGNS[4], file_data['checksum']))
            ipk_file.write(struct.pack(ENDIANNESS + STRUCT_SIGNS[4], file_data['flags']))

        # Write the raw data at the end of the file
        ipk_file.write(raw_data)

    print(f"\nLog: Packing completed to {output_ipk}.")


# ============================================================================
# CLI INTERFACE
# ============================================================================

if __name__ == "__main__":
    args = sys.argv

    if len(args) < 2:
        _exit("Usage: python ipk.py <operation> [args]\n"
              "Operations:\n"
              "  extract <ipk_file> [output_dir]  - Extract IPK file\n"
              "  pack <folder> <output_ipk>       - Pack folder into IPK")

    operation = args[1].lower()

    if operation == "extract":
        if len(args) < 3:
            _exit("Error: Please specify a target .IPK file to extract!")
        
        target_file = Path(args[2])
        if not target_file.exists():
            _exit(f"Error: The file '{target_file.name}' was not found!")
        
        output_dir = None if len(args) < 4 else args[3]
        extract(target_file, output_dir)
        _exit("Log: Extraction finished.", code=0)

    elif operation == "pack":
        if len(args) < 4:
            _exit("Error: Please specify a target folder to pack and the output IPK file!")
        
        target_folder = Path(args[2])
        if not target_folder.is_dir():
            _exit(f"Error: The folder '{target_folder}' does not exist or is not a directory!")
        
        output_ipk = args[3]
        pack(target_folder, output_ipk, config_data=None)
        _exit("Log: Packing finished.", code=0)

    else:
        _exit(f"Error: Unknown operation '{operation}'. Use 'extract' or 'pack'.")
