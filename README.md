# ComfyUI-Scene-Compiler
A collection of ComfyUI nodes to easily transfert NL into a tagged prompt.

## What is Scene Compiler?

Scene Compiler is an experimental ComfyUI extension that transforms natural language scene descriptions into structured Illustrious prompts.
Unlike traditional prompt generators, Scene Compiler does not try to "imagine" missing details.
Instead, it behaves like a compiler.
It:
- analyses the scene
- extracts semantic information
- validates concepts
- resolves aliases
- categorizes every element
- generates deterministic prompts
The objective is to eliminate hallucinations while producing prompts that integrate naturally with EasyIllustrious workflows.
