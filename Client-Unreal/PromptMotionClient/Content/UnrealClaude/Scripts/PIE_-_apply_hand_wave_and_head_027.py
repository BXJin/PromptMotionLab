
# @Description: PIE world - find CRTest actor and set control rotators for hand wave + head nod
import unreal

# PIE 월드 가져오기
pie_world = None
for world in unreal.UnrealEditorSubsystem.get_pie_worlds(True):
    pie_world = world
    break

if not pie_world:
    # 단일 PIE world
    subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    pie_world = subsystem.get_game_world()

print({'pie_world': str(pie_world)})

if not pie_world:
    print({'error': 'no PIE world'})
    raise SystemExit

# CRTest 액터 찾기
actor = None
for a in unreal.GameplayStatics.get_all_actors_of_class(pie_world, unreal.Actor):
    if 'CRTest' in a.get_actor_label():
        actor = a
        break

print({'actor': actor.get_actor_label() if actor else 'NOT FOUND'})

if not actor:
    raise SystemExit

# ControlRigComponent 찾기
cr_comp = actor.get_component_by_class(unreal.ControlRigComponent)
print({'cr_comp': str(cr_comp)})

if cr_comp:
    # 손 흔들기 - hand_r_fk_ctrl
    cr_comp.set_control_rotator('hand_r_fk_ctrl', unreal.Rotator(0.0, 0.0, 60.0), unreal.ControlRigComponentSpace.LOCAL_SPACE)
    # 고개 끄덕 - head_ctrl
    cr_comp.set_control_rotator('head_ctrl', unreal.Rotator(30.0, 0.0, 0.0), unreal.ControlRigComponentSpace.LOCAL_SPACE)
    # 어깨 올리기 - clavicle_r_ctrl
    cr_comp.set_control_rotator('clavicle_r_ctrl', unreal.Rotator(0.0, 0.0, 20.0), unreal.ControlRigComponentSpace.LOCAL_SPACE)
    print({'gestures_applied': True})
