####
1. 根据kalibr标定文件生成配置文件
#kalibr标定目录文件 C72-cyperstereo_imu_calibra/cyperstereo_imu_calibra-results-imucam.txt
#修改为自己的相机SN编号(相机中间贴纸数字) cyperstereo_sn_c**.yaml
python3 generate_cyperstereo_yaml.py \
  C72-cyperstereo_imu_calibra/cyperstereo_imu_calibra-results-imucam.txt \
  -t cyperstereo_sn_c72.yaml \
  -o cyperstereo_sn_c**.yaml 

2. 参考build.sh文件编译工程

3. 运行离线数据集
./cyperstereo_offline ../Vocabulary/ORBvoc.txt ../cyperstereo_sn_c**.yaml /home/han/slam_dataset/Cyperstereo/5/left /home/han/slam_dataset/Cyperstereo/5/right /home/han/slam_dataset/Cyperstereo/5/imu/imu.csv

其中../cyperstereo_sn_c**.yaml 是1标定出来的相机配置文件
/home/han/slam_dataset/Cyperstereo/5/left 是采集的左目相机图片文件
/home/han/slam_dataset/Cyperstereo/5/right 是采集的右目相机图片文件
/home/han/slam_dataset/Cyperstereo/5/imu/imu.csv 是采集的imu文件

###
4. 在线运行cyperstereo相机
./cyperstereo_online ../Vocabulary/ORBvoc.txt ../cyperstereo_sn_c**.yaml
其中../cyperstereo_sn_c**.yaml 是1标定出来的相机配置文件
如果电脑的性能不够，注意将帧率调低，目前是15hz
