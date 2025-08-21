import Gaffer
import GafferScene
import GafferCycles
import IECore
import imath
import json
import os
import re

# --- Type conversion map for plugs ---
PLUG_TYPE_MAP = {
    'Gaffer::FloatPlug': 'float',
    'Gaffer::IntPlug': 'int',
    'Gaffer::V3fPlug': 'vector',
    'Gaffer::Color3fPlug': 'color',
    'Gaffer::StringPlug': 'string',
    'Gaffer::BoolPlug': 'int'
}

SPECIAL_CASES = [
    "image_texture",
    "float_curve",
    "vector_curves",
    "rgb_curves"
]

SHADER_TYPE_REMAP = {
    "hue/saturation/value":'hsv',
    "color_ramp":"rgb_ramp",
    "add_shader":"add_closure",
    "curves_info":"hair_info",
    "camera_data":"camera_info",
    "mix_shader":"mix_closure",
    "volume_scatter":"scatter_volume",
    "volume_absorption":"absorption_volume",
    "ies_texture":"ies_light",
    "point_density":"point_density_texture",
    "uv_map":"uvmap",
    "color_attribute":"vertex_color",

}

label_map_path = os.path.join("C:\\GitHub\\GafferShaderNetFromBlender\\InProgressScripts", "cycles_label_map.json")
with open(label_map_path, "r", encoding="utf-8") as f:
    LABEL_MAP = json.load(f)

def safe_plug_name(plugname):
    plugnamesafe = plugname.lower().replace(" ", "_")
    return plugnamesafe

def normalize_name(name):
    return re.sub(r'[^a-z0-9]', '', name.lower())

def resolve_plug_name(socket_label, gaffer_node, io="parameters", shader_type=None, isBox=False):
    validIo = gaffer_node.getChild(io)
    candidate = safe_plug_name(socket_label)
    #BoxNodes
    if isBox:
        if shader_type in ["rgb_curves", "vector_curves"]:
            if io == "out":
                return "value"
            else:
                return candidate

    # 1. Try safe plug name directly
    if validIo and io in gaffer_node and candidate in gaffer_node[io]:
        return candidate
    
    # 2. Try label map fallback
    if shader_type:
        remap = LABEL_MAP.get(shader_type, {}).get(socket_label.lower())
        if validIo and remap and remap in gaffer_node[io]:
            return remap

    # 3. Try fuzzy match
    norm_target = normalize_name(socket_label)
    if validIo:
        for name in gaffer_node[io].keys():
            if normalize_name(name) == norm_target:
                return name

    return None

def shader_safe_type(shadertype:str):
    if SHADER_TYPE_REMAP.get(shadertype):
        shadertype = SHADER_TYPE_REMAP.get(shadertype)
    safeShadertype = re.sub(r'\W|^(?=\d)', '_', shadertype)
    
    return safeShadertype
    

def process_values(value):
    if isinstance(value, list) and all(isinstance(x, float) for x in value):
        if len(value) == 3:
            return imath.V3f(*value)
        elif len(value) == 4:
            return imath.Color3f(*value[:3])  # ignore alpha
        else:
            return [float(v) for v in value]  # plain list of floats
    elif isinstance(value, list) and all(isinstance(x, int) for x in value):
        return [int(v) for v in value]  # plain list of ints
    else:
        return value
def process_curve(curve, curvedict, signature='FLOAT'):
    curve.clearPoints()
    for i in range(len(curvedict)):
        ptnm:str = "p"+str(i)
        x = curvedict[i][0]
        y = None
        if signature == 'FLOAT':
            y = process_values(curvedict[i][1])
        elif signature == 'RGBA':
            val = curvedict[i][1]
            y = imath.Color3f(val, val, val)
        else:
            pass
        curve.addChild( Gaffer.ValuePlug( ptnm, flags = Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic, ) )
        curve[ptnm].addChild( Gaffer.FloatPlug( "x", defaultValue = x, flags = Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic, ) )
        if signature == 'FLOAT':
            curve[ptnm].addChild( Gaffer.FloatPlug( "y", defaultValue = y, flags = Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic, ) )
        elif signature == 'RGBA':
            curve[ptnm].addChild( Gaffer.Color3fPlug( "y", defaultValue = y, flags = Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic, ) )
        

def is_curvelist_default(curvelist):
    isdefault:bool = len(curvelist) == 2 and curvelist[0][0]==0.0 and curvelist[0][1]==0.0  and curvelist[1][0]==1.0 and curvelist[1][1]==1.0
    return isdefault

def translate_interpolation(curvelist:list):
    interpolation = 1 # AUTO is translated to CatmullRom
    if curvelist[0][2] == "VECTOR":
        interpolation = 0
    return interpolation
