
# @Description: Check CR_Mannequin_Procedural element types and modular rig info
import unreal

cr = unreal.load_asset('/Game/Characters/Mannequins/Rigs/CR_Mannequin_Procedural')
h = cr.hierarchy

all_keys = h.get_all_keys()
type_counts = {}
sample_names = {}
for key in all_keys:
    t = str(key.type)
    type_counts[t] = type_counts.get(t, 0) + 1
    if t not in sample_names:
        sample_names[t] = []
    if len(sample_names[t]) < 5:
        sample_names[t].append(key.name)

print({'total': len(all_keys), 'type_counts': type_counts, 'samples': sample_names})

# also check if modular
print({'is_module': cr.is_control_rig_module()})
mrm = cr.modular_rig_model
print({'modular_rig_model': str(mrm) if mrm else 'None'})
