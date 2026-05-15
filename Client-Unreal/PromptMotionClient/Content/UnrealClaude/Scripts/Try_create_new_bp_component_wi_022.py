
# @Description: create_new_bp_component with class name string
import unreal

bp = unreal.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter_CRTest')
sods = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)

# pos 1: blueprint, pos 2: ?, pos 3: new_class_name
# try different param combos
errors = []
attempts = [
    lambda: sods.create_new_bp_component(bp, bp, 'ControlRigComponent'),
    lambda: sods.create_new_bp_component(bp, None, 'ControlRigComponent'),
    lambda: sods.create_new_bp_component(bp, unreal.ControlRigComponent, 'GestureControlRig'),
]
for i, fn in enumerate(attempts):
    try:
        r = fn()
        print({'attempt': i, 'result': str(r)})
        break
    except Exception as e:
        errors.append({'attempt': i, 'error': str(e)})

if errors:
    print({'errors': errors})