def build_rgb_curves_box(shader_node, params_dict):
    oldNodeName = shader_node.getName()
    parent = shader_node.parent()

    # Create the box
    box = Gaffer.Box("Box1")
    parent.addChild(box)

    # Name plug for safe_connect algo
    string_plug = Gaffer.StringPlug(
        "name",
        Gaffer.Plug.Direction.In,
        shader_node['name'].getValue(),
        Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic
    )
    box.addChild(string_plug)
    Gaffer.Metadata.registerValue(box["name"], 'plugValueWidget:type', '')

    # Nodes inside box
    cshdr = GafferCycles.CyclesShader("c");  cshdr.loadShader("rgb_curves");   box.addChild(cshdr)
    splitshader = GafferCycles.CyclesShader("split"); splitshader.loadShader("separate_rgb"); box.addChild(splitshader)
    rshdr = GafferCycles.CyclesShader("r"); rshdr.loadShader("float_curve");   box.addChild(rshdr)
    gshdr = GafferCycles.CyclesShader("g"); gshdr.loadShader("float_curve");   box.addChild(gshdr)
    bshdr = GafferCycles.CyclesShader("b"); bshdr.loadShader("float_curve");   box.addChild(bshdr)
    combineshader = GafferCycles.CyclesShader("join"); combineshader.loadShader("combine_rgb"); box.addChild(combineshader)

    # Wiring
    rshdr["parameters"]["value"].setInput(splitshader["out"]["r"])
    gshdr["parameters"]["value"].setInput(splitshader["out"]["g"])
    bshdr["parameters"]["value"].setInput(splitshader["out"]["b"])
    combineshader["parameters"]["r"].setInput(rshdr["out"]["value"])
    combineshader["parameters"]["g"].setInput(gshdr["out"]["value"])
    combineshader["parameters"]["b"].setInput(bshdr["out"]["value"])
    cshdr["parameters"]["value"].setInput(combineshader['out']['image'])

    # BoxIO plugs
    boxInPlugA = Gaffer.BoxIO.promote(splitshader["parameters"]["color"])
    boxInPlugB = Gaffer.BoxIO.promote(cshdr['parameters']['fac'])
    boxOutPlug = Gaffer.BoxIO.promote(cshdr['out']['value'])

    # passthrough
    boxOutNode = boxOutPlug.getInput().node()
    boxInNodeA = boxInPlugA.outputs()[0].node()
    boxInNodeB = boxInPlugB.outputs()[0].node()
    boxOutNode["passThrough"].setInput(boxInNodeA["out"])

    # Names
    boxInNodeA['name'].setValue("color")
    boxInNodeB['name'].setValue("fac")
    boxOutNode['name'].setValue("value")
    rshdr["parameters"]["fac"].setInput(boxInNodeB["out"])
    gshdr["parameters"]["fac"].setInput(boxInNodeB["out"])
    bshdr["parameters"]["fac"].setInput(boxInNodeB["out"])

    # Reconnect old inputs
    colorinput = shader_node['parameters']['value'].getInput()
    factorinput = shader_node["parameters"]["fac"].getInput()

    box["fac"].setValue(params_dict["Factor"])
    box["color"].setValue(process_values(params_dict["Color"]))

    if colorinput:
        box['value'].setInput(colorinput)
    if factorinput:
        box['fac'].setInput(factorinput)

    # Cleanup and rename
    parent.removeChild(shader_node)
    box.setName(oldNodeName)

    # Curves
    process_curve(rshdr['parameters']['curve'], params_dict["r"])
    process_curve(gshdr['parameters']['curve'], params_dict["g"])
    process_curve(bshdr['parameters']['curve'], params_dict["b"])
    process_curve(cshdr['parameters']['curves'], params_dict["c"], signature='RGBA')

    # Interpolation
    cshdr['parameters']['curves']["interpolation"].setValue(translate_interpolation(params_dict["c"]))
    rshdr['parameters']['curve']["interpolation"].setValue(translate_interpolation(params_dict["r"]))
    gshdr['parameters']['curve']["interpolation"].setValue(translate_interpolation(params_dict["g"]))
    bshdr['parameters']['curve']["interpolation"].setValue(translate_interpolation(params_dict["b"]))

    return box

