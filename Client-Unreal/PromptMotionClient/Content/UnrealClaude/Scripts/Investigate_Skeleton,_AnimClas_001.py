
# @Description: Get Skeleton asset paths for unreal_file and SKM_Manny, AnimClass for level actors, and ControlRig assets

import unreal

results = {}

# 1. Skeleton for unreal_file
mesh1 = unreal.load_asset('/Game/child_test_2/mesh/unreal_file')
if mesh1:
    skel1 = mesh1.get_editor_property('skeleton')
    results['unreal_file_skeleton'] = str(skel1.get_path_name()) if skel1 else 'None'
    dag_rig1 = mesh1.get_editor_property('default_animating_rig')
    results['unreal_file_default_animating_rig'] = str(dag_rig1) if dag_rig1 else 'None'
else:
    results['unreal_file_skeleton'] = 'LOAD_FAILED'

# 2. Skeleton for SKM_Manny
mesh2 = unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny')
if mesh2:
    skel2 = mesh2.get_editor_property('skeleton')
    results['SKM_Manny_skeleton'] = str(skel2.get_path_name()) if skel2 else 'None'
else:
    results['SKM_Manny_skeleton'] = 'LOAD_FAILED'

# 3. AnimClass for BP_ThirdPersonCharacter (from Blueprint defaults)
bp_asset = unreal.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
if bp_asset:
    results['BP_ThirdPersonCharacter_path'] = str(bp_asset.get_path_name())
    try:
        # Try to get default object
        bp_class = unreal.get_default_object(bp_asset.generated_class()) if hasattr(bp_asset, 'generated_class') else None
        results['bp_default_object'] = str(bp_class) if bp_class else 'N/A'
    except:
        results['bp_default_object'] = 'exception'

# 4. AnimClass for unreal_file SkeletalMeshActor
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SkeletalMeshActor):
    if actor.get_actor_label() == 'unreal_file':
        smc = actor.get_component_by_class(unreal.SkeletalMeshComponent)
        if smc:
            mesh = smc.get_editor_property('skeletal_mesh_asset')
            anim_class = smc.get_editor_property('anim_class')
            results['unreal_file_actor_mesh'] = str(mesh.get_path_name()) if mesh else 'None'
            results['unreal_file_actor_anim_class'] = str(anim_class) if anim_class else 'None'

# 5. AnimClass for BP_ThirdPersonCharacter actor
for actor in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Character):
    label = actor.get_actor_label()
    if 'ThirdPerson' in label or 'BP_Third' in label:
        smc = actor.get_component_by_class(unreal.SkeletalMeshComponent)
        if smc:
            mesh = smc.get_editor_property('skeletal_mesh_asset')
            anim_class = smc.get_editor_property('anim_class')
            results['BP_char_actor_mesh'] = str(mesh.get_path_name()) if mesh else 'None'
            results['BP_char_actor_anim_class'] = str(anim_class) if anim_class else 'None'

# 6. Find ControlRig assets (various class names)
ar = unreal.AssetRegistryHelpers.get_asset_registry()
cr_classes = ['ControlRigBlueprint', 'RigHierarchy', 'IKRigDefinition', 'IKRetargeter']
for cls in cr_classes:
    filter_obj = unreal.ARFilter(class_names=[cls], recursive_paths=True, package_paths=['/Game/'])
    assets = ar.get_assets(filter_obj)
    results[f'assets_{cls}'] = [str(a.package_name) for a in assets]

print(str(results))
