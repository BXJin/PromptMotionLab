
# @Description: Get bone names via KismetAnimationLibrary
import unreal

mesh = unreal.load_asset('/Game/child_test_2/mesh/unreal_file')

# get_reference_pose 타입 탐색
try:
    ref = mesh.get_editor_property('skeleton').get_reference_pose()
    item = ref[0]
    print({'type': type(item).__name__, 'dir': [a for a in dir(item) if not a.startswith('_')]})
except Exception as e:
    print({'error': str(e)})

# curve meta data names (= morph target driven curves)
skel = mesh.get_editor_property('skeleton')
try:
    names = skel.get_curve_meta_data_names()
    print({'curve_names_count': len(names), 'sample': [str(n) for n in names[:10]]})
except Exception as e:
    print({'curve_error': str(e)})
