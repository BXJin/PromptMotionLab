
# @Description: List all controls in CR_Mannequin_Procedural via hierarchy property
import unreal

cr = unreal.load_asset('/Game/Characters/Mannequins/Rigs/CR_Mannequin_Procedural')
h = cr.hierarchy

controls = []
for key in h.get_all_keys():
    if key.type == unreal.RigElementType.CONTROL:
        controls.append(key.name)

print({'count': len(controls), 'controls': controls})
