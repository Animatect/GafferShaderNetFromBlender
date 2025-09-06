import Gaffer
import GafferCycles
import GafferScene
import IECore
import IECoreScene
import imath

def create_Scene(blenderBox):
	parent = blenderBox.parent()
	# --------------------------------------------------
	# Add Catalogue
	# --------------------------------------------------
	catalogue = GafferScene.Catalogue( "Catalogue" )
	parent.addChild( catalogue )
	catalogue["directory"].setValue( '${project:rootDirectory}/catalogues/${script:name}' )

	# --------------------------------------------------
	# Add Interactive Render
	# --------------------------------------------------
	InteractiveRender = GafferScene.InteractiveRender( "InteractiveRender" )
	parent.addChild( InteractiveRender )

	# --------------------------------------------------
	# Add Outputs node
	# --------------------------------------------------
	outputs = GafferScene.Outputs("Outputs")
	parent.addChild(outputs)

	# Output 1 : Beauty_Denoise
	outputs.addOutput(
		"Interactive/Beauty_Denoise",
		IECoreScene.Output(
			"beauty",      # fileName
			"ieDisplay",   # driver
			"rgba",        # data
			{
				"remoteDisplayType": "GafferScene::GafferDisplayDriver",
				"displayPort": "${image:catalogue:port}",
				"displayHost": "localhost",
				"driverType": "ClientDisplayDriver",
				"catalogue:imageName": "Image",
				"quantize": IECore.IntVectorData([0,0,0,0]),
				"denoise": True,   # custom param
			}
		)
	)

	# Output 2 : Beauty
	outputs.addOutput(
		"Interactive/Beauty",
		IECoreScene.Output(
			"beauty",      # fileName
			"ieDisplay",   # driver
			"rgba",        # data
			{
				"remoteDisplayType": "GafferScene::GafferDisplayDriver",
				"displayPort": "${image:catalogue:port}",
				"displayHost": "localhost",
				"driverType": "ClientDisplayDriver",
				"catalogue:imageName": "Image",
				"quantize": IECore.IntVectorData([0,0,0,0]),
			}
		)
	)
	# Connect Outputs into InteractiveRenderer
	InteractiveRender["in"].setInput(outputs["out"])

	# --------------------------------------------------
	# Add a Cycles options node
	# --------------------------------------------------
	cyclesOptions = GafferCycles.CyclesOptions("CyclesOptions")
	parent.addChild(cyclesOptions)
	cyclesOptions["options"]["cycles:device"]["value"].setValue("OPTIX:00")
	cyclesOptions["options"]["cycles:integrator:denoiser_type"]["value"].setValue("optix")

	# Connect options into Outputs
	outputs["in"].setInput(cyclesOptions["out"])

	# --------------------------------------------------
	# Example: add a Cycles background shader
	# --------------------------------------------------
	bg = GafferCycles.CyclesBackground("CyclesBackground")
	parent.addChild(bg)

	emission = GafferCycles.CyclesShader("emission")
	parent.addChild(emission)
	emission.loadShader("emission")

	bg["shader"].setInput(emission["out"]["emission"])

	# --------------------------------------------------
	# Add StandardOptions
	# --------------------------------------------------
	stdOptions = GafferScene.StandardOptions("StandardOptions")
	parent.addChild(stdOptions)
	stdOptions["options"]["render:resolution"]["value"].setValue(imath.V2i(1920, 1080))
	stdOptions["options"]["render:resolution"]["enabled"].setValue(True)
	stdOptions["options"]["render:defaultRenderer"]["value"].setValue("Cycles")
	stdOptions["options"]["render:defaultRenderer"]["enabled"].setValue(True)

	# Chain them together
	cyclesOptions["in"].setInput(stdOptions["out"])
	stdOptions["in"].setInput(bg["out"])

	# --------------------------------------------------
	# Connect the box if Possible
	# --------------------------------------------------
	if blenderBox.getChild('out'):
		bg["in"].setInput(blenderBox["out"])
