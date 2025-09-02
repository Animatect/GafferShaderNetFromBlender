# generate_label_map.py
# Create the remap of plugs json based on the metadata file in the code.
#Is not perfect and the resulting Json needs to be patched heavily 
# 
# DO NOT OVERWRITE THE CURRENTLY CREATED ONE

import inspect
import os
import sys
import json
import Gaffer

# Locate Gaffer install root
gaffer_module_path = os.path.dirname(inspect.getfile(Gaffer))
gaffer_root = os.path.abspath(os.path.join(gaffer_module_path, "..", ".."))

# Load metadata.py from GafferCyclesUI
cyclesUImetadatapath = os.path.join(gaffer_root, "startup", "GafferCyclesUI")
sys.path.append(cyclesUImetadatapath)
import metadata

def build_label_to_param_map():
    label_map = {}
    for shader, params in metadata.parameterMetadata.items():
        shader_map = {}
        for name, meta in params.items():
            if isinstance(meta, dict):
                label = meta.get("label")
                if isinstance(label, str):
                    shader_map[label.lower()] = name
        label_map[shader] = shader_map
    return label_map

label_map = build_label_to_param_map()

# Write JSON next to this script
#output_path = os.path.join(os.path.dirname(__file__), "cycles_label_map.json")
output_path = os.path.join("C:\\GitHub\\GafferShaderNetFromAttr_Builder\\InProgressScripts", "cycles_label_map.json")

with open(output_path, "w", encoding="utf-8") as f:
    json.dump(label_map, f, indent=2)

print(f"✅ Saved label map to: {output_path}")