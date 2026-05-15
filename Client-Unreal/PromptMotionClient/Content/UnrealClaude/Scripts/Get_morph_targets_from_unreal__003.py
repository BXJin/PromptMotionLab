
# @Description: Get bones and morphs separately - simpler script
import unreal

mesh = unreal.load_asset('/Game/child_test_2/mesh/unreal_file')

# Morph Target 목록
morphs = mesh.get_all_morph_target_names()
print({'morph_count': len(morphs), 'morphs': sorted([str(m) for m in morphs])})
