"""ComfyUI node registrations for Scene Compiler.

Each node lives in its own module and is aggregated here into the
``NODE_CLASS_MAPPINGS`` / ``NODE_DISPLAY_NAME_MAPPINGS`` that ComfyUI reads.
Nodes are thin interfaces; all compiler logic lives in the ``compiler`` package.
"""

from __future__ import annotations

from .scene_analyzer_node import SceneAnalyzerNode

NODE_CLASS_MAPPINGS: dict[str, type] = {
    "SceneCompilerAnalyzer": SceneAnalyzerNode,
}

NODE_DISPLAY_NAME_MAPPINGS: dict[str, str] = {
    "SceneCompilerAnalyzer": "Scene Analyzer",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
