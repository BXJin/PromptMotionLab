
# @Description: Inspect BP_ThirdPersonCharacter CDO - mesh, skeleton, anim class details
import unreal

r = {}
bp = unreal.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter')
if not bp:
    print({'error': 'load failed'})
    raise SystemExit

gen_class = bp.generated_class()
cdo = unreal.get_default_object(gen_class)

# SkeletalMeshComponent (CharacterMesh0)
smc = cdo.get_component_by_class(unreal.SkeletalMeshComponent)
if smc:
    mesh = smc.get_editor_property('skeletal_mesh_asset')
    anim_class = smc.get_editor_property('anim_class')
    anim_mode = smc.get_editor_property('animation_mode')
    r['mesh'] = mesh.get_path_name() if mesh else 'None'
    r['anim_class'] = str(anim_class) if anim_class else 'None'
    r['anim_mode'] = str(anim_mode)
    if mesh:
        skel = mesh.get_editor_property('skeleton')
        r['skeleton'] = skel.get_path_name() if skel else 'None'

print(r)
