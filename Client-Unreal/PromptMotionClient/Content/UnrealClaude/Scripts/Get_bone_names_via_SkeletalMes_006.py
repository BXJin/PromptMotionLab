
# @Description: Get bone names via SkeletalMeshComponent in editor world
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()

# unreal_file 액터 찾기
actor = None
for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.SkeletalMeshActor):
    if 'unreal_file' in a.get_actor_label():
        actor = a
        break

if actor:
    smc = actor.get_component_by_class(unreal.SkeletalMeshComponent)
    bones = smc.get_all_socket_names()  # socket names
    print({'sockets': [str(s) for s in bones]})
    
    # bone names via animation
    bone_names = unreal.AnimationLibrary.get_bone_pose_for_frame if hasattr(unreal, 'AnimationLibrary') else None
    
    # try get_bone_names
    try:
        bn = smc.get_bone_names()
        print({'bone_count': len(bn), 'bones': sorted([str(b) for b in bn])})
    except Exception as e:
        print({'bone_error': str(e)})
else:
    # BP_ThirdPersonCharacter 에서 시도
    for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Character):
        if 'CRTest' not in a.get_actor_label():
            smc = a.get_component_by_class(unreal.SkeletalMeshComponent)
            if smc:
                try:
                    bn = smc.get_bone_names()
                    print({'bone_count': len(bn), 'bones': sorted([str(b) for b in bn])})
                except Exception as e:
                    print({'bone_error': str(e)})
            break
