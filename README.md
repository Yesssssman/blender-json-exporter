# Epic Fight Animation & Model exporter

This plugin is specially created for Minecraft - Epic Fight development, in blender 2.79 version.

## Applying to your blender

1. Download the whole source code.
2. Go to the folder where blender is installed, move all files under /2.79/scripts/addons/io_export_mc_json/. (Last folder name is example)
3. Go to the Blender > File > User Preferences > Add-ons, And find the add-on named "Import-Export: Minecraft Model Json Exporter"
4. Check to the checkbox and save user settings
5. Now you can see the exporter named "Animated Minecraft Model" is activated!

## About the bug and supports

Since this exporter is designed for a very restricted purpose, I won't provide any support. The mesh, armature, and animation data must be created first to export the model properly.

## Changelog

1.0.3 - Ported it to Blender 3.6 (Credits: box7805)
1.0.2: Added the part ditingushing function by the vertex group it will store all vectices in the vertex group which is the name ends with "_mesh"
1.0.1: Separated the option "export model" to "export mesh" and "export armature". This is because the armature data is useless to armors.
	Changed the hidden joints not to be exported
1.0.0: Created

## Credits
box7805 - Blender 3.6 exporter