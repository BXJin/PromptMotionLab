
# @Description: Debug ControlRigComponent - check mapping and rig instance
import unreal

subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
game_world = subsystem.get_game_world()

actor = None
for a in unreal.GameplayStatics.get_all_actors_of_class(game_world, unreal.Actor):
    if 'CRTest' in a.get_actor_label():
        actor = a
        break

cr_comp = actor.get_component_by_class(unreal.ControlRigComponent)

# CR 인스턴스 확인
cr = cr_comp.get_control_rig(0)
print({'cr_instance': str(cr)})

# CR class 설정 확인
cr_class = cr_comp.get_editor_property('control_rig_class')
print({'cr_class': str(cr_class)})

# mapped_components 확인
try:
    mapped = cr_comp.get_editor_property('mapped_components')
    print({'mapped_components': str(mapped)})
except Exception as e:
    print({'mapped_components_error': str(e)})

# ControlRigComponent의 모든 property 목록
props = [p for p in dir(cr_comp) if not p.startswith('_') and 'map' in p.lower()]
print({'map_props': props})

# SkeletalMeshComponent 확인
smc = actor.get_component_by_class(unreal.SkeletalMeshComponent)
print({'smc': str(smc)})

# AnimInstance 확인
if smc:
    anim = smc.get_anim_instance()
    print({'anim_instance': type(anim).__name__ if anim else 'None'})
