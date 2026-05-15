
# @Description: Test set_control_rotator on hand_r_fk_ctrl - hand wave test
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actor = None
for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
    if 'CRTest' in a.get_actor_label():
        actor = a
        break

cr_comp = actor.get_component_by_class(unreal.ControlRigComponent)

# ControlRigComponentSpace 값 확인
spaces = [s for s in dir(unreal.ControlRigComponentSpace) if not s.startswith('_')]
print({'spaces': spaces})

# 현재 hand_r_fk_ctrl 값 읽기
try:
    current = cr_comp.get_control_rotator('hand_r_fk_ctrl', unreal.ControlRigComponentSpace.WORLD_SPACE)
    print({'hand_r_current': str(current)})
except Exception as e:
    print({'get_error': str(e)})

# hand_r_fk_ctrl 에 Yaw 60도 설정 (손 흔들기)
try:
    cr_comp.set_control_rotator('hand_r_fk_ctrl', unreal.Rotator(0.0, 60.0, 0.0), unreal.ControlRigComponentSpace.LOCAL_SPACE)
    print({'set_hand_r_done': True})
except Exception as e:
    print({'set_error': str(e)})

# headNod 테스트 - head_ctrl pitch 30도
try:
    cr_comp.set_control_rotator('head_ctrl', unreal.Rotator(30.0, 0.0, 0.0), unreal.ControlRigComponentSpace.LOCAL_SPACE)
    print({'set_head_done': True})
except Exception as e:
    print({'head_error': str(e)})
