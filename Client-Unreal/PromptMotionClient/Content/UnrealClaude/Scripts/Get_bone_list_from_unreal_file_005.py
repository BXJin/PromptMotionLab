
# @Description: Get bones from unreal_file skeleton via reference pose
import unreal

skel = unreal.load_asset('/Game/Characters/Mannequin_UE4/Meshes/SK_Mannequin_Skeleton')
ref_pose = skel.get_reference_pose()
all_bones = sorted([str(b.bone_name) for b in ref_pose])
print({'total': len(all_bones), 'bones': all_bones})
