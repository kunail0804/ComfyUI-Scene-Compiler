"""ComfyUI Scene Compiler — ComfyUI custom node entry point.

ComfyUI loads this module by path and reads ``NODE_CLASS_MAPPINGS`` /
``NODE_DISPLAY_NAME_MAPPINGS`` to register the compiler's nodes. The mappings are
populated in Phase 5 when the nodes are implemented; until then they are empty so
that a fresh install imports cleanly without registering anything.

Compiler logic never lives here — it belongs in the ``compiler/`` package. This
file is an interface for ComfyUI only.
"""

# Populated by nodes/ in Phase 5 (issues #19–#26).
NODE_CLASS_MAPPINGS: dict[str, type] = {}
NODE_DISPLAY_NAME_MAPPINGS: dict[str, str] = {}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
