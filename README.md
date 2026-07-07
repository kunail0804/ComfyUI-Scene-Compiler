# ComfyUI Scene Compiler

> Transform natural language into deterministic Illustrious prompts.

ComfyUI Scene Compiler is an experimental ComfyUI extension that converts natural language scene descriptions into structured prompts for Illustrious-based models.

Unlike traditional prompt generators, Scene Compiler does **not** try to imagine missing information.

Instead, it analyzes, validates and compiles a scene into a deterministic prompt.

---

## Why?

Most existing prompt generators follow this pipeline:

```
Natural Language
        │
        ▼
      LLM
        │
        ▼
 Illustrious Prompt
```

While simple, this approach often generates:

- hallucinated clothing
- invented backgrounds
- random camera angles
- fake emotions
- unnecessary quality tags
- inconsistent prompts

Scene Compiler follows another philosophy.

```
Natural Language
        │
        ▼
 Scene Analysis
        │
        ▼
 Scene JSON
        │
        ▼
 Resolver
        │
        ▼
 Validator
        │
        ▼
 Prompt Compiler
        │
        ▼
 Illustrious Prompt
```

The LLM is **never responsible** for creating Danbooru tags.

It only analyzes the scene.

---

# Philosophy

Scene Compiler behaves like a compiler.

Instead of generating prompts, it compiles them.

```
Text

↓

Semantic Analysis

↓

Intermediate Representation

↓

Validation

↓

Compilation

↓

Prompt
```

This makes the result:

- deterministic
- reproducible
- extensible
- debuggable

---

# Features

## Scene Analysis

Extract structured information from natural language.

Input

```
A blonde girl is holding a man's hand while walking under the rain.
```

Output

```json
{
    "characters":[
        {
            "gender":"female",
            "hair":"blonde"
        },
        {
            "gender":"male"
        }
    ],
    "interaction":[
        "holding hands",
        "walking"
    ],
    "environment":[
        "rain"
    ]
}
```

---

## Deterministic Resolver

Convert concepts into valid Illustrious tags.

Example

```
white dress
```

↓

```
white dress
```

---

```
holding someone's hand
```

↓

```
holding hands
```

---

## Validator

The validator ensures that:

- tags exist
- aliases are resolved
- categories are respected
- invalid concepts are rejected

The validator never invents tags.

---

## Category Splitter

Automatically routes tags into:

- Characters
- Hairstyles
- Clothing
- Eyes
- Expressions
- Interactions
- Camera
- Background
- Lighting
- Style
- Quality

Designed for EasyIllustrious workflows.

---

## Ollama Support

Runs locally.

Supports every Ollama compatible model.

Examples:

- Qwen
- Gemma
- Llama
- DeepSeek

---

# Roadmap

## Version 1

- Scene Analyzer
- Scene JSON
- Resolver
- Category Splitter
- Prompt Builder

---

## Version 2

- Knowledge Base
- Validator
- Alias Resolution
- Embedding Search
- Better Resolver

---

## Version 3

- Plugin Architecture
- Multiple Model Targets
- Interactive Debugger
- Advanced Knowledge Base

---

# Example

Input

```
A blonde girl hugs her boyfriend under the rain.
```

Output

```
Character

1girl

blonde hair

Character 2

1boy

Interaction

hug

Environment

rain

Prompt

1girl,
1boy,
blonde hair,
hug,
rain
```

---

# Project Goal

The long-term objective is to create the first deterministic prompt compiler dedicated to Danbooru-based image generation models.

Instead of asking an AI to imagine prompts, Scene Compiler transforms natural language into a structured scene representation before compiling it into a valid Illustrious prompt.

---

# Contributing

Contributions are welcome.

The project is still in its early stages and every idea is welcome.

Our primary objective is reliability rather than creativity.

**The compiler never invents.**

# IA Usage in the project

Pretty much everything from text to the code is done using IA. Maybe you don't like that and I understand but I am not qualified enough to understand how ComfyUI nodes works to create new ones and I lack in knowledge to know what a project like this needs. The idea is to use IA to learn as well as produce something usefull to me.
The text and brainstorming is done using GPT and the code is written using Claude Code with Opus 4.8.


**Sorry for my english this is not my primary language**
