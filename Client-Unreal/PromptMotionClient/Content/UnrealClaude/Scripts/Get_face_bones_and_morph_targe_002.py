
# @Description: Get all bones and morph targets from unreal_file
import unreal

skel = unreal.load_asset('/Game/Characters/Mannequin_UE4/Meshes/SK_Mannequin_Skeleton')
mesh = unreal.load_asset('/Game/child_test_2/mesh/unreal_file')

# 모든 bone 이름
ref_pose = skel.get_reference_pose()
bone_names = [str(b.bone_name) for b in ref_pose]
print({'total_bones': len(bone_names)})

# 얼굴 관련 bone 필터
face_keywords = ['head','neck','jaw','eye','tongue','teeth','brow','cheek','nose','lip','ear','chin','skull','face']
face_bones = [b for b in bone_names if any(k in b.lower() for k in face_keywords)]
print({'face_bones': sorted(face_bones)})

# 전체 bone 목록 (확인용)
print({'all_bones': sorted(bone_names)})

# Morph Target 목록
morphs = mesh.get_all_morph_target_names()
print({'morph_count': len(morphs), 'morphs': sorted([str(m) for m in morphs])})
