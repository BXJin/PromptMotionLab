
# @Description: Check skeleton paths and ABP_Quinn target skeleton

import unreal
results = {}

skel_ue4 = unreal.load_asset('/Game/Characters/Mannequin_UE4/Meshes/SK_Mannequin_Skeleton')
skel_ue5 = unreal.load_asset('/Game/Characters/Mannequins/Meshes/SK_Mannequin')

results['UE4_skel_path'] = skel_ue4.get_path_name() if skel_ue4 else 'LOAD_FAILED'
results['UE5_skel_path'] = skel_ue5.get_path_name() if skel_ue5 else 'LOAD_FAILED'
results['same_object'] = (skel_ue4 == skel_ue5) if (skel_ue4 and skel_ue5) else 'N/A'

abp_quinn = unreal.load_asset('/Game/Characters/Mannequins/Animations/ABP_Quinn')
if abp_quinn:
    try:
        tgt = abp_quinn.get_editor_property('target_skeleton')
        results['ABP_Quinn_target_skel'] = tgt.get_path_name() if tgt else 'None'
    except Exception as e:
        results['ABP_Quinn_target_skel'] = str(e)

abp_manny = unreal.load_asset('/Game/Characters/Mannequins/Animations/ABP_Manny')
if abp_manny:
    try:
        tgt = abp_manny.get_editor_property('target_skeleton')
        results['ABP_Manny_target_skel'] = tgt.get_path_name() if tgt else 'None'
    except Exception as e:
        results['ABP_Manny_target_skel'] = str(e)

print(str(results))
