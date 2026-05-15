
# @Description: Test SetControlRotation on hand_r_fk_ctrl via ControlRigComponent
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()

# CRTest 액터 찾기
actor = None
for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
    if 'CRTest' in a.get_actor_label():
        actor = a
        break

if not actor:
    print({'error': 'CRTest actor not found'})
    raise SystemExit

print({'actor': actor.get_actor_label()})

# ControlRigComponent 찾기
cr_comp = actor.get_component_by_class(unreal.ControlRigComponent)
print({'cr_comp': str(cr_comp)})

if not cr_comp:
    print({'error': 'No ControlRigComponent'})
    raise SystemExit

# ControlRig 인스턴스 가져오기
cr = cr_comp.get_control_rig(0)
print({'control_rig': str(cr), 'cr_type': type(cr).__name__ if cr else 'None'})

if cr:
    # hand_r_fk_ctrl 현재 값 확인
    try:
        rot = cr.get_control_rotation('hand_r_fk_ctrl', unreal.ControlRigComponentSpace.WORLD_SPACE)
        print({'hand_r_current_rot': str(rot)})
    except Exception as e:
        print({'get_rot_error': str(e)})

    # hand_r_fk_ctrl 회전 설정 (Yaw 45도 - 손 흔들기 방향)
    try:
        cr.set_control_rotation('hand_r_fk_ctrl', unreal.Rotator(0, 45, 0), unreal.ControlRigComponentSpace.LOCAL_SPACE)
        print({'set_rot_done': True})
    except Exception as e:
        print({'set_rot_error': str(e)})
