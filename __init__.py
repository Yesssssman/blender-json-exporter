bl_info = {
    "name": "Minecraft Model Json Exporter",
    "author": "Yesssssman, box",
    "blender": (2, 80, 0),
    "category": "Import-Export",
    "location": "File > Import-Export",
    "description": "Epic Fight Mod JSON exporter ported to Blender 2.8+",
}

import bpy
from bpy.props import *
from bpy_extras.io_utils import ExportHelper

class ExportToJson(bpy.types.Operator, ExportHelper):
    """Export to Json that is specially designed for Epic Fight"""
    bl_idname = "export_mc.json"
    bl_label = "Export to Json for Minecraft"
    filename_ext = ".json"
    filter_glob = StringProperty(default="*.json", options={"HIDDEN"})
    bl_options = {'PRESET'}

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    export_anim : BoolProperty(
        name="Export Animation",
        description="Export animation data",
        default=True,
    )

    export_mesh : BoolProperty(
        name="Export Mesh",
        description="Export mesh data",
        default=True,
    )

    export_armature : BoolProperty(
        name="Export Armature",
        description="Export armature data",
        default=True,
    )

    def execute(self, context):
        if not self.filepath:
            raise Exception("Filepath not set")
        
        from . import export_mc_json
        return export_mc_json.save(context, **self.as_keywords())


def menu_func(self, context):
    self.layout.operator(ExportToJson.bl_idname, text="Animated Minecraft Model (.json)")

def register():
    bpy.utils.register_class(ExportToJson)
    bpy.types.TOPBAR_MT_file_export.append(menu_func)

def unregister():
    bpy.utils.unregister_class(ExportToJson)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func)

if __name__ == "__main__":
    register()