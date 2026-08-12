"""Where the modules under test live.

The harness is three files at the root; everything holding it up is in `rig/`,
which is deliberately not a package — a sandbox overwrites those files between
image build and launch, and an installed copy would shadow the fresh one. So
both directories go on the path here, once, rather than in eight test files.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for directory in (ROOT, ROOT / "rig"):
    sys.path.insert(0, str(directory))
