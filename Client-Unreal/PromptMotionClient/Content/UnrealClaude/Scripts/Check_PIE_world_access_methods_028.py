
# @Description: Get PIE world - check available methods
import unreal

subsystem = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
methods = [m for m in dir(subsystem) if 'world' in m.lower() or 'pie' in m.lower() or 'game' in m.lower()]
print({'methods': methods})
