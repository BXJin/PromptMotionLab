
# @Description: Compare SK_Mannequin_Skeleton(UE4) vs SK_Mannequin(UE5), get CR_Mannequin_Procedural controls, check BP_ThirdPersonCharacter mesh settings

import unreal

results = {}

# 1. SK_Mannequin_Skeleton (unreal_file 쪽 - UE4 경로)
skel_ue4 = unreal.load_asset('/Game/Characters/Mannequin_UE4/Meshes/SK_Mannequin_Skeleton')
if skel_ue4:
    results['UE4_skel_path'] = skel_ue4.get_path_name()
    results['UE4_skel_class'] = type(skel_ue4).__name__
    # bone count via ref skeleton
    try:
        ref_skel = skel_ue4.get_editor_property('reference_skeleton')
        results['UE4_bone_count'] = 'ref_skeleton_access: ok'
    except Exception as e:
        results['UE4_skel_note'] = str(e)
else:
    results['UE4_skel_path'] = 'LOAD_FAILED'

# 2. SK_Mannequin (UE5 Manny/Quinn)
skel_ue5 = unreal.load_asset('/Game/Characters/Mannequins/Meshes/SK_Mannequin')
if skel_ue5:
    results['UE5_skel_path'] = skel_ue5.get_path_name()
    results['UE5_skel_class'] = type(skel_ue5).__name__
else:
    results['UE5_skel_path'] = 'LOAD_FAILED'

# 3. Check if they are the same object (compatible = same asset)
if skel_ue4 and skel_ue5:
    results['same_skeleton_object'] = (skel_ue4 == skel_ue5)

# 4. ABP_Quinn target skeleton
abp_quinn = unreal.load_asset('/Game/Characters/Mannequins/Animations/ABP_Quinn')
if abp_quinn:
    try:
        tgt_skel = abp_quinn.get_editor_property('target_skeleton')
        results['ABP_Quinn_target_skeleton'] = str(tgt_skel.get_path_name()) if tgt_skel else 'None'
    except Exception as e:
        results['ABP_Quinn_target_skeleton'] = str(e)

# 5. Check BP_ThirdPersonCharacter default mesh (Blueprint CDO)
bp = unreal.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
if bp:
    try:
        gen_class = bp.generated_class()
        cdo = unreal.get_default_object(gen_class)
        smc = cdo.get_component_by_class(unreal.SkeletalMeshComponent)
        if smc:
            mesh = smc.get_editor_property('skeletal_mesh_asset')
            anim_class = smc.get_editor_property('anim_class')
            results['BP_CDO_mesh'] = str(mesh.get_path_name()) if mesh else 'None'
            results['BP_CDO_anim_class'] = str(anim_class) if anim_class else 'None'
    except Exception as e:
        results['BP_CDO_error'] = str(e)

# 6. CR_Mannequin_Procedural - get rig hierarchy / control list
cr = unreal.load_asset('/Game/Characters/Mannequins/Rigs/CR_Mannequin_Procedural')
if cr:
    results['CR_Procedural_class'] = type(cr).__name__
    results['CR_Procedural_path'] = cr.get_path_name()
    # Try to get hierarchy
    try:
        hierarchy = cr.get_editor_property('hierarchy')
        results['CR_hierarchy_type'] = type(hierarchy).__name__
    except Exception as e:
        results['CR_hierarchy_error'] = str(e)
    # List all properties
    try:
        props = []
        for p in cr.get_class().iter_properties():
            props.append(p.name)
        results['CR_properties'] = props[:20]
    except Exception as e:
        results['CR_props_error'] = str(e)
else:
    results['CR_Procedural'] = 'LOAD_FAILED'

print(str(results))
