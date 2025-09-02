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
    ) # type: ignore

    root_prim_path: bpy.props.StringProperty(
        name="Root Prim",
        description="Name of the root prim under which everything is grouped",
        default="/root"
    ) # type: ignore


    selection_only: bpy.props.BoolProperty(
        name="Selection Only",
        description="Export only selected objects",
        default=False
    ) # type: ignore


    visible_only: bpy.props.BoolProperty(
        name="Visible Only",
        description="Export only visible objects",
        default=True
    ) # type: ignore


    export_animation: bpy.props.BoolProperty(
        name="Animation",
        description="Export keyframe animation",
        default=False
    ) # type: ignore


    use_settings: bpy.props.EnumProperty(
        name="Use Settings For",
        description="Choose which settings to use for modifiers/visibility",
        items=[
            ("RENDER", "Render", ""),
            ("VIEWPORT", "Viewport", "")
        ],
        default="RENDER"
    ) # type: ignore


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
    ) # type: ignore


    rename_uvmaps: bpy.props.BoolProperty(
        name="Rename UV Maps",
        description="Rename exported UV maps to be unique",
        default=False
    ) # type: ignore


    export_normals: bpy.props.BoolProperty(
        name="Normals",
        description="Export normals",
        default=True
    ) # type: ignore


    use_instancing: bpy.props.BoolProperty(
        name="Use Instancing",
        description="Export object data as instances when possible",
        default=True
    ) # type: ignore


    # --- Rigging ---
    export_blendshapes: bpy.props.BoolProperty(
        name="Shape Keys",
        description="Export shape keys (blend shapes)",
        default=True
    ) # type: ignore


    export_skins: bpy.props.BoolProperty(
        name="Armatures",
        description="Export armature (skin) data",
        default=True
    ) # type: ignore


    export_bones: bpy.props.BoolProperty(
        name="Only Deform Bones",
        description="Export only deform bones (skip non-deforming)",
        default=False
    ) # type: ignore


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
        try:
            bpy.ops.wm.usd_export(
                filepath=self.filepath,
                root_prim_path=self.root_prim_path,
                selected_objects_only=self.selection_only,
                visible_objects_only=self.visible_only,
                export_animation=self.export_animation,
                evaluation_mode=self.use_settings,

                export_meshes = self.export_meshes,
                export_lights = self.export_lights,
                export_cameras = self.export_cameras,
                export_curves = self.export_curves,
                export_points = self.export_pointclouds,
                export_volumes = self.export_volumes,
                export_hair = self.export_hair,
                convert_world_material = self.export_world,

                export_uvmaps=self.export_uvmaps,
                rename_uvmaps =self.rename_uvmaps,
                export_normals=self.export_normals,
                export_materials=False,       # 🚫 No materials
                use_instancing=self.use_instancing,
                export_shapekeys =self.export_blendshapes,
                export_armatures =self.export_skins,
                only_deform_bones =self.export_bones,
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