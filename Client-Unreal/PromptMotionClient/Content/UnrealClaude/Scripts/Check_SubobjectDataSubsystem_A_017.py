
# @Description: Check ControlRigBlueprintLibrary API and SubobjectDataSubsystem add_new_subobject signature
import unreal

# SubobjectDataSubsystem API 확인
sods = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
sods_methods = [m for m in dir(sods) if not m.startswith('_')]
print({'sods_methods': sods_methods})

# AddNewSubobjectParams fields
params_fields = [f for f in dir(unreal.AddNewSubobjectParams) if not f.startswith('_')]
print({'params_fields': params_fields})
