import bpy
import json
import os

def build_usd_path(obj, root="/root"):
    """Recursively build a USD-like path for an object based on Blender parent hierarchy."""
    path = root
    if obj.parent:
        path = build_usd_path(obj.parent, root)
    return path + "/" + obj.name

def export_usd_like_json(filepath):
    """Export scene hierarchy as JSON with USD-style paths and material attributes."""
    paths = {}

    for obj in bpy.context.scene.objects:
        usd_path = build_usd_path(obj)
        obj_entry = {"type": obj.type}

        if obj.type == 'MESH':
            mesh = obj.data
            ### Material Split ###
            material_count = len(obj.material_slots)

            if material_count > 1:  # only worth storing if multiple materials
                # Ensure mat_index attribute exists on mesh
                if "mat_index" not in mesh.attributes:
                    mesh.attributes.new(name="mat_index", type='INT', domain='FACE')

                attr = mesh.attributes["mat_index"].data

                # Assign mat indices per face
                for i, poly in enumerate(mesh.polygons):
                    attr[i].value = poly.material_index

                # Collect mat_index mapping into JSON
                obj_entry["attributes"] = {
                    "mat_index": [poly.material_index for poly in mesh.polygons]
                }

        paths[usd_path] = obj_entry

    # Write out
    with open(filepath, "w") as f:
        json.dump(paths, f, indent=4)
    print(f"Exported hierarchy to {filepath}")


# Example usage: saves JSON next to the .blend
folder = "C:\\GitHub\\GafferShaderNetFromBlender\\InProgressScripts\\testFiles\\"
output_path = os.path.join(folder, "scene_hierarchy.json")
export_usd_like_json(output_path)
