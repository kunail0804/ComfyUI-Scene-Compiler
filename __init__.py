"""ComfyUI Scene Compiler — ComfyUI custom node entry point.

ComfyUI loads this module by path and reads ``NODE_CLASS_MAPPINGS`` /
``NODE_DISPLAY_NAME_MAPPINGS`` to register the compiler's nodes. The mappings are
aggregated in the ``nodes`` package; the compiler logic lives entirely in the
``compiler`` package, which never imports ComfyUI.

The ``compiler`` and ``schemas`` packages are imported by their top-level names,
so this entry point puts the repository root on ``sys.path`` when ComfyUI loads it
by file path. The ``nodes`` package is only ever imported relative to this
package (never as a top-level ``nodes``), so it does not collide with ComfyUI's
own core ``nodes`` module.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # ComfyUI loads this file inside a package, so the relative import resolves.
    from .nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS
except ImportError:
    # Imported standalone (e.g. by the test runner): fall back to the top-level
    # package that is on sys.path.
    from nodes import NODE_CLASS_MAPPINGS, NODE_DISPLAY_NAME_MAPPINGS

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
