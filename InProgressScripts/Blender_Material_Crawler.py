import bpy
import mathutils
import json
import os




class MaterialExporter:
    def __init__(self):
        ######################
        #####  UI_STUFF  #####
        ######################
        self.process_selected_only = False
        
        #####################
        #####  MAPPING  #####
        #####################
        """Initialize with a path to the Blender→Cycles shader map JSON file."""
        script_dir = r"C:\GitHub\GafferShaderNetFromBlender\InProgressScripts"#os.path.dirname(os.path.abspath(__file__))
        mapping_path = os.path.join(script_dir, "blender_shader_class_to_cycles_name.json")
        with open(mapping_path, "r") as f:
            self.BLENDER_TO_CYCLES_SHADER_MAP = json.load(f)

    #####################################
    #-------------HIERARCHY-------------#
    #####################################

    def get_parent_path(self, obj):
        path = [obj.name]
        while obj.parent:
            obj = obj.parent
            path.append(obj.name)
        return "/".join(reversed(path))


    #########################################
    #-------------NODE HANDLING-------------#
    #########################################

    def blender_node_to_cycles(self, node):
        cycles_name = self.BLENDER_TO_CYCLES_SHADER_MAP.get(node.bl_idname)
        if cycles_name is None:
            print(f"⚠️ No mapping for {node.bl_idname}")
            return "unknown"
        # Special Cases.
        if node.bl_idname == 'ShaderNodeMix':
            if node.data_type == 'FLOAT':
                cycles_name = 'mix_float'
            elif node.data_type == 'VECTOR':
                if node.factor_mode == 'UNIFORM':
                    cycles_name = 'mix_vector'
                else:
                    cycles_name = 'mix_vector_non_uniform'
            elif node.data_type == 'RGBA':
                cycles_name = 'mix_color'
        if node.bl_idname == 'ShaderNodeMapRange':
            if node.data_type == 'FLOAT':
                cycles_name = 'map_range'
            elif node.data_type == 'VECTOR':
                cycles_name = 'vector_map_range'

        return cycles_name

    def get_image_filepath(self, img):
        imgpath = img.filepath.replace("\\", "/")
        imgpath = bpy.path.abspath(imgpath)
        imgpath = os.path.realpath(imgpath)

        return imgpath

    def handle_image_nodes(self, node):
        uiparams = {}
        if node.image:
            uiparams["image"] = self.get_image_filepath(node.image).replace("\\", "/")
            uiparams["Source"] = node.image.source
            uiparams["frame_duration"] = node.image_user.frame_duration
            uiparams["frame_offset"] = node.image_user.frame_offset
            uiparams["frame_start"] = node.image_user.frame_start
            uiparams["frame_current"] = node.image_user.frame_current
            uiparams["use_auto_refresh"] = node.image_user.use_auto_refresh
            uiparams["use_cyclic"] = node.image_user.use_cyclic
            uiparams["alpha_mode"] = node.image.alpha_mode
            uiparams["image_color_space"] = node.image.colorspace_settings.name

        return uiparams

    def to_serializable(self, socket):
        try:
            # is socket or value
            if hasattr(socket, "default_value"):
                val = socket.default_value
            else:
                val = socket
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

    def extract_node_extras(self, node):
        extras = {}
        socket_names = {s.name for s in node.inputs} | {s.name for s in node.outputs}
        skip_exact = {
            "bl_idname", "bl_label", "bl_description", "bl_icon", "bl_static_type",
            "name", "label", "type", "location", "select", "color_tag", "color",
            "width", "height", "bl_width_min", "bl_width_max", "bl_width_default",
            "bl_height_min", "bl_height_max", "bl_height_default", "inputs", "internal_links",
            "show_options", "show_preview", "show_texture", "use_custom_color",
            "parent", "hide", "mute", "warning_propagation", "debug_zone_body_lazy_function_graph",
            "debug_zone_lazy_function_graph", "dimensions", "draw_buttons", "draw_buttons_ext", 
            "input_template", "is_registered_node_type", "location_absolute", "output_template",
            "outputs", "poll", "poll_instance", "rna_type", "socket_value_update", "update",
            "color_mapping", "texture_mapping"
            
        }
        skip_specific ={}
        if node.bl_idname == "ShaderNodeTexPointDensity":
            skip_specific = {"cache_point_density", "calc_point_density", "calc_point_density_minmax", "object"}
        if node.bl_idname in ("ShaderNodeTexImage", "ShaderNodeTexEnvironment"):
            skip_specific = {"image", "image_user"}

        for attr in dir(node):
            if attr.startswith("_") or attr.startswith("bl_") or attr in socket_names or attr in skip_exact or attr in skip_specific:
                continue
            
            val = getattr(node, attr)
            #print(f"{attr} : {val}")
            if hasattr(node, attr):
                extras[attr] = self.to_serializable(val)
                
                
        return extras

    # Handles Only the extra Params and adds to the auto inputs
    def handle_ui_params(self, node):
        uiparams = {}
        if node.bl_idname in ("ShaderNodeVertexColor", "ShaderNodeAttribute", "ShaderNodeUVMap", "ShaderNodeVectorTransform"):
            attrs=["layer_name", "attribute_name", "attribute_type", "uv_map", "from_instancer"]
            attrs.extend(["vector_type", "convert_from", "convert_to"])
            for attr in attrs:
                if hasattr(node, attr):
                    uiparams[attr] = getattr(node, attr, "")

        if node.bl_idname == "ShaderNodeTexPointDensity":
            if node.object is not None:
                uiparams["Object"] = self.get_parent_path(node.object)
        #if node.bl_idname == "ShaderNodeTexImage":

        if node.bl_idname in ("ShaderNodeTexImage", "ShaderNodeTexEnvironment"):        
            uiparams.update(self.handle_image_nodes(node))

        return uiparams


    # Handles the whole object
    def handle_special_cases(self, node):
        specials = {}
        if node.bl_idname == "ShaderNodeMix":
            specials["data_type"] = node.data_type
            specials["clamp_factor"] = node.clamp_factor
            if node.data_type == 'RGBA':
                specials["blending_mode"] = node.blend_type
                specials["clamp_result"] = node.clamp_result
                specials["Factor_Float"] = node.inputs[0].default_value
                specials["A_Color"] = self.to_serializable(node.inputs[6])
                specials["B_Color"] = self.to_serializable(node.inputs[7])
            elif node.data_type == 'VECTOR':
                if node.factor_mode == 'UNIFORM':
                    specials["Factor_Float"] = node.inputs[0].default_value
                else:
                    specials["Factor_Vector"] = self.to_serializable(node.inputs[1])
                specials["A_Vector"] = self.to_serializable(node.inputs[4])
                specials["B_Vector"] = self.to_serializable(node.inputs[5])
            elif node.data_type == 'FLOAT':
                specials["Factor_Float"] = node.inputs[0].default_value
                specials["A_Float"] = node.inputs[2].default_value
                specials["B_Float"] = node.inputs[3].default_value
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
                specials["Vector"] = self.to_serializable(node.inputs[6])
                specials["Value"] = node.inputs[0].default_value
                specials["From Min"] = self.to_serializable(node.inputs[7])
                specials["From Max"] = self.to_serializable(node.inputs[8])
                specials["To Min"] = self.to_serializable(node.inputs[9])
                specials["To Max"] = self.to_serializable(node.inputs[10])
                specials["Steps"] = self.to_serializable(node.inputs[11])
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
                specials["Vector"] = self.to_serializable(node.inputs["Vector"])
                labels = ['x','y','z']
            if node.bl_idname =="ShaderNodeRGBCurve":
                specials["Color"] = self.to_serializable(node.inputs["Color"])
                labels = ['r','g','b','c']
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
                val = self.to_serializable(input_socket)
                specials[name] = val
        elif node.bl_idname == "ShaderNodeValue":
            specials["Value"] = node.outputs['Value'].default_value
        elif node.bl_idname == "ShaderNodeRGB":
            specials["Color"] = self.to_serializable(node.outputs['Color'])
        elif node.bl_idname == "ShaderNodeTexCoord":
            if node.object is not None:
                specials["Object"] = self.get_parent_path(node.object)
            specials["from_instancer"] = node.from_instancer

        return specials

    ############ WALK THE TREE ##############
    ### this is where the tracing happens ###
    #########################################
    def walk(self, socket, material, visited, node_info, links):
        # Go through all the links of the socket.
        for link in socket.links:
            from_node = link.from_node
            from_socket = link.from_socket
            to_node = link.to_socket.node
            to_socket = link.to_socket
            # Only process not visited nodes
            if from_node.name not in visited:
                visited.add(from_node.name)

                ## HANDLE GROUPS
                if from_node.type == 'GROUP':
                    params = {
                        inp.identifier: self.to_serializable(inp)
                        for inp in from_node.inputs
                        if hasattr(inp, "default_value")
                    }
                    group_data = self.trace_group_network(from_node)
                    node_info[from_node.name] = {
                        "type": from_node.bl_idname,
                        "cycles_type": "group",
                        "params": params,
                        "location": self.to_serializable(from_node.location),
                        "group": group_data   # embed the group subtree
                    }
                
                # HANDLE 99.9% of the cases here.
                else:
                    # Remap the UI name blender is using to a more appropiate technical cycles name, and handle special cases
                    cycles_type = self.blender_node_to_cycles(from_node)
                    # Handle cases where shader could not be mapped
                    if cycles_type == "unknown":
                        print("On ",material.name, " the node ", from_node.name, " of Type: ", from_node.bl_idname, " mapped to unknown.")
                        return None
                    
                    # PARAMETERS
                    # We check for special handling and if the params dict is not set, means was not special and we proceed with regular node handling.
                    params = self.handle_special_cases(from_node)            
                    if len(params)==0:
                        params = {
                            inp.identifier: self.to_serializable(inp)
                            for inp in from_node.inputs
                            if hasattr(inp, "default_value")
                        }
                        params.update(self.extract_node_extras(from_node))
                        params.update(self.handle_ui_params(from_node))

                    # Set the dictionary to setrialize
                    
                    node_info[from_node.name] = {
                        "type": from_node.bl_idname,
                        "cycles_type": cycles_type,
                        "params": params,
                        "location": self.to_serializable(from_node.location)
                    }

                # We do the navigation backwards to other nodes connected to this one's inputs
                for input_socket in from_node.inputs:
                    if input_socket.is_linked:
                        self.walk(socket=input_socket, material=material, visited=visited, node_info=node_info, links=links)

            # Only add link if the to_node (downstream) is already in visited
            if to_node.name in visited:
                linkdict = {
                    "from_node": from_node.name,
                    "from_socket": from_socket.identifier,
                    "to_node": to_node.name,
                    "to_socket": to_socket.identifier
                }
                if not linkdict in links:
                    links.append(linkdict)
        
        return "SUCCESS"

    def trace_group_network(self, group_node):
        group_tree = group_node.node_tree
        nodes = group_tree.nodes

        output_node = next((n for n in nodes if n.type == 'GROUP_OUTPUT' and n.is_active_output), None)
        if output_node is None:
            print(f"No group Output found in {group_node.name}")
            return None
            
        visited = set()
        node_info = {}
        links = []    

        # add the output node to the dictionary nodes
        visited.add(output_node.name)
        node_info[output_node.name] = {
            "type": output_node.bl_idname,
            "cycles_type": self.blender_node_to_cycles(output_node),
            "params": {},
            "location": list(output_node.location)
        }
        # Do the node net navigation, Start from Surface / Displacement / Volume.
        for socket in output_node.inputs:
            if socket.is_linked:
                for link in socket.links:
                    success = self.walk(socket=link.from_socket, material=group_node, visited=visited, node_info=node_info, links=links)
                    if not success:
                        print(f"{group_node.name} encountered an error and the Matiral won't be processed")
                        return None
        # Create a map for sockets that goes from identifier to name.
        socketmap = {}
        for input in group_node.inputs:
            socketmap.update({input.identifier : input.name})
        for output in group_node.outputs:
            socketmap.update({output.identifier : output.name})
        return {
            group_node.name: {
                "nodes": node_info,
                "links": links,
                "socket_map":socketmap
            }
        }


    ### START THE MAIN TRACE FOR A NETWORK ###
    def trace_shader_network(self, material):
        if not material.use_nodes:
            print(f"{material.name} has no nodes.")
            return None

        tree = material.node_tree
        nodes = tree.nodes

        output_node = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output), None)
        if output_node is None:
            print(f"No Material Output found in {material.name}")
            return None

        
        visited = set()
        node_info = {}
        links = []    

        # add the output node to the dictionary nodes
        visited.add(output_node.name)
        node_info[output_node.name] = {
            "type": output_node.bl_idname,
            "cycles_type": self.blender_node_to_cycles(output_node),
            "params": {},
            "location": list(output_node.location)
        }
        # Do the node net navigation, Start from Surface / Displacement / Volume.
        for socket_name in ("Surface", "Displacement", "Volume"):
            if socket_name in output_node.inputs and output_node.inputs[socket_name].is_linked:
                for link in output_node.inputs[socket_name].links:
                    success = self.walk(socket=link.from_socket, material=material, visited=visited, node_info=node_info, links=links)
                    if not success:
                        print(f"{material.name} encountered an error and the Matiral won't be processed")
                        return None
        return {
            material.name: {
                "nodes": node_info,
                "links": links
            }
        }

    #########################################
    #-------------EXPORT ENTRY--------------#
    #########################################
    def get_serialized_dict(self) -> dict:
        all_materials_data = {}
        mat_iter_collection = bpy.data.materials
        if self.process_selected_only:
            # change mat_iter_collection for a collection of selected only.
            pass
        for mat in mat_iter_collection:
            data = self.trace_shader_network(mat)
            if data:
                all_materials_data.update(data)

        return all_materials_data
        


    def export_all(self, filepath):
        serialized_dict = self.get_serialized_dict()
        with open(filepath, 'w') as f:
            json.dump(serialized_dict, f, indent=2)
        print(f"\n✅ Shader network exported to {filepath}")


# Example usage
if __name__ == "__main__":
    script_dir = r"C:\GitHub\GafferShaderNetFromBlender\InProgressScripts"
    # mapping_path = os.path.join(script_dir, "blender_shader_class_to_cycles_name.json")
    output_path = os.path.join(script_dir, "testFiles", "materialNet.json")

    exporter = MaterialExporter()
    exporter.export_all(output_path)
