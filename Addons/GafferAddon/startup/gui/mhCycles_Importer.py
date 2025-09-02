import Gaffer
import GafferUI
import GafferScene
import IECore
import imath
import os
import GafferCycles


def setup_box(node, code):
	mainShaderbox = node
	
	mainShaderbox.addChild( Gaffer.V2fPlug( "__uiPosition", defaultValue = imath.V2f( 0, 0 ), flags = Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic, ) )
	# mainShaderbox.addChild( Gaffer.StringVectorDataPlug( "paths", defaultValue = IECore.StringVectorData( [  ] ), flags = Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic, ) )
	mainShaderbox.addChild( Gaffer.StringPlug( "updateList", defaultValue = '', flags = Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic, ) )
	
	# ---------- New Plugs ----------
	# File chooser
	mainShaderbox.addChild( 
		Gaffer.StringPlug( "fileName", defaultValue = "", flags = Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic ) 
	)

	# Split Sub Meshes checkbox
	mainShaderbox.addChild(
		Gaffer.BoolPlug( "splitSubMeshes", defaultValue = False, flags = Gaffer.Plug.Flags.Default | Gaffer.Plug.Flags.Dynamic )
	)

	# ---------- Metadata ----------
	Gaffer.Metadata.registerValue( mainShaderbox, 'uiEditor:emptySections', IECore.StringVectorData( [  ] ) )
	Gaffer.Metadata.registerValue( mainShaderbox, 'uiEditor:emptySectionIndices', IECore.IntVectorData( [  ] ) )

	# ## Paths ##
	# Gaffer.Metadata.registerValue( mainShaderbox["paths"], 'nodule:type', '' )
	# Gaffer.Metadata.registerValue( mainShaderbox["paths"], 'layout:section', 'Settings' )
	# Gaffer.Metadata.registerValue( mainShaderbox["paths"], 'layout:index', 0 )
	# mainShaderbox["paths"].setValue( IECore.StringVectorData( [ '/' ] ) )

	## File chooser UI
	Gaffer.Metadata.registerValue( mainShaderbox["fileName"], "nodule:type", "" )
	Gaffer.Metadata.registerValue( mainShaderbox["fileName"], "plugValueWidget:type", "GafferUI.FileSystemPathPlugValueWidget" )
	Gaffer.Metadata.registerValue( mainShaderbox["fileName"], "path:leaf", True )
	Gaffer.Metadata.registerValue( mainShaderbox["fileName"], "path:extensions", IECore.StringVectorData( [ "usd", "gcyc" ] ) )
	Gaffer.Metadata.registerValue( mainShaderbox["fileName"], "layout:section", "Settings" )
	Gaffer.Metadata.registerValue( mainShaderbox["fileName"], "label", "Input File" )
	Gaffer.Metadata.registerValue( mainShaderbox["fileName"], "description", "Select a USD or JSON file with matching name." )
	Gaffer.Metadata.registerValue( mainShaderbox["fileName"], "layout:index", 1 )

	## Split Sub Meshes checkbox
	Gaffer.Metadata.registerValue( mainShaderbox["splitSubMeshes"], "nodule:type", "" )
	Gaffer.Metadata.registerValue( mainShaderbox["splitSubMeshes"], "layout:section", "Settings" )
	Gaffer.Metadata.registerValue( mainShaderbox["splitSubMeshes"], "label", "Split Sub Meshes" )
	Gaffer.Metadata.registerValue( mainShaderbox["splitSubMeshes"], "description", "If enabled, sub-meshes are split when importing." )
	Gaffer.Metadata.registerValue( mainShaderbox["splitSubMeshes"], "layout:index", 2 )

	## Button ##
	Gaffer.Metadata.registerValue( mainShaderbox["updateList"], 'nodule:type', '' )
	Gaffer.Metadata.registerValue( mainShaderbox["updateList"], 'layout:section', 'Settings' )
	Gaffer.Metadata.registerValue( mainShaderbox["updateList"], 'plugValueWidget:type', 'GafferUI.ButtonPlugValueWidget' )
	Gaffer.Metadata.registerValue( mainShaderbox["updateList"], 'layout:accessory', False )

	Gaffer.Metadata.registerValue( mainShaderbox["updateList"], 'buttonPlugValueWidget:clicked', code )

	Gaffer.Metadata.registerValue( 
		mainShaderbox["updateList"], 
		'description', 
		'This button will import the usd and mat library files of the same name into this box.\n'+
		'Given the option it will split the multi material meshes into their own sub meshes to assign the propper material.\n'+
		'It can also import only the materials by importing a .gcyc file thah has no .usd file with the same name in the same folder.'
		)
	Gaffer.Metadata.registerValue( mainShaderbox["updateList"], 'label', 'Import Cycles Scene' )
	Gaffer.Metadata.registerValue( mainShaderbox["updateList"], 'layout:index', 3 )
	Gaffer.Metadata.registerValue( mainShaderbox["updateList"], 'layout:divider', True )

	## Color ##	
	Gaffer.Metadata.registerValue( mainShaderbox, 'nodeGadget:color', imath.Color3f( 0.815686, 0.352941, 0.156863 ) )

	# ---------- Icon ----------
	import inspect
	scriptPath = inspect.getsourcefile(lambda: None)
	gafferRoot = os.path.dirname(os.path.dirname(os.path.dirname(scriptPath)))# go up 
	iconPath = os.path.join(gafferRoot, "python", "MagicHammer","Cycles_Import","icons","blender.png")
	Gaffer.Metadata.registerValue( mainShaderbox, 'iconScale', 4.0 )
	
	if os.path.exists(iconPath):
		Gaffer.Metadata.registerValue(mainShaderbox, "icon", iconPath)
	
	Gaffer.Metadata.registerValue( mainShaderbox, 'noduleLayout:customGadget:addButtonTop:visible', False )
	Gaffer.Metadata.registerValue( mainShaderbox, 'noduleLayout:customGadget:addButtonBottom:visible', False )
	Gaffer.Metadata.registerValue( mainShaderbox, 'noduleLayout:customGadget:addButtonLeft:visible', False )
	Gaffer.Metadata.registerValue( mainShaderbox, 'noduleLayout:customGadget:addButtonRight:visible', False )

	# in plug
	# mainShaderbox.addChild( Gaffer.BoxIn( "BoxIn" ) )
	# mainShaderbox["BoxIn"].setup( GafferScene.ScenePlug( "out", ) )
	
	# # out plug
	# mainShaderbox.addChild( Gaffer.BoxOut( "BoxOut" ) )
	# mainShaderbox["BoxOut"].setup( GafferScene.ScenePlug( "in", ) )

def __cycmatnetextract() :
	return Gaffer.Box( "Cycles_Scene_Box" )


def __cycmatnetextractPostCreator( node, menu ) :
	## BUTTON CODE ##
	code:str = ""
	code += "from MagicHammer.Cycles_Import.import_Cycles_materials_to_Gaffer import create_networks\n"
	code += "node = plug.node()\n"
	code += "create_networks( node )"
	################

	setup_box( node, code )

## MAKE NODE ##
nodeMenu = GafferUI.NodeMenu.acquire( application )

nodeMenu.append(
	path = "/Cycles/Pipeline/Cycles_Importer",
	nodeCreator = __cycmatnetextract,
	postCreator = __cycmatnetextractPostCreator,
	searchText = " Cycles_Importer"
)