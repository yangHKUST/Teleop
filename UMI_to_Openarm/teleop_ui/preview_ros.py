#!/usr/bin/env python3
"""Isolated RViz display topics. Reads actual joints; never touches control topics."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import uuid
import yaml
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile,DurabilityPolicy,ReliabilityPolicy,qos_profile_sensor_data
from sensor_msgs.msg import JointState
from std_msgs.msg import String
from geometry_msgs.msg import TransformStamped
from tf2_msgs.msg import TFMessage
from model_state import DisplayModel

ROOT=Path(__file__).resolve().parents[1]
URDF=ROOT/'UMI_to_arm/arm/mujoco_sim/urdf/openarm_bimanual.urdf'


class ViewNode(Node):
    def __init__(self,directory,topic):
        super().__init__('openarm_ui_view_'+uuid.uuid4().hex[:8])
        self.directory=directory;self.topic=topic;self.text=URDF.read_text();self.model=DisplayModel(self.text)
        qos=QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL,reliability=ReliabilityPolicy.RELIABLE)
        self.description=self.create_publisher(String,topic+'/robot_description',qos)
        self.static=self.create_publisher(TFMessage,topic+'/tf_static',qos)
        self.dynamic=self.create_publisher(TFMessage,topic+'/tf',10)
        self.create_subscription(JointState,'/joint_states',self.receive,qos_profile_sensor_data)
        self.create_timer(1/30,self.tick);self.published_static=False;self.last_status=0

    def receive(self,msg):self.model.receive(msg.name,msg.position,time.monotonic())

    def tick(self):
        now=time.monotonic()
        try:mode=json.loads((self.directory/'selection.json').read_text())['mode']
        except (OSError,ValueError,KeyError):mode='dual'
        pose,status=self.model.snapshot(now,mode)
        fixed=[];dynamic=[];stamp=self.get_clock().now().to_msg()
        for joint in self.model.joints:
            xyz,q=self.model.transform(joint,pose)
            msg=TransformStamped();msg.header.stamp=stamp;msg.header.frame_id=joint['parent'];msg.child_frame_id=joint['child']
            msg.transform.translation.x,msg.transform.translation.y,msg.transform.translation.z=map(float,xyz)
            msg.transform.rotation.x,msg.transform.rotation.y,msg.transform.rotation.z,msg.transform.rotation.w=map(float,q)
            (fixed if joint['kind']=='fixed' else dynamic).append(msg)
        self.dynamic.publish(TFMessage(transforms=dynamic))
        if not self.published_static:
            self.static.publish(TFMessage(transforms=fixed));self.description.publish(String(data=self.text));self.published_static=True
        if now-self.last_status>.2:
            temp=self.directory/'status.tmp';temp.write_text(json.dumps(status,ensure_ascii=False));temp.replace(self.directory/'status.json');self.last_status=now


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True);args=parser.parse_args()
    topic='/openarm_ui_view_'+uuid.uuid4().hex
    config=yaml.safe_load((ROOT/'openarm_control/src/openarm_description/rviz/bimanual.rviz').read_text())
    config['Panels']=[]
    config['Window Geometry']={'Width':700,'Height':650,'Hide Left Dock':True,'Hide Right Dock':True}
    manager=config['Visualization Manager']
    manager['Views']['Current'].update({'Distance':2.5,'Pitch':.25,'Yaw':0.0,'Focal Point':{'X':0.0,'Y':0.0,'Z':.15}})
    for display in manager['Displays']:
        if display['Class']=='rviz_default_plugins/RobotModel':
            display['Description Topic']['Value']=topic+'/robot_description'
            display['Description Topic']['Durability Policy']='Transient Local'
            display['Links']={'All Links Enabled':True}
        if display['Class']=='rviz_default_plugins/TF':display['Enabled']=False;display['Value']=False
    path=args.directory/'display.rviz';path.write_text(yaml.safe_dump(config,sort_keys=False))
    rclpy.init();node=ViewNode(args.directory,topic)
    proc=subprocess.Popen(['rviz2','-d',str(path),'--ros-args','-r','/tf:='+topic+'/tf','-r','/tf_static:='+topic+'/tf_static'])
    try:
        while rclpy.ok() and proc.poll() is None:rclpy.spin_once(node,timeout_sec=.1)
    except KeyboardInterrupt:pass
    finally:
        if proc.poll() is None:
            proc.terminate()
            try:proc.wait(timeout=5)
            except subprocess.TimeoutExpired:proc.kill();proc.wait()
        node.destroy_node()
        if rclpy.ok():rclpy.shutdown()

if __name__=='__main__':main()