def build_vector_curves_box(shader_node, params_dict):
    oldNodeName = shader_node.getName()
    parent = shader_node.parent()

    # Create the box
    box = Gaffer.Box("Box1")
    parent.addChild(box)

    # Name plug for safe_connect algo
    string_plug = Gaffer.StringPlug(
        "name",
        Gaffer.Plug.Direction.In,
        shader_node['name'].getValue(),
        Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic
    )
    box.addChild(string_plug)
    Gaffer.Metadata.registerValue(box["name"], 'plugValueWidget:type', '')

    # Nodes inside box
    splitshader = GafferCycles.CyclesShader("split"); splitshader.loadShader("separate_xyz"); box.addChild(splitshader)
    rshdr = GafferCycles.CyclesShader("x"); rshdr.loadShader("float_curve");   box.addChild(rshdr)
    gshdr = GafferCycles.CyclesShader("y"); gshdr.loadShader("float_curve");   box.addChild(gshdr)
    bshdr = GafferCycles.CyclesShader("z"); bshdr.loadShader("float_curve");   box.addChild(bshdr)
    combineshader = GafferCycles.CyclesShader("join"); combineshader.loadShader("combine_xyz"); box.addChild(combineshader)

    # Wiring
    rshdr["parameters"]["value"].setInput(splitshader["out"]["x"])
    gshdr["parameters"]["value"].setInput(splitshader["out"]["y"])
    bshdr["parameters"]["value"].setInput(splitshader["out"]["z"])
    combineshader["parameters"]["x"].setInput(rshdr["out"]["value"])
    combineshader["parameters"]["y"].setInput(gshdr["out"]["value"])
    combineshader["parameters"]["z"].setInput(bshdr["out"]["value"])

    # BoxIO plugs
    boxInPlugA = Gaffer.BoxIO.promote(splitshader["parameters"]["vector"])
    boxInPlugB = Gaffer.BoxIO.promote(rshdr['parameters']['fac'])
    boxOutPlug = Gaffer.BoxIO.promote(combineshader['out']['vector'])

    # passthrough
    boxOutNode = boxOutPlug.getInput().node()
    boxInNodeA = boxInPlugA.outputs()[0].node()
    boxInNodeB = boxInPlugB.outputs()[0].node()
    boxOutNode["passThrough"].setInput(boxInNodeA["out"])

    # Names
    boxInNodeA['name'].setValue("vector")
    boxInNodeB['name'].setValue("fac")
    boxOutNode['name'].setValue("value")
    rshdr["parameters"]["fac"].setInput(boxInNodeB["out"])
    gshdr["parameters"]["fac"].setInput(boxInNodeB["out"])
    bshdr["parameters"]["fac"].setInput(boxInNodeB["out"])

    # Reconnect old inputs
    colorinput = shader_node['parameters']['value'].getInput()
    factorinput = shader_node["parameters"]["fac"].getInput()

    box["fac"].setValue(params_dict["Factor"])
    box["vector"].setValue(process_values(params_dict["Vector"]))

    if colorinput:
        box['value'].setInput(colorinput)
    if factorinput:
        box['fac'].setInput(factorinput)

    # Cleanup and rename
    parent.removeChild(shader_node)
    box.setName(oldNodeName)

    # Curves
    process_curve(rshdr['parameters']['curve'], params_dict["x"])
    process_curve(gshdr['parameters']['curve'], params_dict["y"])
    process_curve(bshdr['parameters']['curve'], params_dict["z"])

    # Interpolation
    rshdr['parameters']['curve']["interpolation"].setValue(translate_interpolation(params_dict["x"]))
    gshdr['parameters']['curve']["interpolation"].setValue(translate_interpolation(params_dict["y"]))
    bshdr['parameters']['curve']["interpolation"].setValue(translate_interpolation(params_dict["z"]))

    return box

def set_shader_specialCases(shader_node, params_dict, shader_type):
    if shader_type == "image_texture":        
        shader_node["parameters"]["filename"].setValue((params_dict["image"].replace("\\", "/")))
    # On Curves, interpolation is not 1:1 and takes the value of the first point on Blender.
    elif shader_type == "float_curve":
        shader_node["parameters"]["fac"].setValue(params_dict["Factor"])
        shader_node["parameters"]["value"].setValue(params_dict["Value"])
        shader_node['parameters']['curve']["interpolation"].setValue(translate_interpolation(params_dict["curve"]))
        process_curve(shader_node['parameters']['curve'], params_dict["curve"])
    elif shader_type == "rgb_curves":
        build_rgb_curves_box(shader_node, params_dict)
    elif shader_type == "vector_curves":
        build_vector_curves_box(shader_node, params_dict)

    

