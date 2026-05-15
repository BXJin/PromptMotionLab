
# @Description: Add ControlRigComponent with CR_Mannequin_Body to BP_ThirdPersonCharacter_CRTest
import unreal

bp = unreal.load_asset('/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter_CRTest')
cr_asset = unreal.load_asset('/Game/Characters/Mannequins/Rigs/CR_Mannequin_Body')

# Get blueprint editor subsystem
bes = unreal.get_editor_subsystem(unreal.BlueprintEditorLibrary) if hasattr(unreal, 'BlueprintEditorLibrary') else None

# Add ControlRigComponent to blueprint
comp_name = 'GestureControlRig'
gen_class = bp.generated_class()
cdo = unreal.get_default_object(gen_class)

# Check if already exists
existing = cdo.get_component_by_class(unreal.ControlRigComponent) if hasattr(unreal, 'ControlRigComponent') else None
print({'ControlRigComponent_available': hasattr(unreal, 'ControlRigComponent'), 'existing': str(existing)})

# List control rig related classes
cr_classes = [c for c in dir(unreal) if 'ControlRig' in c or 'controlrig' in c.lower()]
print({'cr_classes': cr_classes[:20]})
