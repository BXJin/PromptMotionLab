
# @Description: Check ControlRigComponent API methods
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
actor = None
for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor):
    if 'CRTest' in a.get_actor_label():
        actor = a
        break

cr_comp = actor.get_component_by_class(unreal.ControlRigComponent)
print({'cr_comp': str(cr_comp)})

if cr_comp:
    methods = [m for m in dir(cr_comp) if 'control' in m.lower() or 'rig' in m.lower()]
    print({'methods': methods})
