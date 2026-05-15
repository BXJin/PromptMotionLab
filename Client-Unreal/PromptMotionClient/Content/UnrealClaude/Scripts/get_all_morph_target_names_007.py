import unreal

paths = {
    'child_test_2': '/Game/child_test_2/mesh/unreal_file',
    'child_female_test1': '/Game/chlid_femele_test1/mesh/unreal_file'
}

for char_name, path in paths.items():
    sm = unreal.load_asset(path)
    if sm is None:
        print(f'{char_name}: LOAD FAILED')
        continue
    morphs = sorted(sm.get_all_morph_target_names())
    print(f'=== {char_name} === total: {len(morphs)}')
    for m in morphs:
        print(f'  {m}')
    print()
