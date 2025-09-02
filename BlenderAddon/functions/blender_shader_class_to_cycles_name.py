import bpy
import json
import os

def extract_shader_node_mappings():
    mapping = {}

    for node_class in dir(bpy.types):
        if node_class.startswith("ShaderNode"):
            cls = getattr(bpy.types, node_class)
            if hasattr(cls, "bl_rna") and hasattr(cls.bl_rna, "name"):
                ui_name = cls.bl_rna.name  # e.g. "Glass BSDF"
                cycles_name = ui_name.lower().replace(" ", "_")
                mapping[node_class] = cycles_name

    return mapping

# Generate mapping
shader_mapping = extract_shader_node_mappings()

# Save next to script
#script_dir = os.path.dirname(os.path.abspath(__file__))
#output_path = os.path.join(script_dir, "blender_shader_class_to_cycles_name.json")
output_path = bpy.path.abspath("//blender_shader_class_to_cycles_name.json")

with open(output_path, "w") as f:
    json.dump(shader_mapping, f, indent=2)

print(f"\n Mapping saved to {output_path}")