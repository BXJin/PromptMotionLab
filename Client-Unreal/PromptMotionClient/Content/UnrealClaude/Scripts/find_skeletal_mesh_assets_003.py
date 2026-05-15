import unreal

lib = unreal.EditorAssetLibrary
all_assets = lib.list_assets('/Game/', recursive=True, include_folder=False)

# Filter only SkeletalMesh assets
sk_assets = [a for a in all_assets if '.SK_' in a or 'SkeletalMesh' in a or ('child' in a.lower() and ':' not in a)]
print('Candidate assets:')
for a in sk_assets[:50]:
    print(a)
