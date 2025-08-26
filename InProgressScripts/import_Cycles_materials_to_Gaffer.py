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
    "rgb_curves",
    "rgb_ramp"
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
        print("isbox")
        if shader_type in ["rgb_curves", "vector_curves"]:
            if io == "out":
                return "value"
            else:
                return candidate
        elif shader_type == "group":
            return candidate

    # 1. Try safe plug name directly
    if validIo and io in gaffer_node and candidate in gaffer_node[io]:
        return candidate
    
    # 2. Try label map fallback
    if shader_type:
        remap = LABEL_MAP.get(shader_type, {}).get(socket_label.lower())
        # special cases
        if shader_type in ["mix_closure", "add_closure"]:
            if io == "out":
                return "closure"
        if validIo and remap and remap in gaffer_node[io]:
            return remap
        
        # unsupported plugs
        elif remap == 'UNSUPPORTED':
            return 'UNSUPPORTED'

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

def process_ramp(ramp, rampdict):
    ramp.clearPoints()
    for i in range(len(rampdict)):
        ptnm:str = "p"+str(i)
        x = rampdict[i]["pos"]
        y = process_values(rampdict[i]["color"])
        ramp.addChild( Gaffer.ValuePlug( ptnm, flags = Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic, ) )
        ramp[ptnm].addChild( Gaffer.FloatPlug( "x", defaultValue = x, flags = Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic, ) )
        ramp[ptnm].addChild( Gaffer.Color3fPlug( "y", defaultValue = y, flags = Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic, ) )
                
def convert_ramp_interpolation(interpolation:str):
    translatdict:dict = {
        "ease":3,
        "cardinal":1,
        "linear":0,
        "b_spline":2,
        "constant":4
    }
    return translatdict[interpolation.lower()]

def convert_curve_interpolation(curvelist:list):
    interpolation = 1 # AUTO is translated to CatmullRom
    if curvelist[0][2] == "VECTOR":
        interpolation = 0
    return interpolation

def build_curves_box(shader_node, params_dict, mode="rgb"):
    # Builds a curves box in Gaffer for either rgb_curves or vector_curves.
    # mode: "rgb" or "vector"

    oldNodeName = shader_node.getName()
    parent = shader_node.parent()

    box = Gaffer.Box("Box1")
    parent.addChild(box)

    # Safe_connect plug
    string_plug = Gaffer.StringPlug(
        "name",
        Gaffer.Plug.Direction.In,
        shader_node['name'].getValue(),
        Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic
    )
    box.addChild(string_plug)
    Gaffer.Metadata.registerValue(box["name"], 'plugValueWidget:type', '')

    if mode == "rgb":
        # RGB curves: has a special shader node
        cshdr = GafferCycles.CyclesShader("c")
        cshdr.loadShader("rgb_curves")
        box.addChild(cshdr)

        splitshader = GafferCycles.CyclesShader("split")
        splitshader.loadShader("separate_rgb")
        box.addChild(splitshader)

        combineshader = GafferCycles.CyclesShader("join")
        combineshader.loadShader("combine_rgb")
        box.addChild(combineshader)

        channels = [("r", "r"), ("g", "g"), ("b", "b")]
        paramKey = "Color"

    else:  # mode == "vector"
        splitshader = GafferCycles.CyclesShader("split")
        splitshader.loadShader("separate_xyz")
        box.addChild(splitshader)

        combineshader = GafferCycles.CyclesShader("join")
        combineshader.loadShader("combine_xyz")
        box.addChild(combineshader)

        channels = [("x", "x"), ("y", "y"), ("z", "z")]
        paramKey = "Vector"

    # Build float curves for each channel
    curve_nodes = {}
    for chName, splitOut in channels:
        n = GafferCycles.CyclesShader(chName)
        n.loadShader("float_curve")
        box.addChild(n)

        n["parameters"]["value"].setInput(splitshader["out"][splitOut])
        combineshader["parameters"][chName].setInput(n["out"]["value"])
        curve_nodes[chName] = n

    # BoxIO plugs
    if mode == "rgb":
        splitshader["parameters"]["color"].setInput(cshdr["out"]["value"])  # feed rgb_curves
        boxInPlugA = Gaffer.BoxIO.promote(splitshader["parameters"]["color"])
        boxInPlugB = Gaffer.BoxIO.promote(cshdr['parameters']['fac'])
        boxOutPlug = Gaffer.BoxIO.promote(cshdr['out']['value'])
    else:
        boxInPlugA = Gaffer.BoxIO.promote(splitshader["parameters"]["vector"])
        boxInPlugB = Gaffer.BoxIO.promote(curve_nodes['x']['parameters']['fac'])
        boxOutPlug = Gaffer.BoxIO.promote(combineshader['out']['vector'])

    # passthrough
    boxOutNode = boxOutPlug.getInput().node()
    boxInNodeA = boxInPlugA.outputs()[0].node()
    boxInNodeB = boxInPlugB.outputs()[0].node()
    boxOutNode["passThrough"].setInput(boxInNodeA["out"])

    # Names
    boxInNodeA['name'].setValue(paramKey.lower())
    boxInNodeB['name'].setValue("fac")
    boxOutNode['name'].setValue("value")
    for n in curve_nodes.values():
        n["parameters"]["fac"].setInput(boxInNodeB["out"])

    # Reconnect old inputs
    colorinput = shader_node['parameters']['value'].getInput()
    factorinput = shader_node["parameters"]["fac"].getInput()

    box["fac"].setValue(params_dict["Factor"])
    box[paramKey.lower()].setValue(process_values(params_dict[paramKey]))

    if colorinput:
        box['value'].setInput(colorinput)
    if factorinput:
        box['fac'].setInput(factorinput)

    parent.removeChild(shader_node)
    box.setName(oldNodeName)

    # Curves
    for chName in curve_nodes.keys():
        process_curve(curve_nodes[chName]['parameters']['curve'], params_dict[chName])
        curve_nodes[chName]['parameters']['curve']["interpolation"].setValue(
            convert_curve_interpolation(params_dict[chName])
        )

    if mode == "rgb":
        # The additional composite curve
        process_curve(cshdr['parameters']['curves'], params_dict["c"], signature='RGBA')
        cshdr['parameters']['curves']["interpolation"].setValue(convert_curve_interpolation(params_dict["c"]))
        cshdr['parameters']['value'].setInput(combineshader['out']['image'])

    return box


