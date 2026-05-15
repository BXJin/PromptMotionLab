
# @Description: Get all CR_Mannequin_Body controls, filtered for upper body gesture relevant ones
import unreal

cr_body = unreal.load_asset('/Game/Characters/Mannequins/Rigs/CR_Mannequin_Body')
h = cr_body.hierarchy
all_controls = [key.name for key in h.get_all_keys() if key.type == unreal.RigElementType.CONTROL]
print({'all_controls': all_controls})
