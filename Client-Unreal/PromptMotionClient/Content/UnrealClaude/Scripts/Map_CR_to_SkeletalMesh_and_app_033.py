
# @Description: Map CR to SkeletalMeshComponent and test gesture
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

print({'smc': smc.get_name() if smc else 'None'})

# SkeletalMeshComponent 매핑
try:
    cr_comp.add_mapped_complete_skeletal_mesh(smc)
    print({'mapped_complete': True})
except Exception as e:
    print({'map_complete_error': str(e)})
    try:
        cr_comp.add_mapped_skeletal_mesh(smc)
        print({'mapped': True})
    except Exception as e2:
        print({'map_error': str(e2)})

# 이제 gesture 적용
cr_comp.set_control_rotator('hand_r_fk_ctrl', unreal.Rotator(0.0, 0.0, 60.0), unreal.ControlRigComponentSpace.LOCAL_SPACE)
cr_comp.set_control_rotator('head_ctrl', unreal.Rotator(30.0, 0.0, 0.0), unreal.ControlRigComponentSpace.LOCAL_SPACE)
print({'gestures_applied': True})
