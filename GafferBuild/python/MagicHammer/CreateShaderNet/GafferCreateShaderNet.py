import re
import IECore
import IECoreScene
import GafferCycles
import Gaffer
import GafferScene
import imath
import warnings


def visit( scene, path, initBox, mainBox, index = 0)->int:
		lastnode = initBox
		idx:int = index

		print( "la iteracion actual es {}".format( idx ) )

		for childName in scene.childNames( path ) :
			#print(childName)
			newpath = path.rstrip( "/" ) + "/" + str( childName )
			print("El path actual es: {}".format( newpath ) )
			if scene.object(newpath).typeName() == "MeshPrimitive":
				attr = scene.attributes(newpath)
				if 'cycles:surface' in attr:
					## QUERY ATTRIBUTE ##
					shaderNet = attr['cycles:surface']
					#### MAKE SHADERS ####
					shaderbox = convert_cyc_shaders("cycles:surface", shaderNet, newpath, mainBox, idx)
					#print( "El Shader {} es del tipo {}".format( shaderbox.getName(), str( type(shaderbox) ) ) )					
					#print( "El nombre del lastnode es {}  y es del tipo {}".format( lastnode.getName(), str( type(lastnode) ) ) )
					if idx == 0:
						
						print("idx0")
						connect_in_out(mainBox, lastnode, shaderbox, True)
					else:
						print("idxnot0")
						connect_in_out(mainBox, lastnode, shaderbox, False)
					lastnode = shaderbox
					#print( "El NUEVO nombre del lastnode es {}  y AHORA es del tipo {}".format( lastnode.getName(), str( type(lastnode) ) ) )
					idx += 1
			#We assign the values inside the recursive function variables to the variables outside to transport them correctly.
			idx, lastnode = visit( scene, newpath, lastnode, mainBox, idx)

		return idx, lastnode


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

def connect_in_out(parentbox, lastbox, box, isFirstIteration):
	bxout = parentbox['BoxOut']
	#bxin = lastbox
	print("el last box en la funcion es: {}".format( lastbox.getName() ) )
	print("es la primera iteracion = {}".format( str(isFirstIteration) ) )
	#if parentbox==lastbox:
	if isFirstIteration:
		bxin = parentbox["BoxIn"]
		bxout["in"].setInput(box["out"])
		box["in"].setInput(bxin["out"])
	#Connect
	else:
		bxin = lastbox		
		bxout["in"].setInput(box["out"])
		box["in"].setInput(bxin["out"])

def connect_shaderassignment(shassignnode, boxnode, path = ""):
	bxout = boxnode['BoxOut']
	bxin = boxnode["BoxIn"]
	#Connect
	bxout["in"].setInput(shassignnode["out"])
	shassignnode["in"].setInput(bxin["out"])
	# Filter path
	if not path == "":		
		### Create Filter Node ###
		pathFilter = GafferScene.PathFilter(boxnode.getName() + "_pathFilter")
		boxparent = boxnode.parent()
		boxparent.addChild(pathFilter)
		
		##set filter paths
		#paths.setValue( IECore.StringVectorData( [ path ] ) )
		paths = pathFilter["paths"]
		ar = paths.getValue()
		ar.append(path)
		paths.setValue(ar)

		## Connect Filter
		boxnode.addChild( Gaffer.BoxIn( "BoxIn1"  ) )
		boxnode["BoxIn1" ].setup( GafferScene.FilterPlug( "out", defaultValue = 0, minValue = 0, maxValue = 7, flags = Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.AcceptsDependencyCycles, ) )
		boxnode["BoxIn1"]["name"].setValue( 'filter' )

		Gaffer.Metadata.registerValue( boxnode["filter"], 'nodule:color', imath.Color3f( 0.689999998, 0.537800014, 0.228300005 ) )
		Gaffer.Metadata.registerValue( boxnode["filter"], 'description', 'The result of the filter. This should be connected into\nthe "filter" plug of a FilteredSceneProcessor.' )
		Gaffer.Metadata.registerValue( boxnode["filter"], 'plugValueWidget:type', '' )
		Gaffer.Metadata.registerValue( boxnode["filter"], 'noduleLayout:section', 'right' )
		
		boxnode["filter"].setInput( pathFilter["out"] )

		#Connect ShaderAssignment
		shassignnode['filter'].setInput( boxnode['BoxIn1']["out"] )



def transfer_shader_parameters(source, target):
	sourceparams = source["parameters"].items()
	
	#print(type(params))
	#print(params)
	for p,v in sourceparams:
		#print("\t\t\t", p, v)
		target["parameters"][p] = v

## Hay que pasar el network desde python con el codigo que ya se probo
def convert_cyc_shaders(surface_attr, network, path, ParentShaderBox, shadernumber:int = 0):
	print("||||||||||||||||||||| ", surface_attr,network, " |||||||||||||||||||||")
	if isinstance( network, IECoreScene.ShaderNetwork ) :
		output_shader = None # Set variable for output shader
		#AddShaderAssignmentmyBox = Gaffer.Box("myShaderBox")
		boxname = "ShaderNetwork_"+str(shadernumber).zfill(4)	
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

if not focusNode == None:

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
	node = focusNode
	numberofshaders, lastcreatednode = visit( node["out"], "/", mainBox, mainBox, 0 )

	print("Se crearon {} Shaders".format(str(numberofshaders)))

else:
	warnings.warn("No Focus Node Selected")



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

