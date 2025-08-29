import bpy
import json
import os

def assign_mat_id(obj):
    mesh = obj.data
    hasmultiplemat:bool = False

    # Create the attribute if it doesn't already exist
    if "mat_index" not in mesh.attributes:
        mesh.attributes.new(name="mat_index", type='INT', domain='FACE')

    # Access the attribute data
    attr = mesh.attributes["mat_index"].data
    
    if len(attr)>0:
        # Assign the material index to each face
        for i, poly in enumerate(mesh.polygons):
            attr[i].value = poly.material_index
        
        hasmultiplemat = len(attr) > 1    

    return hasmultiplemat
    

def build_usd_path(obj, root="/root"):
    """Recursively build a USD-like path for an object based on Blender parent hierarchy."""
    if obj.parent:
        return build_usd_path(obj.parent, root) + "/" + obj.name
    return root + "/" + obj.name

def export_material_hierarchy_json(filepath):
    data = {}

    for obj in bpy.context.scene.objects:
        if obj.type != 'MESH':
            continue

        usd_path = build_usd_path(obj)
        has_multiple_mat = assign_mat_id(obj)

        # Build material index → name mapping
        mat_by_index = {}
        for idx, slot in enumerate(obj.material_slots):
            if slot.material:
                mat_by_index[idx] = slot.material.name

        data[obj.name] = {
            "path": usd_path,
            "mat_by_index": mat_by_index
        }

    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)

    print(f"Exported material hierarchy JSON to {filepath}")


# Example usage: save next to blend file
folder = "C:\\GitHub\\GafferShaderNetFromBlender\\InProgressScripts\\testFiles\\"
output_path = os.path.join(folder, "scene_hierarchy.json")
export_material_hierarchy_json(output_path)