def set_shader_specialCases(shader_node, params_dict, shader_type):
    if shader_type == "image_texture":        
        shader_node["parameters"]["filename"].setValue((params_dict["image"].replace("\\", "/")))
    # On Curves, interpolation is not 1:1 and takes the value of the first point on Blender.
    elif shader_type == "float_curve":
        shader_node["parameters"]["fac"].setValue(params_dict["Factor"])
        shader_node["parameters"]["value"].setValue(params_dict["Value"])
        shader_node['parameters']['curve']["interpolation"].setValue(convert_curve_interpolation(params_dict["curve"]))
        process_curve(shader_node['parameters']['curve'], params_dict["curve"])
    elif shader_type == "rgb_curves":
        build_curves_box(shader_node, params_dict, mode="rgb")
    elif shader_type == "vector_curves":
        build_curves_box(shader_node, params_dict, mode="vector")
    elif shader_type == "rgb_ramp":
        shader_node["parameters"]["fac"].setValue(params_dict["Factor"])
        shader_node['parameters']['ramp']["interpolation"].setValue(convert_ramp_interpolation(params_dict["interpolation"]))
        process_ramp(shader_node['parameters']['ramp'], params_dict["ramp_elements"])
    

def set_shader_parameters(shader_node, params_dict, shader_type):
    print(f"!!!! 🎱 ShaderType: {shader_type} !!!!!")
    if shader_type in SPECIAL_CASES:
        set_shader_specialCases(shader_node, params_dict, shader_type)
        return 
    
    for param_label, value in params_dict.items():
        plug_name = resolve_plug_name(param_label, shader_node, io="parameters", shader_type=shader_type)
        if plug_name == "UNSUPPORTED":
            print( f"😞 the parameter: '{param_label}' on shader: '{shader_type}', is unsupported by CyclesGaffer.")
            continue
        if not plug_name:
            if param_label.lower() == 'weight':
                # ignore the weight parameter that comes in every node and is irrelevant for translation.
                continue                
            # Special Cases
            specialcases = [
                'mix' in shader_type or "map_range" in shader_type and param_label.lower() in ['data_type'],
                shader_type in ["texture_coordinate", "uvmap"] and param_label.lower() in ['from_instancer'],
                shader_type == "attribute" and param_label.lower() == "attribute_type",
                shader_type == "ies_texture" and param_label.lower() == "mode"
            ]
            if True in specialcases:
                continue

            print(f"⚠️ Could not resolve param '{param_label}' for shader type '{shader_type}'")
            continue

        try:
            if shader_type == "vector_rotate" and value == "AXIS_ANGLE":
                value = "axis"
            elif isinstance(value, str) and not value in ["1D","2D","3D","4D"]:
                # Upercase labels and strings produce invalid results.
                value = value.lower()
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
        print("snn:!: ", src_node['name'].getValue())
        src_shader_type = src_node['name'].getValue()
        dst_shader_type = dst_node['name'].getValue()
        src_plug_name = resolve_plug_name(src_socket_label, src_node, io="out", shader_type=src_shader_type, isBox=isSrcBox)
        dst_plug_name = resolve_plug_name(dst_socket_label, dst_node, io="parameters", shader_type=dst_shader_type, isBox=isDstBox)
        print("src_plug_name::", src_plug_name)
        print("dst_plug_name::", dst_plug_name)
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

