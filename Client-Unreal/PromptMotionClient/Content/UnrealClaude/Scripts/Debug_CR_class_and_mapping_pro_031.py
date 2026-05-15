
# @Description: Simple CR debug - cr_class and get_control_rig
import unreal

subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
game_world = subsystem.get_game_world()

actor = None
for a in unreal.GameplayStatics.get_all_actors_of_class(game_world, unreal.Actor):
    if 'CRTest' in a.get_actor_label():
        actor = a
        break

cr_comp = actor.get_component_by_class(unreal.ControlRigComponent)

# cr_class 및 rig 인스턴스
cr_class = cr_comp.get_editor_property('control_rig_class')
cr = cr_comp.get_control_rig(0)
print({'cr_class': str(cr_class), 'cr_instance': str(cr)})

# ControlRigComponent에서 bone 매핑 관련 속성
props = [p for p in dir(cr_comp) if not p.startswith('_')]
print({'all_props': [p for p in props if any(k in p.lower() for k in ['map','bone','mesh','connect','skeletal','component'])]})
