import bpy

class EXPORT_OT_blender_to_gaffer(bpy.types.Operator):
    """Export with Blender→Gaffer pipeline"""
    bl_idname = "export_scene.blender_to_gaffer"
    bl_label = "Blender to Gaffer (.usd)"
    bl_options = {"PRESET"}

    # --- General ---
    filepath: bpy.props.StringProperty(
        name="File Path",
        description="Filepath to export USD",
        subtype="FILE_PATH"
    )

    root_prim_path: bpy.props.StringProperty(
        name="Root Prim",
        description="Name of the root prim under which everything is grouped",
        default="/root"
    )

    selection_only: bpy.props.BoolProperty(
        name="Selection Only",
        description="Export only selected objects",
        default=False
    )

    visible_only: bpy.props.BoolProperty(
        name="Visible Only",
        description="Export only visible objects",
        default=True
    )

    export_animation: bpy.props.BoolProperty(
        name="Animation",
        description="Export keyframe animation",
        default=False
    )

    use_settings: bpy.props.EnumProperty(
        name="Use Settings For",
        description="Choose which settings to use for modifiers/visibility",
        items=[
            ("RENDER", "Render", ""),
            ("VIEWPORT", "Viewport", "")
        ],
        default="RENDER"
    )

    # --- Object Types ---
    export_meshes: bpy.props.BoolProperty(name="Meshes", default=True)
    export_lights: bpy.props.BoolProperty(name="Lights", default=True)
    export_world: bpy.props.BoolProperty(name="World Dome Light", default=True)
    export_cameras: bpy.props.BoolProperty(name="Cameras", default=True)
    export_curves: bpy.props.BoolProperty(name="Curves", default=True)
    export_pointclouds: bpy.props.BoolProperty(name="PointClouds", default=True)
    export_volumes: bpy.props.BoolProperty(name="Volumes", default=True)
    export_hair: bpy.props.BoolProperty(name="Hair", default=True)

    # --- Geometry ---
    export_uvmaps: bpy.props.BoolProperty(
        name="UV Maps",
        description="Export UV maps",
        default=True
    )

    rename_uvmaps: bpy.props.BoolProperty(
        name="Rename UV Maps",
        description="Rename exported UV maps to be unique",
        default=False
    )

    export_normals: bpy.props.BoolProperty(
        name="Normals",
        description="Export normals",
        default=True
    )

    use_instancing: bpy.props.BoolProperty(
        name="Use Instancing",
        description="Export object data as instances when possible",
        default=True
    )

    # --- Rigging ---
    export_blendshapes: bpy.props.BoolProperty(
        name="Shape Keys",
        description="Export shape keys (blend shapes)",
        default=True
    )

    export_skins: bpy.props.BoolProperty(
        name="Armatures",
        description="Export armature (skin) data",
        default=True
    )

    export_bones: bpy.props.BoolProperty(
        name="Only Deform Bones",
        description="Export only deform bones (skip non-deforming)",
        default=False
    )

    # ------------------------------------------------------------------
    # Draw UI
    # ------------------------------------------------------------------
    def draw(self, context):
        layout = self.layout

        # General
        box = layout.box()
        box.label(text="General", icon="SCENE_DATA")
        box.prop(self, "root_prim_path")
        box.prop(self, "selection_only")
        box.prop(self, "visible_only")
        box.prop(self, "export_animation")
        box.prop(self, "use_settings")

        # Object Types
        box = layout.box()
        box.label(text="Object Types", icon="OBJECT_DATA")
        col = box.column(align=True)
        col.prop(self, "export_meshes")
        col.prop(self, "export_lights")
        col.prop(self, "export_world")
        col.prop(self, "export_cameras")
        col.prop(self, "export_curves")
        col.prop(self, "export_pointclouds")
        col.prop(self, "export_volumes")
        col.prop(self, "export_hair")

        # Geometry
        box = layout.box()
        box.label(text="Geometry", icon="MESH_DATA")
        box.prop(self, "export_uvmaps")
        box.prop(self, "rename_uvmaps")
        box.prop(self, "export_normals")
        box.prop(self, "use_instancing")

        # Rigging
        box = layout.box()
        box.label(text="Rigging", icon="ARMATURE_DATA")
        box.prop(self, "export_blendshapes")
        box.prop(self, "export_skins")
        box.prop(self, "export_bones")

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------
    def execute(self, context):
        # Build object types set
        obj_types = set()
        if self.export_meshes: obj_types.add("MESH")
        if self.export_lights: obj_types.add("LIGHT")
        if self.export_world: obj_types.add("WORLD")
        if self.export_cameras: obj_types.add("CAMERA")
        if self.export_curves: obj_types.add("CURVE")
        if self.export_pointclouds: obj_types.add("POINTCLOUD")
        if self.export_volumes: obj_types.add("VOLUME")
        if self.export_hair: obj_types.add("HAIR")

        try:
            bpy.ops.wm.usd_export(
                filepath=self.filepath,
                root_prim_path=self.root_prim_path,
                selected_objects_only=self.selection_only,
                visible_objects_only=self.visible_only,
                export_animation=self.export_animation,
                evaluation_mode=self.use_settings,
                export_object_types=obj_types,
                export_uvmaps=self.export_uvmaps,
                export_uvmaps_rename=self.rename_uvmaps,
                export_normals=self.export_normals,
                export_materials=False,       # 🚫 No materials
                use_instancing=self.use_instancing,
                export_blendshapes=self.export_blendshapes,
                export_skins=self.export_skins,
                export_bones=self.export_bones,
            )
        except Exception as e:
            self.report({'ERROR'}, f"USD export failed: {e}")
            return {'CANCELLED'}

        self.report({'INFO'}, f"USD exported to {self.filepath}")
        return {'FINISHED'}

    def invoke(self, context, event):
        # Default filename
        self.filepath = bpy.path.abspath("//export.usda")
        context.window_manager.fileselect_add(self)
        return {"RUNNING_MODAL"}



def menu_func_export(self, context):
    self.layout.operator(EXPORT_OT_blender_to_gaffer.bl_idname,
                         text="Blender to Gaffer (.usd)")


def register():
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)