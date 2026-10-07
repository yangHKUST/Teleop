#include <opencv2/highgui/highgui.hpp>
#include <iostream>
#include <fstream>
#include <vector>
#include <glob.h>
#include <unistd.h>
#include <dirent.h>
#include <stdlib.h>
#include <string>
#include <stdio.h>
#include <map>
#include <Eigen/Dense>
#include <System.h>

using namespace std;


int get_int_from_string(string& str);
//get num in file name in sort from small to big
vector<int> getFiles(char* dirc){
    vector<string> files;
    struct dirent *ptr;
    DIR *dir;
    dir = opendir(dirc);
    
    if(dir == NULL)
    {
        perror("open dir error ...");
        exit(1);
    }

    while((ptr = readdir(dir)) != NULL){
        if(strcmp(ptr->d_name,".")==0 || strcmp(ptr->d_name,"..")==0)    ///current dir OR parrent dir  
            continue;  
        if(ptr->d_type == 8)//it;s file
        {
            files.push_back(ptr->d_name);
        }

        else if(ptr->d_type == 10)//link file
            continue;
        else if(ptr->d_type == 4) //dir
        {
            files.push_back(ptr->d_name);
        }
    }
    closedir(dir);
    
    vector<int> result;
    for(int i=0;i < files.size();i++)
    {
        result.push_back(get_int_from_string(files[i]));
    }
    sort(result.begin(),result.end());

    for(size_t i = 0; i < result.size();++i){
        //cout << result[i] << endl;
    }
    return result;
}

int get_int_from_string(string& str)
{
    int result = 0;
    for(int i = 0; i < str.size(); i++)
    {
        if (str[i] >= '0'&& str[i] <= '9')  
        {  
            result = result * 10 + str[i] - 48;  
        }  
    }
    return result;
}


int main(int argc, char** argv)
{   
    if (argc != 6)
    {
        cout << "usage: image_publisher left_image_folder right_image_folder imu_file " << endl;
        return -1;
    }
    ORB_SLAM3::System SLAM(argv[1],argv[2],ORB_SLAM3::System::IMU_STEREO, true);
    
    std::cout << argv[1] << std::endl;
    std::cout << argv[2] << std::endl;
    std::cout << argv[3] << std::endl;
    std::cout << argv[4] << std::endl;
    std::cout << argv[5] << std::endl;
    vector<int> left_image_count = getFiles(argv[3]);// 
    vector<int> right_image_count = getFiles(argv[4]);
    FILE *fp;
    fp = fopen(argv[5],"r");
    double imu_time,last_imu_time;
    float acceleration[3],angular_v[3];
    float last_acceleration[3], last_angular_v[3];
    int time_count_left,time_count_right;
    int imu_seq = 1;
    std::map<int,int> imu_big_interval;
    int fscanf_return;
    fscanf_return = fscanf(fp,"%lf,%f,%f,%f,%f,%f,%f",
                &imu_time,angular_v,angular_v+1,angular_v+2,acceleration,acceleration+1,acceleration+2);
    last_acceleration[0] = acceleration[0];
    last_acceleration[1] = acceleration[1];
    last_acceleration[2] = acceleration[2];
    last_angular_v[0] = angular_v[0];
    last_angular_v[1] = angular_v[1];
    last_angular_v[2] = angular_v[2];
    last_imu_time = imu_time;
    if (fscanf_return != 7)
    {
        std::cout << "imu format error " << last_imu_time <<std::endl;
        fclose(fp);
        return -1;
    }
    for(size_t i = 10;(i < right_image_count.size() - 10) ;++i)
    {
        std::vector<ORB_SLAM3::IMU::Point> vImuMeas;
        vImuMeas.clear();    

        if (feof(fp))
            break;
        
        ostringstream stringStream;
        //转换左图
        std::string left_filename = string(argv[3]) + "/" + to_string(left_image_count[i]) + ".png";
        cv::Mat left_image = cv::imread(left_filename);
        if(left_image.empty()) {
            std::cout << "left image empty" << std::endl;
            return 0;
        }
        time_count_left = left_image_count[i];
    
        //转换右图
        std::string right_filename = string(argv[4])+"/"+ to_string(right_image_count[i]) + ".png";
        cv::Mat right_image = cv::imread(right_filename);
        if(right_image.empty()) {
            std::cout << "right image empty" << std::endl;
            return 0;
        }
        time_count_right = right_image_count[i];
        if(time_count_left != time_count_right) {
           std::cout << "left image time != right image time" <<  time_count_left << std::endl;
           return -1; 
        }
        // std::cout << "imu_time: " << imu_time << " " << last_angular_v[0] << " " << last_angular_v[1] << " " << last_angular_v[2] << " " << last_acceleration[0] <<  " " << last_acceleration[1] <<  " " << last_acceleration[2] << std::endl;                                         
        while (imu_time < left_image_count[i]*0.0001 - 0.005) {
            if (last_imu_time > imu_time) {
                std::cout << "imu time disorder" << last_imu_time << std::endl;
            }
            if (imu_time - last_imu_time > 0.5) {
                std::cout << "large interval in imu" << last_imu_time << std::endl;
            }
            vImuMeas.push_back(ORB_SLAM3::IMU::Point(acceleration[0],acceleration[1],acceleration[2],
                                         angular_v[0],angular_v[1],angular_v[2],imu_time));
                        
            last_imu_time = imu_time;
            fscanf_return = fscanf(fp,"%lf,%f,%f,%f,%f,%f,%f",
                &imu_time,angular_v,angular_v+1,angular_v+2,acceleration,acceleration+1,acceleration+2);
            last_acceleration[0] = acceleration[0] ;
            last_acceleration[1] = acceleration[1] ;
            last_acceleration[2] = acceleration[2] ;
            last_angular_v[0] = angular_v[0] ;
            last_angular_v[1] = angular_v[1] ;
            last_angular_v[2] = angular_v[2] ;
            if (fscanf_return != 7) {
                std::cout << "imu format error " << last_imu_time <<std::endl;
                fclose(fp);
                return -1;
            }
            std::cout.setf(std::ios::fixed, std::ios::floatfield);
	        std::cout.precision(6);
            // std::cout << "imu_time: " << imu_time << " " << angular_v[0] << " " << angular_v[1] << " " << angular_v[2] << " " << acceleration[0] <<  " " << acceleration[1] <<  " " << acceleration[2] << std::endl;
        }
        std::cout << "image time: " << time_count_left * 0.0001 << std::endl;
        // cv::imshow("left", left_image_res);
        // cv::imshow("right", right_image_res);
        // cv::waitKey(1);

        Sophus::SE3f Tcw = SLAM.TrackStereo(left_image, right_image, time_count_left * 0.0001, vImuMeas);
        Eigen::Vector3f t = Tcw.translation();     
        Eigen::Quaternionf q = Tcw.unit_quaternion();
        std::cout << std::fixed << std::setprecision(6)
            << "timestamp " << time_count_left * 0.0001<< " " << t.x() << " " << t.y() << " " << t.z()<< 
            " q " << q.x() << " " << q.y() << " " << q.z() << " " << q.w() << std::endl;
        //SLAM.TrackStereo(left_image, right_image, time_count_left * 0.0001f);
        //SLAM.TrackMonocular(left_image, time_count_left * 0.0001, vImuMeas);
        usleep(50000);
    }
    
    SLAM.Shutdown();
    SLAM.SaveTrajectoryEuRoC("CameraTrajectory.txt");
    // SLAM.SaveKeyFrameTrajectoryEuRoC("KeyFrameTrajectory.txt");
    fclose(fp);
    return 0;

}
