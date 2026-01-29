
from pathlib import Path
import sys
import os


if __name__ == "__main__":
    base_dir = Path(__file__).parent
    dll_dir = base_dir / "dlls"
    # Add dlls folder to PATH so the exe finds all dependencies
    os.environ["PATH"] = str(dll_dir) + os.pathsep + os.environ.get("PATH", "")
    src_dir = base_dir / "src"
    sys.path.insert(0, str(src_dir))
    from app import run

    run()
