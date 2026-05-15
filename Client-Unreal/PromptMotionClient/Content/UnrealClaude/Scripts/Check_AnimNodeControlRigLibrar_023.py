
# @Description: Check ABP_Quinn AnimGraph for existing Control Rig nodes
import unreal

abp = unreal.load_asset('/Game/Characters/Mannequins/Animations/ABP_Quinn')
# AnimNodeControlRigLibrary 에서 사용 가능한 함수 확인
methods = [m for m in dir(unreal.AnimNodeControlRigLibrary) if not m.startswith('_')]
print({'AnimNodeControlRigLibrary_methods': methods})

# AnimLayerControlRigObject 확인
layer_methods = [m for m in dir(unreal.AnimLayerControlRigObject) if not m.startswith('_')]
print({'AnimLayerControlRigObject_methods': layer_methods[:20]})
