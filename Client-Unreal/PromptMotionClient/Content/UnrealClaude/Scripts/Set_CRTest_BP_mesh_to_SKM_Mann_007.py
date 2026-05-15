
# @Description: Set BP_ThirdPersonCharacter_CRTest mesh to SKM_Manny

import unreal

bp = unreal.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter_CRTest')
manny = unreal.load_asset('/Game/Characters/Mannequins/Meshes/SKM_Manny')

gen_class = bp.generated_class()
cdo = unreal.get_default_object(gen_class)
smc = cdo.get_component_by_class(unreal.SkeletalMeshComponent)

smc.set_editor_property('skeletal_mesh_asset', manny)

unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)

# verify
mesh = smc.get_editor_property('skeletal_mesh_asset')
anim = smc.get_editor_property('anim_class')
print({'mesh': mesh.get_path_name() if mesh else 'None', 'anim_class': str(anim)})
