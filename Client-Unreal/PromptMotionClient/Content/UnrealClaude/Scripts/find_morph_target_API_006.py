import unreal

# Find the correct API for morph targets
paths = {
    'child_test_2': '/Game/child_test_2/mesh/unreal_file',
    'child_female_test1': '/Game/chlid_femele_test1/mesh/unreal_file'
}

for char_name, path in paths.items():
    sm = unreal.load_asset(path)
    if sm is None:
        print(f'{char_name}: LOAD FAILED')
        continue
    # Try different APIs
    methods = [m for m in dir(sm) if 'morph' in m.lower() or 'target' in m.lower() or 'blend' in m.lower()]
    print(f'{char_name} morph-related methods: {methods}')
    # Try EditorAssetLibrary approach
    try:
        import unreal
        morph_data = unreal.SkeletalMeshEditorSubsystem
        print(f'  SkeletalMeshEditorSubsystem available')
    except:
        pass