def create_basecheck_shader(mainShaderbox):
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

def sanitize_name(name: str) -> str:
    # Replace any non-alphanumeric or underscore with "_"
    safe = re.sub(r'[^0-9a-zA-Z_]', '_', name)
    # Optionally, avoid names starting with a digit
    if safe and safe[0].isdigit():
        safe = "_" + safe
    return safe

#### MAIN LOGIC ####
def create_material_network(mat_box, material, isGroup=False):
    nodes = material["nodes"]
    links = material.get("links", [])
    print("LINKS: \n", links)
    created_nodes = {}
    
    output_node_name =          ""
    group_output_node_name =    ""
    group_input_node_name =     ""

    if len(links) == 0:
        return "NOLINKS"
    
    ### NODE CREATION HANDLING ###
    for node_name, node_info in nodes.items():
        node_type = node_info.get("type", "")
        shader_type = shader_safe_type(node_info.get("cycles_type", ""))
        params = node_info.get("params", {})
        if node_type == "ShaderNodeOutputMaterial":
            output_node_name = node_name
            continue        
        if node_type == "NodeGroupOutput":
            group_output_node_name = node_name
            continue      
        if node_type == "NodeGroupInput":
            group_input_node_name = node_name
            continue


        safe_name = re.sub(r'\W|^(?=\d)', '_', node_name)
        
        # HANDLE GROUP NODES
        if node_type == "ShaderNodeGroup":
            group_box = Gaffer.Box(safe_name)
            mat_box.addChild(group_box)
            created_nodes[node_name] = safe_name
            
            group_data = node_info.get("group",{})
            for group_name, group in group_data.items(): # Only 1 group but we iterate to get the data
                group_box.setName(group_name)

                 # Safe_connect plug
                string_plug = Gaffer.StringPlug( "name", Gaffer.Plug.Direction.In, "group", Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic )
                group_box.addChild(string_plug)
                Gaffer.Metadata.registerValue(group_box["name"], 'plugValueWidget:type', '')
                #

                load_group_network(group_box, group)
            
            
        else:
            shader = GafferCycles.CyclesShader(safe_name)
            shader.loadShader(shader_type)
            shader.shaderType = shader_type
            mat_box.addChild(shader)
            created_nodes[node_name] = safe_name

            # print(f"➕ Created shader node: {node_name} as {safe_name}")
            set_shader_parameters(shader, params, shader_type)

    ### LINKS HANDLING ###
    shaderAssignments:list = []
    for link in links:
        #print("📦 Raw link:", link)
        if not isinstance(link, dict):
            continue

        from_node = link["from_node"]
        to_node = link["to_node"]
        from_socket = link["from_socket"]
        to_socket = link["to_socket"]
        

        # Safety
        if from_node == output_node_name or from_node == group_output_node_name: # Gaffer has no Output Node.
            continue

        # Group I/O
        if from_node == group_input_node_name:
            dst_node = mat_box[created_nodes[to_node]]
            dst_shader_type = dst_node['name'].getValue()
            dst_plug_name = resolve_plug_name(to_socket, dst_node, io="parameters", shader_type=dst_shader_type, isBox=False)
            print(f"dst_plug_name::::{dst_plug_name}")
            boxInPlug = Gaffer.BoxIO.promote( dst_node["parameters"][dst_plug_name] )
            groupInput = dst_node["parameters"][dst_plug_name].getInput().node()
            groupInput["name"].setValue(safe_plug_name(from_socket))            
        if to_node == group_output_node_name:
            src_node = mat_box[created_nodes[from_node]]
            src_shader_type = src_node['name'].getValue()            
            src_plug_name = resolve_plug_name(from_socket, src_node, io="out", shader_type=src_shader_type, isBox=False)
            boxOutPlug = Gaffer.BoxIO.promote(src_node['out'][src_plug_name])
            groupOutput = src_node['out'][src_plug_name].outputs()[0].node()
            groupOutput["name"].setValue(safe_plug_name(to_socket))

        # Material ShaderAssignments
        if to_node == output_node_name:   # We replace the output node with a Shader Assignment.
            final_shader = created_nodes.get(from_node)
            if final_shader:
                sh_assign = GafferScene.ShaderAssignment(f"ShaderAssign_{to_socket}")
                mat_box.addChild(sh_assign)
                sh_assign["shader"].setInput(mat_box[final_shader]["out"])
                shaderAssignments.append(sh_assign)
                print(f"🎯 Created ShaderAssignment and connected final shader {final_shader}")
            continue
        
        # connect input and outputs for this node
        if from_node in created_nodes and to_node in created_nodes:
            safe_connect(mat_box, created_nodes[from_node], from_socket, created_nodes[to_node], to_socket)
    
    return shaderAssignments
