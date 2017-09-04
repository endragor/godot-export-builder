Python script for assembling Godot 3.0 export templates from the engine's source code.

Prerequisites:

- Python 2.7
- Godot 3+
- Prerequisites of the specific platform you are building export templates for (check out [Godot's documentation](https://godot.readthedocs.io/en/stable/development/compiling/index.html))

Has only been tested on macOS.

Usage:

```bash
python make_templates.py <godot_src_dir> <templates_dir> <comma_separated_platforms>
```
