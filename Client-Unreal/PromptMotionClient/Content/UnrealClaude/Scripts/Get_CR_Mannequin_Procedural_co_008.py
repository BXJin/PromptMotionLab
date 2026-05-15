
# @Description: Get CR_Mannequin_Procedural control names from hierarchy
import unreal

cr = unreal.load_asset('/Game/Characters/Mannequins/Rigs/CR_Mannequin_Procedural')
if not cr:
    print({'error': 'load failed'})
    raise SystemExit

hierarchy = cr.get_hierarchy()
controls = []
for key in hierarchy.get_all_keys():
    if key.type == unreal.RigElementType.CONTROL:
        ctrl = hierarchy.get_control(key)
        controls.append({
            'name': key.name,
            'type': str(ctrl.control_type) if ctrl else 'unknown'
        })

print({'control_count': len(controls), 'controls': controls})
