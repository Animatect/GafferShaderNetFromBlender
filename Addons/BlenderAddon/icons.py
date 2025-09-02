import bpy
import bpy.utils.previews
import os

preview_collections = {}

def register_icons():
    pcoll = bpy.utils.previews.new()
    icons_dir = os.path.join(os.path.dirname(__file__), "icons")
    icon_path = os.path.join(icons_dir, "gaffer.png")  # safer than .ico
    pcoll.load("my_icon", icon_path, 'IMAGE')
    preview_collections["main"] = pcoll

def unregister_icons():    
    for pcoll in preview_collections.values():
        bpy.utils.previews.remove(pcoll)
    preview_collections.clear()
