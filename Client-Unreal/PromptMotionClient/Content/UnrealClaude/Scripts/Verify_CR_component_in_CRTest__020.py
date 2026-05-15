
# @Description: Verify ControlRigComponent in CRTest BP, set CR class, compile and save
import unreal

bp = unreal.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter_CRTest')
cr_body = unreal.load_asset('/Game/Characters/Mannequins/Rigs/CR_Mannequin_Body')

# BP 컴파일
unreal.BlueprintEditorLibrary.compile_blueprint(bp)

gen_class = bp.generated_class()
cdo = unreal.get_default_object(gen_class)

# 모든 컴포넌트 확인
all_comps = cdo.get_components_by_class(unreal.ActorComponent)
comp_names = [(c.get_name(), type(c).__name__) for c in all_comps]
print({'all_components': comp_names})

cr_comp = cdo.get_component_by_class(unreal.ControlRigComponent)
print({'cr_comp': str(cr_comp)})

if cr_comp:
    cr_class = cr_body.generated_class()
    cr_comp.set_editor_property('control_rig_class', cr_class)
    print({'cr_class_set': str(cr_class)})
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    print({'saved': True})
