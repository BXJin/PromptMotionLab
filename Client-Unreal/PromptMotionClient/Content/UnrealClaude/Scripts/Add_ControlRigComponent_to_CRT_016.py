
# @Description: Add ControlRigComponent to BP_ThirdPersonCharacter_CRTest blueprint via SubobjectDataSubsystem
import unreal

bp = unreal.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter_CRTest')
cr_body = unreal.load_asset('/Game/Characters/Mannequins/Rigs/CR_Mannequin_Body')

# SubobjectDataSubsystem로 Blueprint에 컴포넌트 추가
sods = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
root_data_handles = sods.k2_gather_subobject_data_for_blueprint(bp)

if not root_data_handles:
    print({'error': 'no root handle'})
    raise SystemExit

# ControlRigComponent 추가
params = unreal.AddNewSubobjectParams()
params.parent_handle = root_data_handles[0]
params.new_class = unreal.ControlRigComponent
params.blueprint_context = bp

new_handle, fail_reason = sods.add_new_subobject(params)
print({'new_handle': str(new_handle), 'fail_reason': str(fail_reason)})

# 컴포넌트 이름 변경 및 CR asset 설정
if new_handle.is_valid():
    sods.rename_subobject(new_handle, 'GestureControlRig')
    
    # CDO에서 컴포넌트 찾아서 CR class 설정
    gen_class = bp.generated_class()
    cdo = unreal.get_default_object(gen_class)
    cr_comp = cdo.get_component_by_class(unreal.ControlRigComponent)
    
    if cr_comp:
        cr_class = cr_body.generated_class() if hasattr(cr_body, 'generated_class') else None
        if cr_class:
            cr_comp.set_editor_property('control_rig_class', cr_class)
            print({'cr_class_set': str(cr_class)})
        else:
            print({'error': 'no generated_class on CR asset'})
    else:
        print({'error': 'component not found in CDO'})

    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    print({'done': True})
