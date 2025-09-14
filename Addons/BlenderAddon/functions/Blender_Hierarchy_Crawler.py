import bpy
import json
import os
from mathutils import Vector


class ScheneHierarchyExporter:
    def __init__(self, root="/root", selected_only=False, set_mat_id=True, Bake_TextureSpace=True):
        self.root = root
        self.process_selected_only = selected_only
        self.set_mat_id = set_mat_id
        self.Bake_TextureSpace = Bake_TextureSpace


    # converted from blender/intern/cycles/blender/util.h on line 548 /* Texture Space */
    def mesh_texspace_transform(self, mesh):
        # Get texspace center + size (auto recomputed if needed)
        if mesh.use_auto_texspace:
            mesh.update()

        loc = Vector(mesh.texspace_location)  # center
        size = Vector(mesh.texspace_size)     # half-size along each axis

        # Convert size to reciprocal scale (0.5 / halfsize == 1 / fullsize)
        scale = Vector((
            (0.5 / size.x) if size.x != 0 else 0.0,
            (0.5 / size.y) if size.y != 0 else 0.0,
            (0.5 / size.z) if size.z != 0 else 0.0,
        ))

        # Adjust loc to be ready for transform
        offset = loc * scale - Vector((0.5, 0.5, 0.5))

        return scale, offset

    def generated_to_vector_attribute(self, obj, attr_name="baked_texturespace"):
        if obj.type != 'MESH':
            return
        mesh = obj.data
        
        if attr_name not in mesh.attributes:
            mesh.attributes.new(name=attr_name, type='FLOAT_VECTOR', domain='POINT')
            
        attr = mesh.attributes[attr_name].data

        scale, offset = self.mesh_texspace_transform(mesh)
        for i, v in enumerate(mesh.vertices):
            gen = v.co * scale - offset
            attr[i].vector = gen

    def assign_mat_id(self, obj):
        # assign ID attr to meshes to split in Gaffer
        mesh = obj.data
        hasmultiplemat:bool = False

        # Create the attribute if it doesn't already exist
        if "mat_index" not in mesh.attributes:
            mesh.attributes.new(name="mat_index", type='INT', domain='FACE')

        # Access the attribute data
        attr = mesh.attributes["mat_index"].data
        
        if len(obj.material_slots)>0:
            # Assign the material index to each face
            for i, poly in enumerate(mesh.polygons):
                attr[i].value = poly.material_index
            print("attr: ", attr)
            hasmultiplemat = len(obj.material_slots) > 1

        return hasmultiplemat
        

    def build_usd_path(self, obj, include_data=True):
        # Build parent path first (no data names in recursion)
        if obj.parent:
            base = self.build_usd_path(obj.parent, include_data=False)
        else:
            base = self.root

        # Append just this object's name
        path = f"{base}/{obj.name}"


        # Optionally append the mesh datablock name (only for the leaf)
        if include_data and obj.type == 'MESH' and obj.data:
            path = f"{path}/{obj.data.name}"

        return path


    def process_object(self, obj):
        # Process a single mesh object
        usd_path = self.build_usd_path(obj)
        has_multiple_mat = False
        if self.set_mat_id:
            has_multiple_mat = self.assign_mat_id(obj)
        if self.Bake_TextureSpace:
            self.generated_to_vector_attribute(obj)

        # Build material index → name mapping
        mat_by_index = {}
        for idx, slot in enumerate(obj.material_slots):
            if slot.material:
                mat_by_index[idx] = slot.material.name

        dataobj = {
            obj.name:{
                "path": usd_path,
                "mat_by_index": mat_by_index,
                "has_multiple_mat": has_multiple_mat
            }
        }

        return dataobj

    def get_serialized_hierarchy_dict(self) -> dict:
         # Export the hierarchy of all mesh objects to JSON
        data = {}  # reset before exporting
        obj_iter_collection = bpy.context.scene.objects
        if self.process_selected_only:
            # set mat_iter_collection to an iterated list of selected objects
            selected_objs = set()
            for obj in bpy.context.selected_objects:
                if obj.type == "MESH":
                    selected_objs.add(obj)
            obj_iter_collection = list(selected_objs)

        for obj in obj_iter_collection:
            if obj.type == 'MESH' and len(obj.material_slots) > 0:
                dataobj = self.process_object(obj)
                data.update(dataobj)
        return data

    def export(self, filepath):       
        serialized_dict = self.get_serialized_hierarchy_dict()

        with open(filepath, "w") as f:
            json.dump(serialized_dict, f, indent=4)

        print(f"Exported material hierarchy JSON to {filepath}")


# Example usage: save next to blend file
if __name__ == "__main__":
    folder = "C:\\GitHub\\GafferShaderNetFromBlender\\InProgressScripts\\testFiles\\"
    output_path = os.path.join(folder, "scene_hierarchy.json")

    exporter = ScheneHierarchyExporter(root="/root")
    exporter.export(output_path)