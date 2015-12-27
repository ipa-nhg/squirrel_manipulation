#include "../include/SimplePush.hpp"

using namespace std;

SimplePush::SimplePush():
    PushPlanner()
{
    private_nh.param("push/error_theta_tolerance", err_th_toll_,0.1);
    private_nh.param("push/error_target_tolerance", err_t_toll_ ,0.01);
    private_nh.param("push/velocity_angular_max", vel_ang_max_ ,0.3);
    private_nh.param("push/velocity_linear_max", vel_lin_max_ ,0.3);
    private_nh.param("push/velocity_y_max", vel_y_max_ ,0.3);
}

geometry_msgs::Twist SimplePush::getVelocities(){
    //initialize value
    geometry_msgs::Twist cmd;
    cmd.linear.x = 0.0;
    cmd.linear.y = 0.0;
    cmd.linear.z = 0.0;
    cmd.angular.x = 0.0;
    cmd.angular.y = 0.0;
    cmd.angular.z = 0.0;


    geometry_msgs::PoseStamped target_ = this->getLookaheadPoint();

    //angle between object pose and target
    double aO2T = atan2(target_.pose.position.y - pose_object_.pose.position.y, target_.pose.position.x - pose_object_.pose.position.x);
    if (isnan(aO2T)) aO2T = 0;

    //orientation error
    double err_th = pose_robot_.theta - aO2T;

    //translation error object-target
    double dO2T = distancePoints(pose_object_.pose.position.x, pose_object_.pose.position.y, target_.pose.position.x, target_.pose.position.y);


    if (dO2T < 0.05){
        goal_reached_ = true;
        cmd.angular.z = 0.0;
        cmd.linear.x = 0.0;
        cmd.linear.y = 0.0;
        return cmd;

    }


    if (err_th < - err_th_toll_) {
        //rotating left and moving right
        cmd.angular.z =  vel_ang_max_;
        cmd.linear.y = - vel_y_max_;
    }
    else if (err_th > err_th_toll_){
        //rotating right and moving left
        cmd.angular.z =  - vel_ang_max_;
        cmd.linear.y = vel_y_max_;
    }
    else {
        cmd.angular.z = 0.0;
        cmd.linear.y = 0.0;
    }

    if (dO2T > err_t_toll_){
        cmd.linear.x = vel_lin_max_;
    }
    else{
        cmd.linear.x = 0.0;
    }

    return cmd;

}
