
# @Description: Set ControlRigComponent CR class and compile CRTest BP
import unreal

bp = unreal.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter_CRTest')
cr_body = unreal.load_asset('/Game/Characters/Mannequins/Rigs/CR_Mannequin_Body')

gen_class = bp.generated_class()
cdo = unreal.get_default_object(gen_class)

# ControlRigComponent 존재 확인
cr_comp = cdo.get_component_by_class(unreal.ControlRigComponent)
print({'cr_comp_found': cr_comp is not None, 'cr_comp': str(cr_comp)})

if cr_comp:
    # CR class 설정
    cr_class = cr_body.generated_class()
    cr_comp.set_editor_property('control_rig_class', cr_class)
    print({'cr_class_set': str(cr_class)})

    # BP 컴파일 + 저장
    unreal.KismetSystemLibrary.compile_blueprint(bp)
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    print({'saved': True})
else:
    # 아직 없으면 - 이전 add가 실제로 안됐을 수 있음
    # SubobjectDataSubsystem으로 다시 추가
    sods = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    root_handles = sods.k2_gather_subobject_data_for_blueprint(bp)
    
    params = unreal.AddNewSubobjectParams()
    params.set_editor_property('parent_handle', root_handles[0])
    params.set_editor_property('new_class', unreal.ControlRigComponent)
    params.set_editor_property('blueprint_context', bp)
    
    new_handle, fail_reason = sods.add_new_subobject(params)
    print({'added': True, 'fail_reason': str(fail_reason)})
    
    if not fail_reason:
        sods.rename_subobject(new_handle, 'GestureControlRig')
        # 컴파일 후 CDO 재접근
        unreal.KismetSystemLibrary.compile_blueprint(bp)
        cdo2 = unreal.get_default_object(bp.generated_class())
        cr_comp2 = cdo2.get_component_by_class(unreal.ControlRigComponent)
        if cr_comp2:
            cr_class = cr_body.generated_class()
            cr_comp2.set_editor_property('control_rig_class', cr_class)
            print({'cr_class_set': str(cr_class)})
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        print({'saved': True})
