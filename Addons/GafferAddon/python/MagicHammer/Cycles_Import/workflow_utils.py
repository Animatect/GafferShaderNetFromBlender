import Gaffer
import GafferUI
import GafferScene



def focus_node_in_box(root, materials_box, selection):    
    # Get the script window
    sw = GafferUI.ScriptWindow.acquire(root)
    # Grab the first GraphEditor
    graphEditor = sw.getLayout().editors(GafferUI.GraphEditor)[0]
    # Set the GraphEditor root to the Box
    graphEditor.graphGadget().setRoot(materials_box)
    # Focus on the current selection
    graphEditor.frame(selection)

def select_matchig_filters(root, materials_box, targetPath):
    # clear selection
    root.selection().clear()
    # Loop over child nodes inside the Box
    for node in materials_box.children():
        if isinstance(node, GafferScene.PathFilter):
            # PathFilter has a 'paths' plug (StringVectorDataPlug)
            paths = node["paths"].getValue()
            if targetPath in paths:
                print("Match found in node:", node.getName())
                root.selection().add(node)

    return root.selection()

def find_loc_material(blenderBox):
    # The path we want to match
    targetPath:str = blenderBox['find_path'].getValue()
    materials_box = blenderBox.getChild('Materials')
    root = Gaffer.ScriptNode( "ScriptNode" )
    if materials_box:
        if not targetPath == '':
            selection = select_matchig_filters(root, materials_box, targetPath)
            if selection.size() > 0:
                focus_node_in_box(root, materials_box, selection)
            else:
                print("Didn't find Material for that location inside the Materials box.")
        else:
            print("Path is empty, drag a location to the text field")
    else:
        print("there is no material box with the default 'Materials' name inside this Blender scene node.")