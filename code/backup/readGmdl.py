# 从gdml文件中读取栅元信息
# 输入：文件地址
# 输出：字典allStructure

from lxml import etree
import pickle
from model import Box, Sphere, Tube, Volume


def getVal(root, path):
    return root.xpath(path)[0]


# 遇到的问题
# 1.哪些标签是可选的或者有多种不同格式？(目前已知material的Z标签有两种格式)
# 2.位置和角度的单位只能是mm和radian吗？
# 3.元素的简称formula是否无用？(暂定为无用)
# 4.类似M00000001_Z013027的name标签在生成时是否有规律？
# 5.solids里的栅元块是否只会用到三种类别？/box/sphere/tube
# 6.World栅元在后续处理是否需要？(暂定不需要)
# <box aunit="radian" lunit="mm" name="WorldBox" x="10000" y="10000" z="10000" />
# <sphere aunit="radian" deltaphi="6.29" deltatheta="3.15" lunit="mm" name="Sol_S_S1" rmax="87.407" rmin="0" startphi="0" starttheta="0" />
# <tube aunit="radian" deltaphi="6.29" lunit="mm" name="Sol_S_C2_1" rmax="508" rmin="0" startphi="0" z="2.77" />
try:
    root = etree.parse('Model.gdml')
except:
    pass
# 获取常数定义
conTree = root.xpath('./define/constant')
conNames = [con.xpath('@name')[0] for con in conTree]
conVal = [con.xpath('@value')[0] for con in conTree]

# 获取位置定义
posTree = root.xpath('./define/position')
posName = [pos.xpath('@name')[0] for pos in posTree]
posVal = [(pos.xpath('@unit')[0], float(pos.xpath('@x')[0]), float(pos.xpath('@y')[0]), float(pos.xpath('@z')[0])) for pos in posTree]

# 获取角度定义
rotTree = root.xpath('./define/rotation')
rotName = [rot.xpath('@name')[0] for rot in rotTree]
rotVal = [(rot.xpath('@unit')[0], float(rot.xpath('@x')[0]), float(rot.xpath('@y')[0]), float(rot.xpath('@z')[0])) for rot in rotTree]

constants = dict(zip(conNames, conVal))
position = dict(zip(posName, posVal))
rotation = dict(zip(rotName, rotVal))

# 获取元素定义
eleTree = root.xpath('./materials/element')
eleName = [ele.xpath('@name')[0] for ele in eleTree]
# 序号0-3为int原子序数，double原子质量，string 原子简称
# eleInf = [(ele.xpath('@Z')[0],ele.xpath('atom/@value')[0],ele.xpath('@formula')[0]) for ele in eleTree ]
# 暂定不需要formula
eleInf = [(ele.xpath('@Z')[0], ele.xpath('atom/@value')[0]) for ele in eleTree]
elements = dict(zip(eleName, eleInf))

# 获取材料定义
# 对于无引用的材料，定义同名新元素，假装引用
matTree = root.xpath('./materials/material')
matName = [mat.xpath('@name')[0] for mat in matTree]
matD = [mat.xpath('D/@value')[0] for mat in matTree]
matEles = [
    [(fac.xpath('@ref')[0], float(fac.xpath('@n')[0])) for fac in mat.xpath('fraction')] if len(mat.xpath('@Z')) == 0 else [(
        mat.xpath('@name')[0], 1.0)] for mat in matTree]

materials = dict(zip(matName, zip(matD, matEles)))

# 更新新定义的元素
newTree = [mat for mat in matTree if len(mat.xpath('@Z')) != 0]
newName = [new.xpath('@name')[0] for new in newTree]
newInf = [(int(new.xpath('@Z')[0]), int(new.xpath('atom/@value')[0])) for new in newTree]
newEles = dict(zip(newName, newInf))
elements.update(newEles)

# 获取栅元定义
solids = {}
solid = root.xpath('./solids')[0]
for box in solid.xpath('box'):
    # 设置通用属性
    name = box.xpath('@name')[0]
    newBox = Box(name)
    newBox.aUnit = box.xpath('@aunit')[0]
    newBox.lUnit = box.xpath('@lunit')[0]
    # 设置box属性
    newBox.x = float(box.xpath('@x')[0])
    newBox.y = float(box.xpath('@y')[0])
    newBox.z = float(box.xpath('@z')[0])
    solids[name] = newBox

for sphere in solid.xpath('sphere'):
    # 设置通用属性
    name = sphere.xpath('@name')[0]
    newSphere = Sphere(name)
    newSphere.aUnit = sphere.xpath('@aunit')[0]
    newSphere.lUnit = sphere.xpath('@lunit')[0]
    # 设置sphere属性
    newSphere.deltaPhi = float(sphere.xpath('@deltaphi')[0])
    newSphere.deltaTheta = float(sphere.xpath('@deltatheta')[0])
    newSphere.rMax = float(sphere.xpath('@rmax')[0])
    newSphere.rMin = float(sphere.xpath('@rmin')[0])
    newSphere.startPhi = float(sphere.xpath('@startphi')[0])
    newSphere.startTheta = float(sphere.xpath('@starttheta')[0])
    solids[name] = newSphere

for tube in solid.xpath('tube'):
    # 设置通用属性
    name = tube.xpath('@name')[0]
    newTube = Tube(name)
    newTube.aUnit = tube.xpath('@aunit')[0]
    newTube.lUnit = tube.xpath('@lunit')[0]
    # 设置tube属性
    newTube.rMax = float(tube.xpath('@rmax')[0])
    newTube.rMin = float(tube.xpath('@rmin')[0])
    newTube.startPhi = float(tube.xpath('@startphi')[0])
    newTube.z = float(tube.xpath('@z')[0])
    solids[name] = newTube

# 补充栅元的物质信息和空间信息
allStructure = {}
structures = root.xpath('./structure/volume')
for structure in structures:
    name = structure.xpath('@name')[0]
    # 物质信息
    if name != 'World':
        solidRef = structure.xpath('solidref/@ref')[0]
        materialRef = structure.xpath('materialref/@ref')[0]
        if solids.__contains__(solidRef):
            volume = solids[solidRef]
        else:
            volume = Volume(solidRef)
        items = materials[materialRef]
        volume.matName = materialRef
        volume.matD = items[0]
        volume.matGre = [item + elements[item[0]] for item in items[1]]
        allStructure[name[6:]] = volume
    # 空间信息
    else:
        physvols = structure.xpath('physvol')
        for physvol in physvols:
            name = physvol.xpath('volumeref/@ref')[0]
            allStructure[name[6:]].pos = position[physvol.xpath('positionref/@ref')[0]]
            allStructure[name[6:]].rot = rotation[physvol.xpath('rotationref/@ref')[0]]

# print(constants)
# print(position)
# print(rotation)
# print(elements)
# print(materials)
for key in allStructure.keys():
    print(
        key+'\t'+allStructure[key].__class__.__name__ + '\t' + allStructure[key].name + '\t' + allStructure[key].matName + '\t' +
        allStructure[key].matD)
    print(allStructure[key].pos)
    print(allStructure[key].rot)
    print(allStructure[key].matGre)
    print('\n')

with open('structure', 'wb') as out:
    pickle.dump(allStructure, out)