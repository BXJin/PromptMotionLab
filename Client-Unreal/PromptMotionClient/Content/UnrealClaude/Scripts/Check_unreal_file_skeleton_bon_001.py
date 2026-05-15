
# @Description: Get all bones from unreal_file skeleton and check morph targets
import unreal

# Skeleton bone 목록
skel = unreal.load_asset('/Game/Characters/Mannequin_UE4/Meshes/SK_Mannequin_Skeleton')
mesh = unreal.load_asset('/Game/child_test_2/mesh/unreal_file')

# Skeleton의 모든 bone
ref_skel_methods = [m for m in dir(skel) if not m.startswith('_')]
print({'skel_methods': ref_skel_methods})

# SkeletalMesh에서 bone 이름 목록
mesh_methods = [m for m in dir(mesh) if 'bone' in m.lower() or 'morph' in m.lower() or 'socket' in m.lower()]
print({'mesh_methods': mesh_methods})
