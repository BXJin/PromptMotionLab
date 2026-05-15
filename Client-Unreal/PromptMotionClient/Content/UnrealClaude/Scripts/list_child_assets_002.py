import unreal

# Try asset search by name
lib = unreal.EditorAssetLibrary
all_assets = lib.list_assets('/Game/', recursive=True, include_folder=False)
child_assets = [a for a in all_assets if 'child' in a.lower()]
print('Child assets:', len(child_assets))
for a in child_assets[:30]:
    print(a)
