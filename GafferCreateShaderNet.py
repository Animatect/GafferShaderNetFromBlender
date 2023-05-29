import re
import IECore
import IECoreScene
import GafferCycles
import Gaffer

def transfer_shader_parameters(source, target):
	sourceparams = source["parameters"].items()
	
	#print(type(params))
	#print(params)
	for p,v in sourceparams:
		#print("\t\t\t", p, v)
		target["parameters"][p] = v

def convert_cyc_shaders(surface_attr, network):
	print("||||||||||||||||||||| ", surface_attr,network, " |||||||||||||||||||||")
	if isinstance( network, IECoreScene.ShaderNetwork ) :
		output_shader = None # Set variable for output shader
		print("esshader")
		#AddShaderAssignmentmyBox = Gaffer.Box("myShaderBox")
		boxname = "myShaderBox"
		myBox = Gaffer.Box(boxname)
		root.addChild(myBox)		
		
		myShaderAssignment = GafferScene.ShaderAssignment()
		root[boxname].addChild( myShaderAssignment )
		
		node_dict = {}
		connection_dict = {}
		connections = []
		parameters = None
		
		network_output_shader = network.getOutput().shader # Store output shader name
		for shader in sorted(network.shaders()):
				print("---------------------")
				print(shader)
				print("---------------------")
				shader_name = shader
				shader_type = network.shaders()[shader].name
				type = network.shaders()[shader].type
				print("\tCYCLES TYPE:\t", network.shaders()[shader_name].type)
				print("\tCYCLES_SHADER:\t", shader_type)
				
				# Check if shader is shader nework output
				if network_output_shader == shader:
					output_shader = shader
				
				# Store Connections for later fixes
				input_connections = network.inputConnections( shader )
				output_connections = network.outputConnections( shader )
				#print("\t intput:", shader, input_connections)
				#print("\t output:", shader, output_connections)
				
				#Add Shaders
				myShader = GafferCycles.CyclesShader(shader_name)
				myShader.loadShader(shader_type)
				root[boxname].addChild( myShader )				
				
				#Copy Parameters
				#transfer_shader_parameters(shader, myShader)
				print("!!!!!!!!!!!!")
				#print(network.shaders()[shader].parameters)
				parameters = network.shaders()[shader].parameters
				paramkeys = parameters.keys()
				for parameter in paramkeys:
					try:
						plug = myShader["parameters"][parameter]
						data = parameters.get(parameter)
						Gaffer.PlugAlgo.setValueFromData(plug,data)
					except:
						print(parameter)
				print("!!!!!!!!!!!!")
				
				#Store nodes and connections
				if len(output_connections) > 0:
					connections.append(output_connections)
				
	out = root[boxname][output_shader]
	root[boxname]['ShaderAssignment']['shader'].setInput(out['out'])
	#Set connections
	for nodeconnections in connections:
		for connection in nodeconnections:
			src = connection.source
			dst = connection.destination
			root[boxname][dst.shader]["parameters"][dst.name].setInput(root[boxname][src.shader]['out'][src.name])
	
	return parameters#connections
	
cyc_srf_net = root['AttributeQuery']["value"].getValue()
cyc_srf_exists = root["AttributeQuery"]["exists"]

#print("el surface es:", cyc_srf_net)
srf_result = None
if cyc_srf_exists:
# if False:
	srf_result = convert_cyc_shaders("cycles:surface", cyc_srf_net)


print(srf_result.items())

print(srf_result.get('direction'))
dir(srf_result)

for p, v in srf_result.items():
	print("\t\t\t", p, v)
	root['normal']["parameters"][p] = v

print(root['normal']["parameters"]['direction'])

plug = root['normal']["parameters"]['direction']
data = srf_result.get('direction')

Gaffer.PlugAlgo.setValueFromData(plug,data)

print(srf_result.keys())
""" name = "ShaderAssignment"
script = "myShaderAssignment = GafferScene.{}()".format(name)
exec(script)
root.addChild( myShaderAssignment ) """

"""
target = root['myShaderBox']['color1']
sourceparams = root['myShaderBox']['color']["parameters"].items()
#params = root['myShaderBox']['image_texture']["parameters"].items()

#print(type(params))
#print(params)
for p,v in sourceparams:
	print("\t\t\t", p, v)
	target["parameters"][p] = v
"""

"""
print(srf_result.items())

print(srf_result.get('direction'))
dir(srf_result)

for p, v in srf_result.items():
	print("\t\t\t", p, v)
	root['normal']["parameters"][p] = v

print(root['normal']["parameters"]['direction'])

plug = root['normal']["parameters"]['direction']
data = srf_result.get('direction')

Gaffer.PlugAlgo.setValueFromData(plug,data)


"""

######## TRAVERSE HIERARCHY ##########

"""
##Traverse hierarchy
def visit( scene, path ) :

	for childName in scene.childNames( path ) :
		#print(childName)
		newpath = path.rstrip( "/" ) + "/" + str( childName )
		if scene.object(newpath).typeName() == "MeshPrimitive":
			if 'cycles:surface' in scene.attributes(newpath):
				print( newpath )
				
				## QUERY EL ATTRIBUTE DESDE PYTHON ##
		visit( scene, newpath )

node = root['CustomAttributes']
visit( node["out"], "/" )

####tests####
attr = root['CustomAttributes']["out"].attributes( "/world/geometry/plane" )
print(attr.keys())

attrquery = attr['cycles:surface']
print(attrquery.typeName())

tmp = root['CustomAttributes']["out"].object( "/world/geometry/plane" )
print(tmp.typeName())

print(root['CustomAttributes']["out"].attributes( "/world/geometry/plane" ))

"""