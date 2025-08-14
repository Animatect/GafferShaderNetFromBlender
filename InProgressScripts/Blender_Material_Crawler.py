import bpy
import mathutils
import json
import os


script_dir = r"C:\GitHub\GafferShaderNetFromBlender\InProgressScripts"#os.path.dirname(os.path.abspath(__file__))
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

# Handles the whole object
def handle_special_cases(node):
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
    elif node.bl_idname == "ShaderNodeMix":
        specials["data_type"] = node.data_type
        specials["clamp_factor"] = node.clamp_factor
        specials["clamp_result"] = node.clamp_result
        if node.data_type == 'RGBA':
            specials["Factor"] = node.inputs[0].default_value
            specials["A"] = to_serializable(node.inputs[6])
            specials["B"] = to_serializable(node.inputs[7])
        elif node.data_type == 'VECTOR':
            if node.factor_mode == 'UNIFORM':
                specials["Factor"] = node.inputs[0].default_value
            else:
                specials["Factor"] = to_serializable(node.inputs[1])
            specials["A"] = to_serializable(node.inputs[4])
            specials["B"] = to_serializable(node.inputs[5])
        elif node.data_type == 'FLOAT':
            specials["Factor"] = node.inputs[0].default_value
            specials["A"] = node.inputs[2].default_value
            specials["B"] = node.inputs[3].default_value
    elif node.bl_idname == "ShaderNodeMapRange":
        specials["data_type"] = node.data_type
        specials["interpolation_type"] = node.interpolation_type
        specials["clamp"] = node.clamp
        if node.data_type == 'FLOAT':
            specials["Value"] = node.inputs[0].default_value
            specials["From Min"] = node.inputs[1].default_value
            specials["From Max"] = node.inputs[2].default_value
            specials["To Min"] = node.inputs[3].default_value
            specials["To Max"] = node.inputs[4].default_value
            specials["Steps"] = node.inputs[5].default_value
        elif node.data_type == 'FLOAT_VECTOR':            
            specials["Vector"] = to_serializable(node.inputs[6])
            specials["Value"] = node.inputs[0].default_value
            specials["From Min"] = to_serializable(node.inputs[7])
            specials["From Max"] = to_serializable(node.inputs[8])
            specials["To Min"] = to_serializable(node.inputs[9])
            specials["To Max"] = to_serializable(node.inputs[10])
            specials["Steps"] = to_serializable(node.inputs[11])
    elif node.bl_idname == "ShaderNodeFloatCurve":
        specials["Factor"] = node.inputs["Factor"].default_value
        specials["Value"] = node.inputs["Value"].default_value
        curve = node.mapping.curves[0]
        points = [[point.location[0], point.location[1], point.handle_type] for point in curve.points]
        specials["curve"] = points
    elif node.bl_idname in ("ShaderNodeVectorCurve", "ShaderNodeRGBCurve"):
        specials["Factor"] = node.inputs["Fac"].default_value
        labels = []
        if node.bl_idname =="ShaderNodeVectorCurve":
            specials["Vector"] = to_serializable(node.inputs["Vector"])
            labels = ['x','y','z']
        if node.bl_idname =="ShaderNodeRGBCurve":
            specials["Color"] = to_serializable(node.inputs["Color"])
            labels = ['c','r','g','b']
        curves = node.mapping.curves
        index = 0
        for curve in curves:
            specials[labels[index]] = [[point.location[0], point.location[1], point.handle_type] for point in curve.points]
            index += 1
    elif node.bl_idname == "ShaderNodeValToRGB": # ColorRamp
        specials["Factor"] = node.inputs["Fac"].default_value
        ramp = node.color_ramp
        specials["color_mode"] = ramp.color_mode
        specials["interpolation"] = ramp.interpolation
        elements = node.color_ramp.elements
        specials["ramp_elements"] = [{"pos":element.position, "color":list(element.color)} for element in elements]
    elif node.bl_idname in ("ShaderNodeMath", "ShaderNodeVectorMath"):
        # Common properties
        if hasattr(node, "operation"):
            specials["operation"] = node.operation
        if hasattr(node, "use_clamp"):
            specials["use_clamp"] = node.use_clamp
        # Capture all default values from unconnected inputs
        for idx, input_socket in enumerate(node.inputs):
            name = input_socket.name
            if input_socket.name.lower() in ("value", "vector"):
                name = name+str(idx+1)
            val = to_serializable(input_socket)
            specials[name] = val

    return specials

# Handles Only the extra Params and adds to the auto inputs
def handle_ui_params(node):
    uiparams = {}
    if node.bl_idname in ("ShaderNodeVertexColor", "ShaderNodeAttribute", "ShaderNodeUVMap", "ShaderNodeVectorTransform"):
        attrs=["layer_name", "attribute_name", "attribute_type", "uv_map", "from_instancer"]
        attrs.extend(["vector_type", "convert_from", "convert_to"])
        for attr in attrs:
            if hasattr(node, attr):
                uiparams[attr] = getattr(node, attr, "")

    return uiparams

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
                # We check for special handling and if the is not we proceed with regular node handling.
                params = handle_special_cases(from_node)
                if len(params)==0:
                    params = {
                        inp.name: to_serializable(inp)
                        for inp in from_node.inputs
                        if not inp.is_linked and hasattr(inp, "default_value")
                    }
                    params.update(extract_node_extras(from_node))
                    params.update(handle_ui_params(from_node))

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
output_path = "C:\\GitHub\\GafferShaderNetFromBlender\\InProgressScripts\\testFiles\\materialNet.json"
with open(output_path, 'w') as f:
    json.dump(all_materials_data, f, indent=2)

print(f"\n✅ Shader network exported to {output_path}")
