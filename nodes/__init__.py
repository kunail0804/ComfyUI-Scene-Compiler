"""ComfyUI node registrations for Scene Compiler.

Each node lives in its own module and is aggregated here into the
``NODE_CLASS_MAPPINGS`` / ``NODE_DISPLAY_NAME_MAPPINGS`` that ComfyUI reads.
Nodes are thin interfaces; all compiler logic lives in the ``compiler`` package.
"""

from __future__ import annotations

from .configuration_node import ConfigurationNode
from .debug_viewer_node import DebugViewerNode
from .knowledge_base_loader_node import KnowledgeBaseLoaderNode
from .resolver_node import ResolverNode
from .scene_analyzer_node import SceneAnalyzerNode
from .scene_validator_node import SceneValidatorNode

NODE_CLASS_MAPPINGS: dict[str, type] = {
    "SceneCompilerAnalyzer": SceneAnalyzerNode,
    "SceneCompilerValidator": SceneValidatorNode,
    "SceneCompilerResolver": ResolverNode,
    "SceneCompilerDebugViewer": DebugViewerNode,
    "SceneCompilerKnowledgeBaseLoader": KnowledgeBaseLoaderNode,
    "SceneCompilerConfiguration": ConfigurationNode,
}

NODE_DISPLAY_NAME_MAPPINGS: dict[str, str] = {
    "SceneCompilerAnalyzer": "Scene Analyzer",
    "SceneCompilerValidator": "Scene Validator",
    "SceneCompilerResolver": "Resolver",
    "SceneCompilerDebugViewer": "Debug Viewer",
    "SceneCompilerKnowledgeBaseLoader": "Knowledge Base Loader",
    "SceneCompilerConfiguration": "Configuration",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
