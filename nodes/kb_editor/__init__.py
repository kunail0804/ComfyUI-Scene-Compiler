"""Knowledge Base Editor: a standalone, off-critical-path KB contribution surface.

A small web UI (served on the ComfyUI server sub-route ``/scene-compiler/kb``) and
its backend API for creating/editing/deleting curated Knowledge Base entries with
live validation. The compiler never depends on this package; importing it must not
require ComfyUI.
"""
