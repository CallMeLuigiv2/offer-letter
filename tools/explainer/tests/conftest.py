import sys
from pathlib import Path

TOOL = Path(__file__).resolve().parent.parent
if str(TOOL) not in sys.path:
    sys.path.insert(0, str(TOOL))

FIXTURES = Path(__file__).resolve().parent / "fixtures"
