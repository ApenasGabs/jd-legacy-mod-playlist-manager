from pathlib import Path
import sys

if __name__ == "__main__":
    src_dir = Path(__file__).parent / "src"
    sys.path.insert(0, str(src_dir))
    from app import run

    run()
