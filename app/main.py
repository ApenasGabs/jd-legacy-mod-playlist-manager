
from pathlib import Path
import sys
import os


if __name__ == "__main__":
    base_dir = Path(__file__).parent
    bin_dir = base_dir / "bin"
    # If running as a frozen build, everything relevant is in bin
    if getattr(sys, "frozen", False):
        if bin_dir.exists():
            # Add bin to PATH and sys.path
            os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
            sys.path.insert(0, str(bin_dir))
            # Qt plugins
            os.environ["QT_PLUGIN_PATH"] = str(bin_dir)
            # Add lib/share if they exist
            for sub in ["lib", "share"]:
                subdir = bin_dir / sub
                if subdir.exists():
                    os.environ["PATH"] = str(subdir) + os.pathsep + os.environ["PATH"]
                    sys.path.insert(0, str(subdir))
    else:
        # Development: keep previous behavior
        if bin_dir.exists():
            os.environ["PATH"] = str(bin_dir) + os.pathsep + os.environ.get("PATH", "")
            os.environ["QT_PLUGIN_PATH"] = str(bin_dir)
        sys.path.insert(0, str(base_dir))
    # Import and run src.app.run
    from src.app import run
    run()