def load_group_network(group_box, group):
    groupAssignment = create_material_network(group_box, group, isGroup=True) # Create the Network


# --- Main material loader ---
def load_materials_from_json(json_path, parent):
    with open(json_path, "r") as f:
        material_data = json.load(f)

    # paths = [f"/{mat}" for mat in material_data.keys()]

    #Add Master Box
    materials_box = Gaffer.Box("Materials")
    parent.addChild(materials_box)

    # Add fallback check shader box
    fallback_box = Gaffer.Box("Fallback_Material")
    materials_box.addChild(fallback_box)
    Gaffer.Metadata.registerValue(fallback_box, 'nodeGadget:color', imath.Color3f(1, 0, 1))
    shassignnode = create_basecheck_shader(fallback_box)
    boxInOutHandling(shassignnode)
    last_out = fallback_box["out"]
    # Assign a start value to last_mat_box
    last_mat_box = fallback_box

    for mat_name, material in material_data.items():
        mat_name = sanitize_name(mat_name)
        print(f"\n🧱 Loading material: {mat_name}")
        mat_box = Gaffer.Box(mat_name)
        materials_box.addChild(mat_box)
        
        shaderAssignments = create_material_network(mat_box, material) # Create the Network

        if isinstance(shaderAssignments,str) and shaderAssignments=="NOLINKS":
            print(f"Material {mat_name} does not have a valid Network, probably has 0 connections.")
            Gaffer.Metadata.registerValue( mat_box, 'annotation:user:text', 'EMPTY MATERIAL\n' )
            Gaffer.Metadata.registerValue( mat_box, 'nodeGadget:color', imath.Color3f( 1, 0, 0 ) )
            continue

        if isinstance(shaderAssignments,list):
        # Promote boxIn/out to connect the material output shaders internally with the box flow
            def sort_by_role(nodes):
                order = ['ShaderAssign_Surface', 'ShaderAssign_Volume', 'ShaderAssign_Displacement']
                order_map = {k: i for i, k in enumerate(order)}
                def sort_key(node):
                    name = node.getName()
                    for k in order:
                        if k in name:
                            return order_map[k]
                    return len(order)  # fallback if no keyword matches
                return sorted(nodes, key=sort_key)
            
            shaderAssignments = sort_by_role(shaderAssignments) # Reorder the list to have the Blender order
            if len(shaderAssignments)==1:
                boxInOutHandling(shaderAssignments[0])        
            elif len(shaderAssignments)==2:
                shaderAssignments[1]['in'].setInput(shaderAssignments[0]['out'])
                boxInOutHandling(shaderAssignments[0],shaderAssignments[1])
            else:
                shaderAssignments[1]['in'].setInput(shaderAssignments[0]['out'])
                shaderAssignments[2]['in'].setInput(shaderAssignments[1]['out'])
                boxInOutHandling(shaderAssignments[0],shaderAssignments[2])

        # Connect in/out for box chaining
        mat_box["in"].setInput(last_out)
        last_out = mat_box["out"]
    
    #Handle InOut for master box
    if mat_box.getChild("out"):
        boxInOutHandling(fallback_box, mat_box)
        last_mat_box = mat_box
    else:
        boxInOutHandling(fallback_box, last_mat_box)


# Usage:
# Assuming you're running this in a Gaffer script editor or binding context
json_path = r"C:\GitHub\GafferShaderNetFromBlender\InProgressScripts\testFiles\materialNet.json"
load_materials_from_json(json_path, root)  # or a Gaffer.Box() if building modular