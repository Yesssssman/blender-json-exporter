from collections import OrderedDict
from _ctypes import PyObj_FromPtr
import json
import re

import bmesh
import bpy
import math
import mathutils

class NoIndent(object):
    def __init__(self, value):
        self.value = value

class NoIndentEncoder(json.JSONEncoder):
    FORMAT_SPEC = '@@{}@@'
    regex = re.compile(FORMAT_SPEC.format(r'(\d+)'))

    def __init__(self, **kwargs):
        self.__sort_keys = kwargs.get('sort_keys', None)
        super(NoIndentEncoder, self).__init__(**kwargs)

    def default(self, obj):
        return (self.FORMAT_SPEC.format(id(obj)) if isinstance(obj, NoIndent) else super(NoIndentEncoder, self).default(obj))

    def encode(self, obj):
        format_spec = self.FORMAT_SPEC
        json_repr = super(NoIndentEncoder, self).encode(obj)

        for match in self.regex.finditer(json_repr):
            id = int(match.group(1))
            no_indent = PyObj_FromPtr(id)
            json_obj_repr = json.dumps(no_indent.value, sort_keys=self.__sort_keys)
            json_repr = json_repr.replace('"{}"'.format(format_spec.format(id)), json_obj_repr)
        return json_repr

def ensure_extension( filepath, extension ):
    if not filepath.lower().endswith( extension ):
        filepath += extension
    return filepath

def mesh_triangulate(src, dest):
    bm = bmesh.new()
    bm.from_mesh(src)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(dest)
    bm.free()

def veckey2d(v):
    return round(v.x, 4), round(v.y, 4)

def veckey3d(v):
    return round(v.x, 4), round(v.y, 4), round(v.z, 4)

def wrap_matrix(mat):
    return NoIndent([round(e, 6) for v in mat for e in v])

def create_array_dict(stride, count, array):
    ordered_dict = OrderedDict()
    ordered_dict['stride'] = stride
    ordered_dict['count'] = count
    ordered_dict['array'] = NoIndent(array)
    return ordered_dict

