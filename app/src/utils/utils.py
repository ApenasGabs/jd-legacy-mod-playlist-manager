from pathlib import Path

def adjust_name_17(name):
    """Ensure 17 characters to maintain binary integrity."""
    clean_name = Path(name).stem
    return clean_name[:17].ljust(17, "0")
