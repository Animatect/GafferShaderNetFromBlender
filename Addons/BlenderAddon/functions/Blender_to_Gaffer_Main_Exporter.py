import os
import json
import sys
import bpy

# sys.path.append(os.path)

from .Blender_Material_Crawler import MaterialExporter
from .Blender_Hierarchy_Crawler import ScheneHierarchyExporter


class BlenderExporter(ScheneHierarchyExporter, MaterialExporter):
    def __init__(self, root="/root", selected_only=False, set_mat_id=True, bake_TextureSpace=True):
        ScheneHierarchyExporter.__init__(self, root, selected_only, set_mat_id, bake_TextureSpace)
        MaterialExporter.__init__(self, selected_only)
        self.data = {}
        self.cycles_version = 4.4

    def export_mat_only(self, filepath):
        self.export_materials(filepath)
        
    def export(self, filepath):
        self.data = {
            "materials":{},
            "hierarchy":{}
        }
        material_dict:dict = self.get_serialized_mat_dict()
        hierarchy_dict:dict = self.get_serialized_hierarchy_dict()
        self.data["materials"].update(material_dict)
        self.data["hierarchy"].update(hierarchy_dict)
        
        with open(filepath, "w") as f:
            json.dump(self.data, f, indent=4)

        print(f"Exported scene + material data to {filepath}")


# Example usage
if __name__ == "__main__":
    folder = "C:\\GitHub\\GafferShaderNetFromBlender\\InProgressScripts\\testFiles\\"
    output_path = os.path.join(folder, "combined_export.json")

    exporter = BlenderExporter(root="/root")
    exporter.export(output_path)