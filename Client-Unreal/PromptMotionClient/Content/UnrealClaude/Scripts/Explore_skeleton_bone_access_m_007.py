
# @Description: Get bone names from unreal_file via mesh bone index iteration
import unreal

mesh = unreal.load_asset('/Game/child_test_2/mesh/unreal_file')
skel = mesh.get_editor_property('skeleton')

# PhysicsAsset로 bone 이름 시도
physics = mesh.get_editor_property('physics_asset')
print({'physics_asset': str(physics)})

# LODInfo로 시도
lod_info = mesh.get_editor_property('lod_settings')
print({'lod_settings': str(lod_info)})

# skeleton에서 직접
skel_methods = [m for m in dir(skel) if 'bone' in m.lower() or 'pose' in m.lower() or 'ref' in m.lower()]
print({'skel_bone_methods': skel_methods})

# get_reference_pose 반환 타입 확인
ref = skel.get_reference_pose()
print({'ref_pose_type': type(ref).__name__, 'ref_len': len(ref) if ref else 0})
if ref and len(ref) > 0:
    first = ref[0]
    print({'first_item_type': type(first).__name__, 'first_attrs': [a for a in dir(first) if not a.startswith('_')]})
