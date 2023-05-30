import re
import IECore
import IECoreScene
import GafferCycles
import Gaffer
import GafferScene

def create_shader_box(boxparent, boxname):
	boxNode = Gaffer.Box(boxname)
	boxparent.addChild(boxNode)
	# in plug
	boxNode.addChild( Gaffer.BoxIn( "BoxIn" ) )
	boxNode["BoxIn"].setup( GafferScene.ScenePlug( "out", ) )
	# out plug
	boxNode.addChild( Gaffer.BoxOut( "BoxOut" ) )
	boxNode["BoxOut"].setup( GafferScene.ScenePlug( "in", ) )
	# return the box
	return boxNode

def connect_in_out(parentbox, lastbox, box):
	bxout = parentbox['BoxOut']
	bxin = lastbox
	if parentbox==lastbox:
		bxin = parentbox["BoxIn"]
	#Connect
	bxout["in"].setInput(box["out"])
	box["in"].setInput(bxin["out"])
	#Optionaly set filter

def connect_shaderassignment(shassignnode, boxnode, path = ""):
	bxout = boxnode['BoxOut']
	bxin = boxnode["BoxIn"]
	#Connect
	bxout["in"].setInput(shassignnode["out"])
	shassignnode["in"].setInput(bxin["out"])
	# Filter path
	if not path == "":
		pathFilter = GafferScene.PathFilter()
		boxnode.addChild( pathFilter )
		shassignnode['filter'].setInput( pathFilter['out'] )
		##Filter
		#paths.setValue( IECore.StringVectorData( [ path ] ) )
		paths = pathFilter["paths"]
		ar = paths.getValue()
		ar.append(path)
		paths.setValue(ar)


def transfer_shader_parameters(source, target):
	sourceparams = source["parameters"].items()
	
	#print(type(params))
	#print(params)
	for p,v in sourceparams:
		#print("\t\t\t", p, v)
		target["parameters"][p] = v

## Hay que pasar el network desde python con el codigo que ya se probo
def convert_cyc_shaders(surface_attr, network, path, ParentShaderBox, shadernumber=0):
	print("||||||||||||||||||||| ", surface_attr,network, " |||||||||||||||||||||")
	if isinstance( network, IECoreScene.ShaderNetwork ) :
		output_shader = None # Set variable for output shader
		print("esshader")
		#AddShaderAssignmentmyBox = Gaffer.Box("myShaderBox")
		boxname = "myShaderBox"+str(shadernumber)		
		shaderbox = create_shader_box(ParentShaderBox, boxname)
		
		myShaderAssignment = GafferScene.ShaderAssignment()
		shaderbox.addChild( myShaderAssignment )
		connect_shaderassignment(myShaderAssignment, shaderbox, path)

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
				shaderbox.addChild( myShader )				
				
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
				
	out = shaderbox[output_shader]
	shaderbox['ShaderAssignment']['shader'].setInput(out['out'])
	#Set connections
	for nodeconnections in connections:
		for connection in nodeconnections:
			src = connection.source
			dst = connection.destination
			shaderbox[dst.shader]["parameters"][dst.name].setInput(shaderbox[src.shader]['out'][src.name])
	
	return shaderbox



########### INICIO ############
#Get Focus node
focusNode = root.getFocus()

#Create Main BoxNode to hold shaders
mainBox = create_shader_box(root, "MainShaderBox")

#Get nodes connected to Focus and plug the box node
for output in focusNode["out"].outputs():
	finalnode = output.node()
	finalnodeinplug = output
	plugname = finalnodeinplug.getName()
	finalnode[plugname].setInput(mainBox["out"])		

#Connect into the graph
mainBox["in"].setInput(focusNode["out"])

##Traverse hierarchy
def visit( scene, path ):
	shadercount = 0
	lastnode = mainBox
	for childName in scene.childNames( path ) :
		#print(childName)
		newpath = path.rstrip( "/" ) + "/" + str( childName )
		if scene.object(newpath).typeName() == "MeshPrimitive":
			attr = scene.attributes(newpath)
			if 'cycles:surface' in attr:
				## QUERY ATTRIBUTE ##
				shaderNet = attr['cycles:surface']
				#### MAKE SHADERS ####
				shaderbox = convert_cyc_shaders("cycles:surface", shaderNet, newpath, mainBox, shadercount)
				connect_in_out(mainBox, lastnode, shaderbox)
				lastnode = shaderbox
				shadercount += 1
		visit( scene, newpath )

node = focusNode
visit( node["out"], "/" )



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

"""
### FILTER ###
root['PathFilter3']["paths"].setValue( IECore.StringVectorData( [ '/world/geometry/sphere', "asd" ] ) )

paths = root['PathFilter3']["paths"]

ar = paths.getValue()

ar.append("holi")

for p in ar:
	print(p)

paths.setValue(ar)
"""