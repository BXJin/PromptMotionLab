
# @Description: Check CR mapping and add skeletal mesh mapping
import unreal

subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
game_world = subsystem.get_game_world()

actor = None
for a in unreal.GameplayStatics.get_all_actors_of_class(game_world, unreal.Actor):
    if 'CRTest' in a.get_actor_label():
        actor = a
        break

cr_comp = actor.get_component_by_class(unreal.ControlRigComponent)
smc = actor.get_component_by_class(unreal.SkeletalMeshComponent)

# CR 인스턴스
cr = cr_comp.get_control_rig()
print({'cr_instance': str(cr)})

# mapping 관련 메서드 확인
map_methods = [m for m in dir(cr_comp) if 'map' in m.lower() or 'add' in m.lower() or 'skeletal' in m.lower()]
print({'map_methods': map_methods})

# mapped_components 확인
try:
    mapped = cr_comp.get_editor_property('mapped_components')
    print({'mapped_components_count': len(mapped) if mapped else 0, 'mapped': str(mapped)})
except Exception as e:
    print({'mapped_error': str(e)})
