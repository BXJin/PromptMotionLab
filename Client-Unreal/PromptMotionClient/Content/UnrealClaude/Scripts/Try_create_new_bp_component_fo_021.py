
# @Description: Use create_new_bp_component to add ControlRigComponent to CRTest BP
import unreal

bp = unreal.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter_CRTest')
cr_body = unreal.load_asset('/Game/Characters/Mannequins/Rigs/CR_Mannequin_Body')

sods = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)

# create_new_bp_component 시그니처 파악
import inspect
try:
    print({'sig': str(inspect.signature(sods.create_new_bp_component))})
except:
    print({'sig': 'unavailable'})

# 파라미터 직접 시도
try:
    result = sods.create_new_bp_component(bp, unreal.ControlRigComponent)
    print({'create_result': str(result)})
except Exception as e:
    print({'create_error': str(e)})
