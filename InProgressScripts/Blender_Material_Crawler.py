import bpy
import mathutils
import json
import os


script_dir = r"C:\GitHub\GafferShaderNetFromAttr_Builder\InProgressScripts"#os.path.dirname(os.path.abspath(__file__))
mapping_path = os.path.join(script_dir, "blender_shader_class_to_cycles_name.json")
with open(mapping_path, "r") as f:
    BLENDER_TO_CYCLES_SHADER_MAP = json.load(f)

def blender_node_to_cycles(node):
    cycles_name = BLENDER_TO_CYCLES_SHADER_MAP.get(node.bl_idname)
    if cycles_name is None:
        print(f"⚠️ No mapping for {node.bl_idname}")
        return "unknown"
    return cycles_name
    
def to_serializable(socket):
    try:
        val = socket.default_value
    except AttributeError:
        return None

    # If it's an Euler, Vector, or Color from mathutils
    if isinstance(val, (mathutils.Vector, mathutils.Euler, mathutils.Color)):
        return list(val)

    # Primitive types
    if isinstance(val, (float, int, bool, str)):
        return val

    # Fallback for iterable types
    if hasattr(val, "__iter__"):
        val_list = list(val)
        # Heuristic: treat uniform vector [x, x, x] as scalar x
        if len(set(val_list)) == 1:
            return val_list[0]
        return val_list

    return str(val)

def extract_node_extras(node):
    extras = {}
    socket_names = {s.name for s in node.inputs} | {s.name for s in node.outputs}
    skip_exact = {
        "bl_idname", "bl_label", "bl_description", "bl_icon", "bl_static_type",
        "name", "label", "type", "location", "select", "color_tag", "color",
        "width", "height", "bl_width_min", "bl_width_max", "bl_width_default",
        "bl_height_min", "bl_height_max", "bl_height_default",
        "show_options", "show_preview", "show_texture", "use_custom_color",
        "parent", "hide", "mute", "warning_propagation"
    }

    for attr in dir(node):
        if attr.startswith("_") or attr in socket_names or attr in skip_exact:
            continue
        try:
            val = getattr(node, attr)
            if inspect.ismethod(val) or inspect.isfunction(val):
                continue
            if hasattr(val, "bl_rna"):
                continue
            if is_serializable(val):
                extras[attr] = val
        except Exception:
            continue
    return extras

def extract_special_cases(node):
    specials = {}
    if node.bl_idname == "ShaderNodeTexImage":
        if node.image:
            img = node.image
            imgpath = img.filepath.replace("\\", "/")
            imgpath = bpy.path.abspath(imgpath)
            imgpath = os.path.realpath(imgpath)
            specials["image"] = imgpath
            if hasattr(img, "colorspace_settings"):
                specials["image_color_space"] = img.colorspace_settings.name
            if hasattr(img, "alpha_mode"):
                specials["alpha_mode"] = img.alpha_mode
            if hasattr(img, "use_view_as_render"):
                specials["use_view_as_render"] = img.use_view_as_render
            if hasattr(img, "use_alpha"):
                specials["use_alpha"] = img.use_alpha

        if hasattr(node, "color_space"):
            specials["color_space"] = node.color_space
        if hasattr(node, "interpolation"):
            specials["interpolation"] = node.interpolation
        if hasattr(node, "projection"):
            specials["projection"] = node.projection
        if hasattr(node, "extension"):
            specials["extension"] = node.extension

    return specials

def trace_shader_network(material):
    if not material.use_nodes:
        print(f"{material.name} has no nodes.")
        return None

    tree = material.node_tree
    nodes = tree.nodes

    output_node = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)
    if output_node is None:
        print(f"No Material Output found in {material.name}")
        return None

    surface_input = output_node.inputs.get("Surface")
    if not surface_input or not surface_input.is_linked:
        print(f"Material Output in {material.name} is not connected.")
        return None

    visited = set()
    node_info = {}
    links = []

    def walk(socket):
        for link in socket.links:
            from_node = link.from_node
            from_socket = link.from_socket
            to_node = link.to_socket.node
            to_socket = link.to_socket

            if from_node.name not in visited:
                visited.add(from_node.name)
                cycles_type = blender_node_to_cycles(from_node)
                if cycles_type == "unknown":
                    print("On ",material.name, " the node ", from_node.name, " of Type: ", from_node.bl_idname, " mapped to unknown.")
                params = {
                    inp.name: to_serializable(inp)
                    for inp in from_node.inputs
                    if not inp.is_linked and hasattr(inp, "default_value")
                }

                extras = extract_node_extras(from_node)
                specials = extract_special_cases(from_node)

                # Merge extras and specials into params
                params.update(extras)
                params.update(specials)

                node_info[from_node.name] = {
                    "type": from_node.bl_idname,
                    "cycles_type": cycles_type,
                    "params": params,
                    "location": to_serializable(from_node.location)
                }

                for input_socket in from_node.inputs:
                    if input_socket.is_linked:
                        walk(input_socket)

            # Always store the link
            links.append({
                "from_node": from_node.name,
                "from_socket": from_socket.name,
                "to_node": to_node.name,
                "to_socket": to_socket.name
            })

    # Start from surface input
    visited.add(output_node.name)
    node_info[output_node.name] = {
        "type": output_node.bl_idname,
        "cycles_type": blender_node_to_cycles(output_node),
        "params": {},
        "location": list(output_node.location)
    }

    walk(surface_input)

    return {
        material.name: {
            "nodes": node_info,
            "links": links
        }
    }

# Build and export all materials
all_materials_data = {}
for mat in bpy.data.materials:
    data = trace_shader_network(mat)
    if data:
        all_materials_data.update(data)

# Save to JSON file
#output_path = bpy.path.abspath("//shader_export.json")
output_path = "C:\\GitHub\\GafferShaderNetFromAttr_Builder\\InProgressScripts\\testFiles\\materialNet.json"
with open(output_path, 'w') as f:
    json.dump(all_materials_data, f, indent=2)

print(f"\n✅ Shader network exported to {output_path}")
