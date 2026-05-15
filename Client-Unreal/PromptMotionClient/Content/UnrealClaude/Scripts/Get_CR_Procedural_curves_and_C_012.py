
# @Description: Get all curves from CR_Mannequin_Procedural and controls from CR_Mannequin_Body
import unreal

# CR_Mannequin_Procedural - all curves
cr_proc = unreal.load_asset('/Game/Characters/Mannequins/Rigs/CR_Mannequin_Procedural')
h = cr_proc.hierarchy
curves = [key.name for key in h.get_all_keys() if key.type == unreal.RigElementType.CURVE]
print({'CR_Procedural_curves': curves})

# CR_Mannequin_Body - check for controls
cr_body = unreal.load_asset('/Game/Characters/Mannequins/Rigs/CR_Mannequin_Body')
h2 = cr_body.hierarchy
all_keys2 = h2.get_all_keys()
type_counts2 = {}
for key in all_keys2:
    t = str(key.type)
    type_counts2[t] = type_counts2.get(t, 0) + 1
controls2 = [key.name for key in all_keys2 if key.type == unreal.RigElementType.CONTROL]
print({'CR_Body_types': type_counts2, 'CR_Body_controls': controls2[:30]})
