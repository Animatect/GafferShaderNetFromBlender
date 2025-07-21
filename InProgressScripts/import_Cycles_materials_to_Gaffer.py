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

label_map_path = os.path.join("C:\\GitHub\\GafferShaderNetFromAttr_Builder\\InProgressScripts", "cycles_label_map.json")
with open(label_map_path, "r", encoding="utf-8") as f:
    LABEL_MAP = json.load(f)

def safe_plug_name(plugname):
    plugnamesafe = plugname.lower().replace(" ", "_")
    return plugnamesafe

def normalize_name(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())

def resolve_plug_name(socket_label, gaffer_node, io="parameters", shader_type=None):
    # 1. Try safe plug name directly
    candidate = safe_plug_name(socket_label)
    if io in gaffer_node and candidate in gaffer_node[io]:
        # print("### 1 ###")
        # print("candidate: ", candidate)
        return candidate

    # 2. Try label map fallback
    if shader_type:
        # print("### 2 ###")
        # print("SHT: ", shader_type, ", OnLblMap: ",LABEL_MAP.get(shader_type, {}))
        remap = LABEL_MAP.get(shader_type, {}).get(socket_label.lower())
        # print("remap: ", remap)
        if remap and remap in gaffer_node[io]:
            return remap

    # 3. Try fuzzy match
    print("shader_type: ", shader_type)
    norm_target = normalize_name(socket_label)
    for name in gaffer_node[io].keys():
        # print("### 3 ###")
        if normalize_name(name) == norm_target:
            # print("name: ",name)
            return name

    return None

# --- Safe plug connection with auto converter shader insertion ---
def safe_connect(parent, src_node_name, src_socket_label, dst_node_name, dst_socket_label):
    try:
        src_node = parent[src_node_name]
        dst_node = parent[dst_node_name]

        # Try to guess shader types from node names
        src_shader_type = src_node['name'].getValue()#getattr(src_node, "shaderType", None)
        dst_shader_type = dst_node['name'].getValue()#getattr(dst_node, "shaderType", None)
        print("dst_node: ", dst_node)
        print("dst_shader_type: ", dst_shader_type)

        src_plug_name = resolve_plug_name(src_socket_label, src_node, io="out", shader_type=src_shader_type)
        dst_plug_name = resolve_plug_name(dst_socket_label, dst_node, io="parameters", shader_type=dst_shader_type)

        if not src_plug_name or not dst_plug_name:
            print(f"❌ Could not resolve {src_node_name}.{src_socket_label} → {dst_node_name}.{dst_socket_label}")
            return

        src_plug = src_node["out"][src_plug_name]
        dst_plug = dst_node["parameters"][dst_plug_name]

        if dst_plug.typeName() == src_plug.typeName():
            dst_plug.setInput(src_plug)
            print(f"🔗 Connected {src_node_name}.{src_plug_name} → {dst_node_name}.{dst_plug_name}")
        else:
            from_type = PLUG_TYPE_MAP.get(src_plug.typeName())
            to_type = PLUG_TYPE_MAP.get(dst_plug.typeName())

            if not from_type or not to_type:
                print(f"❌ Unknown plug types: {src_plug.typeName()} → {dst_plug.typeName()}")
                return

            converter_name = f"convert_{from_type}_to_{to_type}"
            converter = GafferCycles.CyclesShader(f"{src_node_name}_to_{dst_node_name}_converter")
            converter.loadShader(converter_name)
            parent.addChild(converter)

            inplugname = f"value_{from_type}"
            outplugname = f"value_{to_type}"

            converter["parameters"][inplugname].setInput(src_plug)
            dst_plug.setInput(converter["out"][outplugname])
            print(f"🔀 Inserted converter: {converter_name} between {src_node_name}.{src_plug_name} → {dst_node_name}.{dst_plug_name}")

    except Exception as e:
        print(f"❌ Failed to connect {src_node_name}.{src_socket_label} → {dst_node_name}.{dst_socket_label}: {e}")

