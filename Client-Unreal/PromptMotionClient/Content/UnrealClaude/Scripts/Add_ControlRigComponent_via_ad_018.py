
# @Description: Add ControlRigComponent to CRTest BP using create_new_bp_component
import unreal

bp = unreal.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter_CRTest')
cr_body = unreal.load_asset('/Game/Characters/Mannequins/Rigs/CR_Mannequin_Body')

sods = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)

# create_new_bp_component signature 확인
import inspect
try:
    sig = inspect.signature(sods.create_new_bp_component)
    print({'create_new_bp_component_sig': str(sig)})
except:
    pass

# add_new_subobject 시도 - set_editor_property 방식
root_handles = sods.k2_gather_subobject_data_for_blueprint(bp)
print({'root_handle_count': len(root_handles), 'first': str(root_handles[0]) if root_handles else 'none'})

params = unreal.AddNewSubobjectParams()
params.set_editor_property('parent_handle', root_handles[0])
params.set_editor_property('new_class', unreal.ControlRigComponent)
params.set_editor_property('blueprint_context', bp)

new_handle, fail_reason = sods.add_new_subobject(params)
print({'new_handle_valid': new_handle.is_valid(), 'fail_reason': str(fail_reason)})

if new_handle.is_valid():
    sods.rename_subobject(new_handle, 'GestureControlRig')
    print({'renamed': True})
