import Gaffer
import GafferUI
import GafferScene
import IECore
import imath
import os
from MagicHammer.CreateShaderNet.GafferCreateShaderNet import create_networks


# def connect_in_graph(node):
# 	focusNode = node.parent.getFocus()
	
# 	if not focusNode == None:

# 		#Create Main BoxNode to hold shaders
# 		mainBox = node

# 		#Get nodes connected to Focus and plug the box node
# 		for output in focusNode["out"].outputs():
# 			finalnode = output.node()
# 			finalnodeinplug = output
# 			plugname = finalnodeinplug.getName()
# 			finalnode[plugname].setInput(mainBox["out"])		

# 		#Connect into the graph
# 		mainBox["in"].setInput(focusNode["out"])


def setup_box(node, code):
	mainShaderbox = node
	
	mainShaderbox.addChild( Gaffer.V2fPlug( "__uiPosition", defaultValue = imath.V2f( 0, 0 ), flags = Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic, ) )
	mainShaderbox.addChild( Gaffer.StringPlug( "updateList", defaultValue = '', flags = Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic, ) )
	mainShaderbox.addChild( Gaffer.StringPlug( "shotsList", defaultValue = '', flags = Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic, ) )
	mainShaderbox.addChild( Gaffer.StringPlug( "currentShot", defaultValue = '', flags = Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic, ) )

	Gaffer.Metadata.registerValue( mainShaderbox, 'uiEditor:emptySections', IECore.StringVectorData( [  ] ) )
	Gaffer.Metadata.registerValue( mainShaderbox, 'uiEditor:emptySectionIndices', IECore.IntVectorData( [  ] ) )

	Gaffer.Metadata.registerValue( mainShaderbox["updateList"], 'nodule:type', '' )
	Gaffer.Metadata.registerValue( mainShaderbox["updateList"], 'layout:section', 'Settings' )
	Gaffer.Metadata.registerValue( mainShaderbox["updateList"], 'plugValueWidget:type', 'GafferUI.ButtonPlugValueWidget' )
	Gaffer.Metadata.registerValue( mainShaderbox["updateList"], 'layout:accessory', False )

	Gaffer.Metadata.registerValue( mainShaderbox["updateList"], 'buttonPlugValueWidget:clicked', code )

	Gaffer.Metadata.registerValue( mainShaderbox["updateList"], 'description', 'es un boton' )
	Gaffer.Metadata.registerValue( mainShaderbox["updateList"], 'label', 'Create Material Networks' )
	Gaffer.Metadata.registerValue( mainShaderbox["updateList"], 'layout:index', -1 )

	# in plug
	mainShaderbox.addChild( Gaffer.BoxIn( "BoxIn" ) )
	mainShaderbox["BoxIn"].setup( GafferScene.ScenePlug( "out", ) )
	# out plug
	mainShaderbox.addChild( Gaffer.BoxOut( "BoxOut" ) )
	mainShaderbox["BoxOut"].setup( GafferScene.ScenePlug( "in", ) )

def __cycmatnetextract() :
	return Gaffer.Box( "MultiShotsBox" )


def __cycmatnetextractPostCreator( node, menu ) :
	## BUTTON CODE ##
	code:str = ""
	code += "from MagicHammer.CreateShaderNet.GafferCreateShaderNet import create_networks\n"
	code += "node = plug.node()\n"
	code += "create_networks( node )"
	################

	setup_box( node, code )

nodeMenu = GafferUI.NodeMenu.acquire( application )

nodeMenu.append(
	path = "/Cycles/Pipeline/CyclesMaterialNetworkExtractor",
	nodeCreator = __cycmatnetextract,
	postCreator = __cycmatnetextractPostCreator,
	searchText = " CyclesMaterialNetworkExtractor"
)