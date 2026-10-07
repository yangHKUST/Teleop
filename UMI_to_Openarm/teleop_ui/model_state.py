"""Display-only pose selection and URDF transforms; no command publishers."""
import math
import xml.etree.ElementTree as ET


def multiply(a,b):
    x,y,z,w=a; X,Y,Z,W=b
    return (w*X+x*W+y*Z-z*Y,w*Y-x*Z+y*W+z*X,w*Z+x*Y-y*X+z*W,w*W-x*X-y*Y-z*Z)


def rotate(q,v):
    return multiply(multiply(q,(*v,0)),(-q[0],-q[1],-q[2],q[3]))[:3]


def origin_rotation(rpy):
    roll,pitch,yaw=rpy
    return multiply(multiply((0,0,math.sin(yaw/2),math.cos(yaw/2)),(0,math.sin(pitch/2),0,math.cos(pitch/2))),(math.sin(roll/2),0,0,math.cos(roll/2)))


class DisplayModel:
    def __init__(self,urdf):
        self.joints=[]; self.defaults={}; self.values={};self.received={}
        self.last_pose={};self.ever_real=set()
        for element in ET.fromstring(urdf).findall('joint'):
            kind=element.get('type');name=element.get('name')
            origin=element.find('origin');axis=element.find('axis');mimic=element.find('mimic')
            numbers=lambda value:tuple(map(float,value.split()))
            joint=dict(name=name,kind=kind,parent=element.find('parent').get('link'),child=element.find('child').get('link'),
                xyz=numbers(origin.get('xyz','0 0 0')) if origin is not None else (0,0,0),
                rotation=origin_rotation(numbers(origin.get('rpy','0 0 0')) if origin is not None else (0,0,0)),
                axis=numbers(axis.get('xyz','1 0 0')) if axis is not None else (1,0,0),
                mimic=dict(mimic.attrib) if mimic is not None else None)
            self.joints.append(joint)
            if kind!='fixed':self.defaults[name]=math.pi/2 if name.endswith('_joint4') else 0.0
        self.groups={side:[f'openarm_{side}_joint{i}' for i in range(1,8)] for side in ('left','right')}

    def receive(self,names,positions,now):
        for name,value in zip(names,positions):
            if name in self.defaults and math.isfinite(value):
                self.values[name]=float(value);self.received[name]=now

    def snapshot(self,now,mode='dual',max_age=.5):
        pose=dict(self.defaults);status={}
        for side,names in self.groups.items():
            if mode not in ('dual',side):
                status[side]='未启用 · 默认姿态预览';continue
            fresh=all(name in self.values and now-self.received[name]<=max_age for name in names)
            if fresh:
                self.ever_real.add(side)
                self.last_pose[side]={name:self.values[name] for name in self.defaults if name.startswith(f'openarm_{side}_') and name in self.values}
                status[side]='实时反馈'
            elif side in self.ever_real:
                status[side]='反馈中断 · 保留最后姿态'
            else:
                status[side]='无反馈 · 默认姿态预览'
            pose.update(self.last_pose.get(side,{}))
        return pose,status

    def transform(self,joint,pose):
        value=pose.get(joint['name'],0)
        if joint['mimic']:
            mimic=joint['mimic'];value=pose.get(mimic['joint'],0)*float(mimic.get('multiplier',1))+float(mimic.get('offset',0))
        xyz=joint['xyz'];q=joint['rotation'];axis=joint['axis']
        if joint['kind'] in ('revolute','continuous'):
            norm=math.sqrt(sum(v*v for v in axis))
            motion=tuple(v/norm*math.sin(value/2) for v in axis)+(math.cos(value/2),)
            q=multiply(q,motion)
        elif joint['kind']=='prismatic':
            displacement=rotate(q,tuple(v*value for v in axis))
            xyz=tuple(a+b for a,b in zip(xyz,displacement))
        return xyz,q
