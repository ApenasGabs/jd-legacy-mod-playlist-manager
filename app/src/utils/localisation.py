############################################################
#
# https://github.com/wukko/ubiart-loc8-converter
#
# UbiArt localisation file converter by https://github.com/wukko
# Tested on Just Dance 2015 - 2022 games on PC, Wii, Wii U, Nintendo Switch (NX).
# This script should work for Rayman Legends/Origins and other UbiArt games too.
#
# This script requires passing parameters when used standalone. 
#
# Usage:
# py loc8Converter.py <mode> <input> <output>
#
# Modes:
# -d --decompress     Decompresses the loc8 file as JSON
# -c --compress       Compresses the file back to loc8 from JSON
# -p --patch          Patches the output JSON file with values in input JSON file
# 
# Credit to me (https://github.com/wukko) is required when this script is used in other projects.
#
############################################################
# MODIFICATION SUMMARY - Edited by Guasta, Jan 2026
#
# This file is a modified version of loc8Converter.py:
# - Patch mode (-p/--patch) and related code were removed; only decompress and compress modes are supported.
# - Added optional "legacy" argument to decompress and compress functions for compatibility with older formats (handles quotes differently).
# - Improved code readability and structure, including more descriptive function arguments and docstrings.
# - Updated usage instructions and help messages to reflect the new script name and available modes.
# - Minor changes in string handling for legacy compatibility.
# - Maintained all original decompress/compress logic for loc8 <-> JSON conversion.
# - Adds optional progress_callback hooks for compress/decompress progress reporting.
#
############################################################

import json

def decompress(input, output, legacy=False, progress_callback=None):
    with open(input, "rb") as f:
        j = {}
        f.seek(8)
        i = 0
        amountOfStrings = int.from_bytes(f.read(4), "big")
        while i != amountOfStrings:
            id = int.from_bytes(f.read(4), "big")
            value = f.read(int.from_bytes(f.read(4), "big")).decode("utf-8").replace("\x0A", "\n")
            if legacy:
                value = value.replace('"', '\\"')
            j[id] = value
            i = i + 1
            if progress_callback:
                try:
                    progress_callback(i, amountOfStrings, id)
                except Exception:
                    pass
    with open(output, "w", encoding="utf-8") as f:
        json.dump(j, f, ensure_ascii=False, separators=(',', ':'))

def compress(input, output, legacy=False, progress_callback=None):
    with open(output, "wb") as f:
        j = json.load(open(input, "r", encoding="utf-8"))
        f.write(b'\x00\x00\x00\x01\x00\x00\x00\x00')
        f.write(len(j).to_bytes(4, "big"))
        keys = list(j.keys())
        total = len(keys)
        for idx, i in enumerate(keys, start=1):
            raw = str(j[i])
            if legacy:
                raw = raw.replace('\\"', '"')
            string = raw.replace("\n", "\x0A").encode("utf-8")
            f.write(int(i).to_bytes(4, "big"))
            f.write(len(string).to_bytes(4, "big"))
            f.write(string)
            if progress_callback:
                try:
                    progress_callback(idx, total, i)
                except Exception:
                    pass
        f.write(b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x06\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF')

if __name__ == "__main__":
    import sys

    if len(sys.argv) == 4:
        mode = sys.argv[1]
        inputFile = sys.argv[2]
        outputFile = sys.argv[3]

        if mode == "-d" or mode == "--decompress":
            decompress(inputFile, outputFile)

        if mode == "-c" or mode == "--compress":
            compress(inputFile, outputFile)

    else:
        print('')
        print("This script requires passing parameters when used standalone.")
        print('')
        print("Usage:")
        print("python localisation.py <mode> <input> <output>")
        print('')
        print("Modes:")
        print("-d --decompress     Decompresses the loc8 file as JSON")
        print("-c --compress       Compresses the file back to loc8 from JSON")