def set_shader_parameters(shader_node, params_dict, shader_type):
    print(params_dict)
    if shader_type in SPECIAL_CASES:
        set_shader_specialCases(shader_node, params_dict, shader_type)
        return 
    
    for param_label, value in params_dict.items():
        plug_name = resolve_plug_name(param_label, shader_node, io="parameters", shader_type=shader_type)
        
        if not plug_name:
            if param_label.lower() == 'weight':
                # ignore the weight parameter that comes in every node and is irrelevant for translation.
                continue
            if 'mix' in shader_type:
                if param_label.lower() in ['data_type']:
                    continue
            print(f"⚠️ Could not resolve param '{param_label}' for shader type '{shader_type}'")
            continue

        try:
            plug = shader_node["parameters"][plug_name]
            plug.setValue(process_values(value))
            print(f"🔧 Set {shader_node.getName()}.{plug_name} = {value} => {value}")
        except Exception as e:
            print(f"❌ Failed to set {shader_node.getName()}.{plug_name}, value={value}:\n {e}")


# --- Safe plug connection with auto converter shader insertion ---
def safe_connect(parent, src_node_name, src_socket_label, dst_node_name, dst_socket_label):
    try:
        src_node = parent[src_node_name]
        dst_node = parent[dst_node_name]
        isSrcBox:bool = src_node.typeName() == "Gaffer::Box"
        isDstBox:bool = dst_node.typeName() == "Gaffer::Box"
        # Try to guess shader types from node names
        src_shader_type = src_node['name'].getValue()
        dst_shader_type = dst_node['name'].getValue()
        src_plug_name = resolve_plug_name(src_socket_label, src_node, io="out", shader_type=src_shader_type, isBox=isSrcBox)
        dst_plug_name = resolve_plug_name(dst_socket_label, dst_node, io="parameters", shader_type=dst_shader_type, isBox=isDstBox)

        if not src_plug_name or not dst_plug_name:
            print(f"❌ Could not resolve {src_node_name}.{src_socket_label} → {dst_node_name}.{dst_socket_label}")
            return
        
        # Handle Box Nodes that replace Imported nodes
        if isSrcBox:
            src_plug = src_node[src_plug_name]
        else:
            src_plug = src_node["out"][src_plug_name]

        if isDstBox:
            dst_plug = dst_node[dst_plug_name]
        else:     
            dst_plug = dst_node["parameters"][dst_plug_name]


        if dst_plug.typeName() == src_plug.typeName():
            dst_plug.setInput(src_plug)
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
            Gaffer.Metadata.registerValue( converter, 'nodeGadget:color', imath.Color3f( 0.234999999, 0.234999999, 0.314999998 ) )

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
    # for v in paths:
    #     newpaths.append(v if v.endswith("/...") else v.rstrip("/") + "/...")
    newpaths.append('*')
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
        
        if len(links) == 0:
            print(f"Material {mat_name} does not have a valid Network, probably has 0 connections.")
            Gaffer.Metadata.registerValue( mat_box, 'annotation:user:text', 'EMPTY MATERIAL\n' )
            Gaffer.Metadata.registerValue( mat_box, 'nodeGadget:color', imath.Color3f( 1, 0, 0 ) )
            continue

        for node_name, node_info in nodes.items():
            node_type = node_info.get("type", "")
            shader_type = shader_safe_type(node_info.get("cycles_type", ""))
            params = node_info.get("params", {})

            if node_type == "ShaderNodeOutputMaterial":
                output_node_name = node_name
                continue

            safe_name = re.sub(r'\W|^(?=\d)', '_', node_name)
            shader = GafferCycles.CyclesShader(safe_name)
            shader.loadShader(shader_type)
            shader.shaderType = shader_type
            mat_box.addChild(shader)
            created_nodes[node_name] = safe_name

            # print(f"➕ Created shader node: {node_name} as {safe_name}")
            set_shader_parameters(shader, params, shader_type)

        print("cn: \n", created_nodes)
        for link in links:
            #print("📦 Raw link:", link)
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
                if False:#from_node == "RGB Curves":
                    from_node = "Box1"
                    from_socket = "out_value"
                    safe_connect(mat_box, from_node, from_socket, created_nodes[to_node], to_socket)
                #print(f"fn: {from_node}, tn: {to_node}, fs: {from_socket}, ts: {to_socket}")
                else:
                    safe_connect(mat_box, created_nodes[from_node], from_socket, created_nodes[to_node], to_socket)

        boxInOutHandling(sh_assign)
        # Connect in/out for box chaining
        mat_box["in"].setInput(last_out)
        last_out = mat_box["out"]
    
    #Handle InOut for master box
    boxInOutHandling(fallback_box, mat_box)


# Usage:
# Assuming you're running this in a Gaffer script editor or binding context
json_path = r"C:\GitHub\GafferShaderNetFromBlender\InProgressScripts\testFiles\materialNet.json"
load_materials_from_json(json_path, root)  # or a Gaffer.Box() if building modular