
# @Description: Get bone names from AnimPose and check facial bone structure
import unreal

mesh = unreal.load_asset('/Game/child_test_2/mesh/unreal_file')
skel = mesh.get_editor_property('skeleton')
ref_pose = skel.get_reference_pose()

# AnimPose API 확인
pose_methods = [m for m in dir(ref_pose) if not m.startswith('_')]
print({'pose_methods': pose_methods})

# bone names 시도
try:
    bone_names = unreal.AnimPoseExtensions.get_bone_names(ref_pose)
    face_kw = ['head','neck','jaw','eye','tongue','teeth','lip','ear','chin','face','brow','nose']
    face_bones = sorted([str(b) for b in bone_names if any(k in str(b).lower() for k in face_kw)])
    all_bones = sorted([str(b) for b in bone_names])
    print({'total': len(all_bones), 'face_bones': face_bones})
    print({'all_bones': all_bones})
except Exception as e:
    print({'error': str(e)})
