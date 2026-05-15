
# @Description: PIE - find CRTest via get_game_world and apply gestures
import unreal

subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
game_world = subsystem.get_game_world()
print({'game_world': str(game_world)})

if not game_world:
    print({'error': 'no game world - PIE running?'})
    raise SystemExit

# CRTest 액터 찾기
actor = None
for a in unreal.GameplayStatics.get_all_actors_of_class(game_world, unreal.Actor):
    if 'CRTest' in a.get_actor_label():
        actor = a
        break

print({'actor': actor.get_actor_label() if actor else 'NOT FOUND'})
if not actor:
    raise SystemExit

cr_comp = actor.get_component_by_class(unreal.ControlRigComponent)
print({'cr_comp_found': cr_comp is not None})

if cr_comp:
    cr_comp.set_control_rotator('hand_r_fk_ctrl', unreal.Rotator(0.0, 0.0, 60.0), unreal.ControlRigComponentSpace.LOCAL_SPACE)
    cr_comp.set_control_rotator('head_ctrl', unreal.Rotator(30.0, 0.0, 0.0), unreal.ControlRigComponentSpace.LOCAL_SPACE)
    cr_comp.set_control_rotator('clavicle_r_ctrl', unreal.Rotator(0.0, 0.0, 20.0), unreal.ControlRigComponentSpace.LOCAL_SPACE)
    print({'gestures_applied': True})