def create_basecheck_shader(mainShaderbox, paths):
    shassignnode = GafferScene.ShaderAssignment("CheckShader")
    mainShaderbox.addChild(shassignnode)

    checkMat = GafferCycles.CyclesShader("CheckMaterial")
    mainShaderbox.addChild(checkMat)
    checkMat.loadShader("emission")
    checkMat["parameters"]["color"].setValue(imath.Color3f(1, 0, 1))  # Magenta
    #Gaffer.Metadata.registerValue(checkMat, 'nodeGadget:color', imath.Color3f(1, 0, 1))

    shassignnode['shader'].setInput(checkMat['out'])

    pathFilter = GafferScene.PathFilter("CheckerNodes_pathFilter")
    mainShaderbox.addChild(pathFilter)
    shassignnode['filter'].setInput(pathFilter["out"])

    newpaths = IECore.StringVectorData()
    for v in paths:
        newpaths.append(v if v.endswith("/...") else v.rstrip("/") + "/...")
    pathFilter["paths"].setValue(newpaths)

    return shassignnode

def boxInOutHandling(innode, outnode=None):
    if not outnode:
        outnode = innode
    #PromoteInOut
    boxInPlug = Gaffer.BoxIO.promote( innode["in"] )
    boxOutPlug = Gaffer.BoxIO.promote( outnode["out"] )
    # Add a passthrough
    boxOutNode = boxOutPlug.getInput().node()
    boxInNode = boxInPlug.outputs()[0].node()
    boxOutNode["passThrough"].setInput( boxInNode["out"] )

# --- Main material loader ---
def load_materials_from_json(json_path, parent):
    with open(json_path, "r") as f:
        material_data = json.load(f)

    paths = [f"/{mat}" for mat in material_data.keys()]

    #Add Master Box
    materials_box = Gaffer.Box("Materials")
    parent.addChild(materials_box)

    # Add fallback check shader box
    fallback_box = Gaffer.Box("Fallback_Material")
    materials_box.addChild(fallback_box)
    Gaffer.Metadata.registerValue(fallback_box, 'nodeGadget:color', imath.Color3f(1, 0, 1))
    shassignnode = create_basecheck_shader(fallback_box, paths)
    boxInOutHandling(shassignnode)
    last_out = fallback_box["out"]

    for mat_name, material in material_data.items():
        print(f"\n🧱 Loading material: {mat_name}")
        mat_box = Gaffer.Box(mat_name)
        materials_box.addChild(mat_box)

        nodes = material["nodes"]
        links = material.get("links", [])
        created_nodes = {}

        for node_name, node_info in nodes.items():
            node_type = node_info.get("type", "")
            shader_type = node_info.get("cycles_type", "")
            params = node_info.get("parameters", {})

            if node_type == "ShaderNodeOutputMaterial":
                output_node_name = node_name
                continue

            safe_name = re.sub(r'\W|^(?=\d)', '_', node_name)
            shader = GafferCycles.CyclesShader(safe_name)
            shader.loadShader(shader_type)
            shader.shaderType = shader_type
            mat_box.addChild(shader)
            created_nodes[node_name] = safe_name

            print(f"➕ Created shader node: {node_name} as {safe_name}")

            for param, value in params.items():
                try:
                    Gaffer.PlugAlgo.setValueFromData(shader["parameters"][param], value)
                except Exception as e:
                    print(f"⚠️ Could not set param {param} on {safe_name}: {e}")

        for link in links:
            print("📦 Raw link:", link)
            if not isinstance(link, dict):
                continue

            from_node = link["from_node"]
            to_node = link["to_node"]
            from_socket = link["from_socket"]
            to_socket = link["to_socket"]

            if from_node == output_node_name:
                continue
            if to_node == output_node_name:
                final_shader = created_nodes.get(from_node)
                if final_shader:
                    sh_assign = GafferScene.ShaderAssignment("ShaderAssignment")
                    mat_box.addChild(sh_assign)
                    sh_assign["shader"].setInput(mat_box[final_shader]["out"])
                    print(f"🎯 Created ShaderAssignment and connected final shader {final_shader}")
                continue

            if from_node in created_nodes and to_node in created_nodes:
                safe_connect(mat_box, created_nodes[from_node], from_socket, created_nodes[to_node], to_socket)

        boxInOutHandling(sh_assign)
        # Connect in/out for box chaining
        mat_box["in"].setInput(last_out)
        last_out = mat_box["out"]
    
    #Handle InOut for master box
    boxInOutHandling(fallback_box, mat_box)


# Usage:
# Assuming you're running this in a Gaffer script editor or binding context
json_path = r"C:\tmp\Gaffer\BlenderInterop\matTests\materialNet.json"
load_materials_from_json(json_path, root)  # or a Gaffer.Box() if building modular