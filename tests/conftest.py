import sys
from pathlib import Path


_SRC_PATH = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(_SRC_PATH))
