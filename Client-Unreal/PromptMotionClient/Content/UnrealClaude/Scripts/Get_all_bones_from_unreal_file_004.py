
# @Description: Get all bones from SK_Mannequin_Skeleton (unreal_file) and filter face bones
import unreal

skel = unreal.load_asset('/Game/Characters/Mannequin_UE4/Meshes/SK_Mannequin_Skeleton')
ref_pose = skel.get_reference_pose()
all_bones = sorted([str(b.bone_name) for b in ref_pose])

face_keywords = ['head','neck','jaw','eye','tongue','teeth','brow','cheek',
                 'nose','lip','ear','chin','skull','face','spine','pelvis']
face_bones = [b for b in all_bones if any(k in b.lower() for k in face_keywords)]

print({'total_bone_count': len(all_bones)})
print({'face_related_bones': face_bones})
print({'all_bones': all_bones})