def export_mesh(obj, bones):
    obj_mesh = obj.to_mesh(bpy.context.scene, False, calc_tessface=False, settings='PREVIEW')
    triangulated_mesh = bpy.data.meshes.new('triangulated_mesh')
    mesh_triangulate(obj_mesh, triangulated_mesh)
    triangulated_mesh.calc_normals_split()
    
    owner_polygons = {}
    
    for f in triangulated_mesh.polygons:
        owners = [p for p in obj_mesh.polygons if all(x in [v for v in p.vertices] for x in [v for v in f.vertices])]
        
        if len(owners) != 1:
            raise Exception('triangulation error');
        
        owner_polygons[f] = owners[0]
    
    # export vertices
    position_array = [round(pos, 6) for v in triangulated_mesh.vertices for pos in v.co[:]]
    
    uv_array = []
    normal_array = []
    loops = triangulated_mesh.loops
    
    uv_unique_count = no_unique_count = 0
    # export normal data
    no_key = no_val = None
    normals_to_idx = {}
    no_get = normals_to_idx.get
    loops_to_normals = [0] * len(loops)
    
    for f in triangulated_mesh.polygons:
        for l_idx in f.loop_indices:
            no_key = veckey3d(loops[l_idx].normal)
            no_val = no_get(no_key)
            
            if no_val is None:
                no_val = normals_to_idx[no_key] = no_unique_count
                
                for n_val in no_key:
                    normal_array.append(n_val)
                
                no_unique_count += 1
            
            loops_to_normals[l_idx] = no_val
    
    del normals_to_idx, no_get, no_key, no_val
    
    # export uv data
    uv_layer = triangulated_mesh.uv_layers.active.data[:]
    uv = f_index = uv_index = uv_key = uv_val = uv_ls = None
    uv_face_mapping = [None] * len(triangulated_mesh.polygons)
    uv_dict = {}
    uv_get = uv_dict.get
    
    for f_index, f in enumerate(triangulated_mesh.polygons):
        uv_ls = uv_face_mapping[f_index] = []
        
        for uv_index, l_index in enumerate(f.loop_indices):
            uv = uv_layer[l_index].uv
            uv_key = veckey2d(uv)
            uv_val = uv_get(uv_key)
            
            if uv_val is None:
                uv_val = uv_dict[uv_key] = uv_unique_count
                
                for i, uv_cor in enumerate(uv):
                    uv_array.append(round(uv_cor if i % 2 == 0 else 1-uv_cor, 6))
                
                uv_unique_count += 1
            
            uv_ls.append(uv_val)
    
    del uv_dict, uv, f_index, uv_index, uv_ls, uv_get, uv_key, uv_val
    
    parts = {'noGroups': []}
    
    for vg in obj.vertex_groups:
        if vg.name[-5:] == "_mesh":
            parts[vg.name[:-5]] = []
    
    # export drawing indices
    for f_index, f in enumerate(triangulated_mesh.polygons):
        f_v = [(vi, triangulated_mesh.vertices[v_idx], l_idx) for vi, (v_idx, l_idx) in enumerate(zip(f.vertices, f.loop_indices))]
        
        polygons_part_indices = {}
        polygons_part_indices['noGruops'] = []
        
        for name in parts.keys():
            polygons_part_indices[name] = []
        
        for vi, v, li in f_v:
            mesh_vgs = [obj.vertex_groups[vg.group].name for vg in v.groups]
            mesh_vgs = list(filter(lambda x: x[-5:] == "_mesh", mesh_vgs))
            
            if len(mesh_vgs) == 0:
                i_list = polygons_part_indices['noGroups']
                i_list.append(v.index)
                i_list.append(uv_face_mapping[f_index][vi])
                i_list.append(loops_to_normals[li])
            else:
                for name in mesh_vgs:
                    i_list = polygons_part_indices[name[:-5]]
                    i_list.append(v.index)
                    i_list.append(uv_face_mapping[f_index][vi])
                    i_list.append(loops_to_normals[li])
        
        for part_name, i_list in polygons_part_indices.items():
            if len(i_list) // 3 == len(f.vertices):
                vg_names = [[obj.vertex_groups[vg.group].name[:-5] for vg in v.groups if obj.vertex_groups[vg.group].name[-5:] == '_mesh'] for v in [obj_mesh.vertices[vid] for vid in owner_polygons[f].vertices]]
                
                if all(part_name in names for names in vg_names):
                    parts[part_name].extend(i_list)
    
    output = OrderedDict()
    output['positions'] = create_array_dict(3, len(position_array) // 3, position_array)
    output['uvs'] = create_array_dict(2, len(uv_array) // 2, uv_array)
    output['normals'] = create_array_dict(3, len(normal_array) // 3, normal_array)
    
    # export skin weight data
    if bones is not None:
        vcounts = []
        weights = []
        vindices = []
        
        for v in triangulated_mesh.vertices :
            vc_val = 0;
            appended_joints = []
            weight_list = []
            weight_total = 0.0
            
            for vg in v.groups:
                if vg.group >= len(obj.vertex_groups):
                    continue
                w_val = max(min(vg.weight, 1.0), 0.0)
                name = obj.vertex_groups[vg.group].name
                if w_val > 0.0 and name not in appended_joints and name[-5:] != "_mesh":
                    appended_joints.append(name)
                    weight_total += w_val
                    weight_list.append((name, w_val))
            
            if weight_total == 0.0:
                weight_total += 1.0
                weight_list.append(('Root', 1.0))
                print("Warn: Vertex", v.index, "is not grouped")
            
            normalization = 1.0 / weight_total
            weight_list = [(name, round(e * normalization, 4)) for name, e in weight_list]
            
            for name, w_val in weight_list:
                vindices.append(bones.index(name) if name in bones else 0)
                if w_val not in weights:
                    weights.append(w_val)
                vindices.append(weights.index(w_val))
                vc_val+=1
            
            vcounts.append(vc_val)
        
        output['vcounts'] = create_array_dict(1, len(vcounts), vcounts)
        output['weights'] = create_array_dict(1, len(weights), weights)
        output['vindices'] = create_array_dict(1, len(vindices), vindices)
    
    output['parts'] = {}
    
    for k, v in parts.items():
        if len(v) > 0:
            output['parts'][k] = create_array_dict(3, len(v) // 3, v)
    
    return output

def export_armature(obj, export_visible_bones):
    def export_bones(b, list, dict, export_visible_bones):
        if export_visible_bones and b.hide:
            return
        
        list.append(b.name)
        matrix = b.matrix_local
        
        if (b.parent is not None):
            matrix = b.parent.matrix_local.inverted_safe() * matrix
        
        dict['name'] = b.name
        dict['transform'] = wrap_matrix(matrix)
        dict['children'] = [export_bones(child, list, OrderedDict(), export_visible_bones) for child in b.children]
        
        return dict
    
    output = OrderedDict()
    
    bones = []
    bone_hierarchy = []
    
    for b in obj.data.bones:
        if b.parent is not None:
            continue
        
        b_dic = export_bones(b, bones, OrderedDict(), export_visible_bones)
        bone_hierarchy.append(b_dic)
    
    output['joints'] = NoIndent(bones)
    output['hierarchy'] = bone_hierarchy
    
    return output

def export_animation(obj, bone_name_list, animation_format):
    scene = bpy.context.scene
    action = obj.animation_data.action
    bones = obj.data.bones
    dope_sheet = {}
    timelines = []
    output = []
    
    if action is not None:
        for curve in action.fcurves:
            keyframePoints = curve.keyframe_points
            name = curve.group.name
            
            if name not in dope_sheet:
                dope_sheet[name] = {'transform':[], 'timestamp':[]}
            
            for keyframe in keyframePoints:
                val = int(keyframe.co[0])
                
                if val not in dope_sheet[(name)]['timestamp']:
                    dope_sheet[(name)]['timestamp'].append(val)
                
                if val not in timelines:
                    timelines.append(val)
        
        timelines.sort()
        
        for t in timelines:
            scene.frame_set(t)
            
            for b in bones:
                if b.name not in dope_sheet:
                    dope_sheet[b.name] = {'transform':[], 'timestamp':[]}
                
                if t in dope_sheet[b.name]['timestamp'] or t == 0 or t == timelines[-1]:
                    matrix = obj.pose.bones[b.name].matrix.copy()
                    bone_local = b.matrix_local.copy()
                    
                    if animation_format == 'ATTR':
                        if b.parent is not None:
                            bone_local = b.parent.matrix_local.inverted_safe() * bone_local
                            parent_pose_invert = obj.pose.bones[b.parent.name].matrix.inverted_safe()
                            matrix = bone_local.inverted_safe() * parent_pose_invert * matrix
                        else:
                            matrix = bone_local.inverted_safe() * matrix
                        
                        if t not in dope_sheet[b.name]['timestamp']:
                            dope_sheet[b.name]['timestamp'].append(t)
                        
                        loc, rot, sca = matrix.decompose()
                        transformdict = OrderedDict()
                        transformdict['loc'] = NoIndent([round(v, 6) for v in loc])
                        transformdict['rot'] = NoIndent([round(v, 6) for v in rot])
                        transformdict['sca'] = NoIndent([round(v, 6) for v in sca])
                        dope_sheet[b.name]['transform'].append(transformdict)
                    else:
                        if (b.parent is not None):
                            parent_pose_invert = obj.pose.bones[b.parent.name].matrix.inverted_safe()
                            matrix = parent_pose_invert * matrix
                        
                        if t not in dope_sheet[b.name]['timestamp']:
                            dope_sheet[b.name]['timestamp'].append(t)
                        
                        dope_sheet[b.name]['transform'].append(wrap_matrix(matrix))
        
        for b in bone_name_list:
            dict = OrderedDict()
            dict['name'] = b
            dict['time'] = NoIndent([round(t / (bpy.context.scene.render.fps), 4) for t in dope_sheet[b]['timestamp']])
            dict['transform'] = dope_sheet[b]['transform']
            output.append(dict)

    return output

def export_camera(camera_obj):
    scene = bpy.context.scene
    action = camera_obj.animation_data.action
    transform = []
    timestamp = []
    
    if action is not None:
        kf_names = set([fcurve.group.name for fcurve in action.fcurves])
        
        if len(kf_names) != 1:
            print(kf_names)
            raise Exception('Camera transform sheet must have 1 keyframe')
        
        for curve in action.fcurves:
            keyframePoints = curve.keyframe_points
            
            for keyframe in keyframePoints:
                val = int(keyframe.co[0])
                
                if val not in timestamp:
                    timestamp.append(val)
        
        timestamp.sort()
        
        for t in timestamp:
            scene.frame_set(t)
            world_mat = mathutils.Matrix.Translation(mathutils.Vector((0.0, 0.0, -1.62))) * camera_obj.matrix_world
            
            loc, rot, sca = world_mat.decompose()
            blender_to_minecraft_coord = mathutils.Quaternion((1.0, 0.0, 0.0), math.radians(-90.0))
            
            loc.rotate(blender_to_minecraft_coord)
            rot.rotate(blender_to_minecraft_coord)
            
            transformdict = OrderedDict()
            transformdict['loc'] = NoIndent([round(v, 6) for v in loc])
            transformdict['rot'] = NoIndent([round(v, 6) for v in rot])
            transformdict['sca'] = NoIndent([round(v, 6) for v in sca])
            transform.append(transformdict)
        
        output = OrderedDict()
        output['time'] = NoIndent([round(t / (bpy.context.scene.render.fps), 4) for t in timestamp])
        output['transform'] = transform
    
    return output

# Correct the bone priority matching with vertex group's order
def correct_bones_as_vertex_groups(obj, bones):
    corrected_bone_names = []
    
    for vg in obj.vertex_groups:
        if vg.name[-5:] != "_mesh" and vg.name != "Clothing" :
            corrected_bone_names.append(vg.name)
    
    return corrected_bone_names

def save(context, **kwargs):
    file_path = ensure_extension( kwargs['filepath'], ".json")
    output = OrderedDict()
    mesh_obj = armature_obj = camera_obj = mesh_result = armature_result = animation_result = camera_result = None
    
    export_msh = kwargs['export_mesh']
    export_armat = kwargs['export_armature']
    export_anim = kwargs['export_anim']
    export_cam = kwargs['export_camera']
    animation_format = kwargs['animation_format']
    export_visible_bones = kwargs['export_only_visible_bones']
    
    for obj in context.scene.objects:
        if obj.type == 'MESH':
            mesh_obj = obj
        elif obj.type == 'ARMATURE':
            armature_obj = obj
        elif obj.type == 'CAMERA':
            camera_obj = obj
    
    if armature_obj is not None:
        armature_result = export_armature(armature_obj, export_visible_bones)
        
        if export_anim:
            animation_result = export_animation(armature_obj, armature_result['joints'].value, animation_format)
    
    if mesh_obj is not None:
        if armature_obj is not None:
            armature_result['joints'].value = correct_bones_as_vertex_groups(mesh_obj, armature_result['joints'].value)
        
        if export_msh:
            mesh_result = export_mesh(mesh_obj, armature_result['joints'].value if armature_obj is not None else None)
    
    if export_cam:
        if camera_obj is None:
            raise Exception('No camera object to export. Create camera object or uncheck Export Camera in export option.')
        else:
            camera_result = export_camera(camera_obj)
    
    if mesh_result is not None:
        output['vertices'] = mesh_result
    if armature_result is not None and export_armat:
        output['armature'] = armature_result
    if animation_result is not None and export_anim:
        if animation_format == 'ATTR':
            output['format'] = 'attributes'
        output['animation'] = animation_result
        
    if camera_result is not None and export_cam:
        output['camera'] = camera_result
    
    json_to_string = json.dumps(output, cls=NoIndentEncoder, indent=4)
    
    with open(file_path, 'w') as outfile:
        outfile.write(json_to_string)
    
    return {"FINISHED"}