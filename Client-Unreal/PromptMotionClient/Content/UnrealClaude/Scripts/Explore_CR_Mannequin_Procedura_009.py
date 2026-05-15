
# @Description: Get CR_Mannequin_Procedural controls via rig controller
import unreal

cr = unreal.load_asset('/Game/Characters/Mannequins/Rigs/CR_Mannequin_Procedural')
print({'class': type(cr).__name__, 'path': cr.get_path_name()})

# list available methods
methods = [m for m in dir(cr) if 'control' in m.lower() or 'hierarch' in m.lower() or 'rig' in m.lower()]
print({'methods': methods[:30]})
