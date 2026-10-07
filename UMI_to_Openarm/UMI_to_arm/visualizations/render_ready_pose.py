"""Render saved ready poses using URDF collision meshes; no hardware access."""
from pathlib import Path
import sys
import struct
import xml.etree.ElementTree as ET
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
import pinocchio as pin
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'arm/mujoco_sim'))
from openarm_urdf_ik import OpenArmDecoupledIk
from openarm_umi_core import load_ready_q, ready_file
font=FontProperties(fname='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc')
plt.rcParams['axes.unicode_minus']=False
k=OpenArmDecoupledIk()
q=np.zeros(k.model.nq)
poses={side:load_ready_q(side) for side in ['right','left']}
for side,values in poses.items():
    for i,value in enumerate(values,1):
        joint=k.model.getJointId(f'openarm_{side}_joint{i}')
        q[k.model.idx_qs[joint]]=value
pin.framesForwardKinematics(k.model,k.data,q)
xml=ET.parse(ROOT/'arm/mujoco_sim/urdf/openarm_bimanual.urdf')
meshes=[]
package=ROOT.parent/'openarm_control/src/openarm_description'
for link in xml.findall('link'):
    name=link.attrib['name']
    for collision in link.findall('collision'):
        mesh=collision.find('geometry/mesh')
        if mesh is None:continue
        path=package/mesh.attrib['filename'].removeprefix('package://openarm_description/')
        blob=path.read_bytes()
        count=struct.unpack_from('<I',blob,80)[0]
        dtype=np.dtype([('normal','<f4',(3,)),('vertices','<f4',(3,3)),('attribute','<u2')])
        vertices=np.frombuffer(blob, dtype=dtype,count=count,offset=84)['vertices'].astype(float)
        vertices*=np.fromstring(mesh.attrib.get('scale','1 1 1'),sep=' ')
        origin=collision.find('origin')
        xyz=np.zeros(3) if origin is None else np.fromstring(origin.attrib.get('xyz','0 0 0'),sep=' ')
        rpy=np.zeros(3) if origin is None else np.fromstring(origin.attrib.get('rpy','0 0 0'),sep=' ')
        transform=k.data.oMf[k.model.getFrameId(name)]*pin.SE3(pin.rpy.rpyToMatrix(rpy),xyz)
        vertices=vertices@transform.rotation.T+transform.translation
        color='#3585cf' if 'right' in name else ('#ed9548' if 'left' in name else '#a5afb9')
        meshes.append((vertices,color))
fig=plt.figure(figsize=(18,9),facecolor='#f7f9fc')
for index,(title,elev,azim) in enumerate([('三维视图',22,38),('侧视：前后 / 上下',0,-90),('俯视：前后 / 左右',90,-90)],1):
    ax=fig.add_subplot(1,3,index,projection='3d',computed_zorder=True)
    for vertices,color in meshes:
        ax.add_collection3d(Poly3DCollection(vertices,facecolors=color,linewidths=0,shade=True))
    ax.set(xlim=(-0.16,0.64),ylim=(-0.53,0.53),zlim=(0,1.02))
    ax.set_box_aspect((0.8,1.06,1.02))
    ax.view_init(elev=elev,azim=azim)
    ax.set_proj_type('ortho')
    ax.set_xlabel('X 前后 (m)',fontproperties=font)
    ax.set_ylabel('Y 左右 (m)',fontproperties=font)
    ax.set_zlabel('Z 上下 (m)',fontproperties=font)
    if index == 2:
        ax.set_yticks([])
        ax.set_ylabel('')
    if index == 3:
        ax.set_zticks([])
        ax.set_zlabel('')
    ax.set_title(title,fontproperties=font,fontsize=17,pad=12)
    ax.set_facecolor('#f7f9fc')
fig.suptitle('OpenArm 当前准备姿态｜右臂蓝色 · 左臂橙色',fontproperties=font,fontsize=23,y=0.93)
right=', '.join(f'{v:.1f}°' for v in np.degrees(poses['right']))
left=', '.join(f'{v:.1f}°' for v in np.degrees(poses['left']))
fig.text(0.5,0.13,'关节 j1 → j7：右臂 ['+right+']\n左臂 ['+left+']',ha='center',fontproperties=font,fontsize=13)
fig.text(0.5,0.055,'读取左右臂保存的 ready 配置。夹爪按闭合绘制。\n依据 URDF 正运动学与简化碰撞网格绘制，不是真机照片；单位为米。',ha='center',fontproperties=font,fontsize=12,color='#526070')
fig.subplots_adjust(left=0.035,right=0.97,bottom=0.24,top=0.82,wspace=0.13)
out=ROOT/'visualizations/current_ready_pose.png'
fig.savefig(out,dpi=150,facecolor=fig.get_facecolor())
print(out)
for side,values in poses.items():
    print(side, values.tolist(), 'saved file exists:',ready_file(side).exists())
print('meshes',len(meshes))
