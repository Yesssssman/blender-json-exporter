bl_info = {
    "name": "Minecraft Model Json Exporter",
    "author": "Yesssssman",
    "blender": (2, 80, 0),
    "category": "Import-Export",
    "location": "File > Import-Export",
    "description":  "Specially designed exporter for developing Minecraft Epic Fight Mod"
}

import bpy
from bpy.props import *
from bpy_extras.io_utils import ExportHelper

class ExportToJson(bpy.types.Operator, ExportHelper):
    """Export to Json that specially designed for Epic Fight"""
    bl_idname = "export_mc.json"        # Unique identifier for buttons and menu items to reference.
    bl_label = "Export to Json for Minecraft"         # Display name in the interface.
    filename_ext = ".json"
    filter_glob = StringProperty(default="*.json", options={"HIDDEN"})

    @classmethod
    def poll( cls, context ):
        return context.active_object != None

    export_anim = BoolProperty(
        name="Export Animation",
        description="Export animation data",
        default=True,
    )

    export_mesh = BoolProperty(
        name="Export Mesh",
        description="Export mesh data",
        default=True,
    )

    export_armature = BoolProperty(
        name="Export Armature",
        description="Export armature data",
        default=True,
    )

    def execute(self, context):
        if not self.filepath:
            raise Exception("filepath not set")    
        keywords = self.as_keywords()
        print('keyward is ', keywords)
        
        from . import export_mc_json
        return export_mc_json.save(context, **keywords)

def menu_func( self, context ):
    self.layout.operator(ExportToJson.bl_idname, text="Animated Minecraft Model (.json)")

def register():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_export.append(menu_func)

def unregister():
    bpy.utils.register_module(__name__)
    bpy.types.INFO_MT_file_export.remove(menu_func)

if __name__ == "__main__":
    register()