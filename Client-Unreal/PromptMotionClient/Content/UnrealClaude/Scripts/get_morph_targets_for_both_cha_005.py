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
    morphs = sm.get_morph_targets()
    morph_names = sorted([m.get_name() for m in morphs])
    print(f'=== {char_name} === ({len(morph_names)} morphs)')
    for m in morph_names:
        print(f'  {m}')
