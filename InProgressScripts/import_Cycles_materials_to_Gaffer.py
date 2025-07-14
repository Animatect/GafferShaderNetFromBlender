import Gaffer
import GafferScene
import GafferCycles
import json
import os
import re
import imath

# --- Type conversion map for plugs ---
PLUG_TYPE_MAP = {
    'Gaffer::FloatPlug': 'float',
    'Gaffer::IntPlug': 'int',
    'Gaffer::V3fPlug': 'vector',
    'Gaffer::Color3fPlug': 'color',
    'Gaffer::StringPlug': 'string',
    'Gaffer::BoolPlug': 'int'
}
def safe_plug_name(plugname):
    plugnamesafe = plugname.lower().replace(" ", "_")
    return plugnamesafe

# --- Safe plug connection with auto converter shader insertion ---
def safe_connect(parent, src_node, src_name, dst_node, dst_name):
    try:
        src_plug = parent[src_node]["out"][src_name]
        dst_plug = parent[dst_node]["parameters"][dst_name]

        if dst_plug.typeName() == src_plug.typeName():
            dst_plug.setInput(src_plug)
            print(f"🔗 Connected {src_node}.{src_name} → {dst_node}.{dst_name}")
        else:
            from_type = PLUG_TYPE_MAP.get(src_plug.typeName())
            to_type = PLUG_TYPE_MAP.get(dst_plug.typeName())

            if not from_type or not to_type:
                print(f"❌ Unknown plug types: {src_plug.typeName()} → {dst_plug.typeName()}")
                return

            converter_name = f"convert_{from_type}_to_{to_type}"
            converter = GafferCycles.CyclesShader(f"{src_node}_to_{dst_node}_converter")
            converter.loadShader(converter_name)
            parent.addChild(converter)

            inplugname = f"value_{from_type}"
            outplugname = f"value_{to_type}"

            converter["parameters"][inplugname].setInput(src_plug)
            dst_plug.setInput(converter["out"][outplugname])
            print(f"🔀 Inserted converter: {converter_name} between {src_node}.{src_name} → {dst_node}.{dst_name}")

    except Exception as e:
        print(f"❌ Failed to connect {src_node}.{src_name} → {dst_node}.{dst_name}: {e}")

# --- Main material loader ---
def load_material_from_json(json_path, parent):
    with open(json_path, "r") as f:
        material_data = json.load(f)

    material_name, material = next(iter(material_data.items()))
    nodes = material["nodes"]
    links = material.get("links", [])

    created_nodes = {}

    # First pass: create all shaders
    for node_name, node_info in nodes.items():
        node_type = node_info.get("type", "")
        shader_type = node_info.get("cycles_type", "")
        parameters = node_info.get("parameters", {})

        if node_type == "ShaderNodeOutputMaterial":
            print(f"🎯 Found output node: {node_name} (skipping shader creation)")
            output_node_name = node_name
            continue

        safe_name = re.sub(r'\W|^(?=\d)', '_', node_name)
        shader_node = GafferCycles.CyclesShader(safe_name)
        shader_node.loadShader(shader_type)
        parent.addChild(shader_node)
        created_nodes[node_name] = safe_name

        print(f"➕ Created shader node: {node_name} as {safe_name}")

        for param, value in parameters.items():
            try:
                plug = shader_node["parameters"][param]
                Gaffer.PlugAlgo.setValueFromData(plug, value)
            except Exception as e:
                print(f"⚠️ Could not set parameter '{param}' on node '{safe_name}': {e}")

    # Second pass: link nodes
    for link in links:
        print("📦 Raw link:", link)
        if isinstance(link, dict):
            from_node = link.get("from_node")
            from_socket = safe_plug_name( link.get("from_socket") )
            to_node = link.get("to_node")
            to_socket = safe_plug_name( link.get("to_socket") )
        else:
            print(f"⚠️ Invalid link format (not a dict): {link}")
            continue

        if from_node == output_node_name:
            continue  # skip linking from output
        if to_node == output_node_name:
            final_shader = created_nodes.get(from_node)
            if final_shader:
                shader_assignment = GafferScene.ShaderAssignment("ShaderAssignment")
                parent.addChild(shader_assignment)
                shader_assignment["shader"].setInput(parent[final_shader]["out"])
                print(f"🎯 Created ShaderAssignment and connected final shader {final_shader}")
            continue
        if from_node in created_nodes and to_node in created_nodes:
            safe_connect(parent, created_nodes[from_node], from_socket, created_nodes[to_node], to_socket)
        else:
            print(f"⚠️ Skipping connection {from_node}.{from_socket} → {to_node}.{to_socket} (node not found)")


# Usage:
# Assuming you're running this in a Gaffer script editor or binding context
json_path = r"C:\tmp\Gaffer\BlenderInterop\matTests\materialNet.json"
load_material_from_json(json_path, root)  # or a Gaffer.Box() if building modular