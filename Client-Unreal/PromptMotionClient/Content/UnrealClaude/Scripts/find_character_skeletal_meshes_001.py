import unreal
results = {}
char_names = ['child_test_2', 'child_female_test1']
for name in char_names:
    assets = unreal.AssetRegistryHelpers.get_asset_registry().get_assets_by_class(unreal.TopLevelAssetPath('/Script/Engine', 'SkeletalMesh'))
    found = [a for a in assets if name.lower() in str(a.asset_name).lower()]
    results[name] = {'count': len(found), 'paths': [str(a.object_path) for a in found[:5]]}
print(str(results))
