import unreal

# Use AssetRegistry with filter
ar = unreal.AssetRegistryHelpers.get_asset_registry()
filter = unreal.ARFilter(class_names=['SkeletalMesh'], recursive_paths=True, package_paths=['/Game/'])
assets = ar.get_assets(filter)
print(f'Total SkeletalMesh assets: {len(assets)}')
for a in assets:
    print(str(a.package_name))
