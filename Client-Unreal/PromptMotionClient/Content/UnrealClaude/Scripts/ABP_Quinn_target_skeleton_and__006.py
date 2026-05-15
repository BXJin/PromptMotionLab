
# @Description: ABP_Quinn target skeleton + UE4 vs UE5 skeleton comparison
import unreal
r = {}

abp = unreal.load_asset('/Game/Characters/Mannequins/Animations/ABP_Quinn')
if abp:
    t = abp.get_editor_property('target_skeleton')
    r['ABP_Quinn_target_skel'] = t.get_path_name() if t else 'None'

s_ue4 = unreal.load_asset('/Game/Characters/Mannequin_UE4/Meshes/SK_Mannequin_Skeleton')
s_ue5 = unreal.load_asset('/Game/Characters/Mannequins/Meshes/SK_Mannequin')
r['UE4_skel'] = s_ue4.get_path_name() if s_ue4 else 'FAIL'
r['UE5_skel'] = s_ue5.get_path_name() if s_ue5 else 'FAIL'
r['same_object'] = (s_ue4 == s_ue5) if (s_ue4 and s_ue5) else 'N/A'

print(r)
