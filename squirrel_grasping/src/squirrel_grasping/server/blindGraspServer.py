import rospy
import actionlib
import numpy as np
import tf
from geometry_msgs.msg import PoseStamped

from squirrel_manipulation_msgs.msg import BlindGraspActionAction
from squirrel_manipulation_msgs.msg import BlindGraspActionResult
from squirrel_manipulation_msgs.msg import BlindGraspActionFeedback

from kclhand_control.srv import graspCurrent, graspPreparation

from moveit_commander import roscpp_initialize, roscpp_shutdown, MoveGroupCommander



class BlindGraspServer(object):

    #units in meter?

    _result = BlindGraspActionResult()
    _feedback = BlindGraspActionFeedback()
    _span = .1 #10 cm
    _dist_2_hand = .025 #2.5 cm

    def __init__(self):
        while rospy.get_time() == 0.0: pass
        rospy.loginfo(rospy.get_caller_id() + ': starting BlindGraspServer')
        self._server = actionlib.SimpleActionServer('blindGrasp', BlindGraspActionAction, execute_cb=self.execute_grasp, auto_start=False)
        self._prepareGrasp = rospy.ServiceProxy('prepareGrasp', graspPreparation)
        self._closeFinger = rospy.ServiceProxy('closeFinger', graspCurrent)
        self._openFinger = rospy.ServiceProxy('openFinger', graspPreparation)
        self._server.start()
        self._tf = tf.TransformListener()

    
    def execute_grasp(self, goal):

        self._feedback.current_phase = 'BlindGrasp: parsing action goal'
        self._feedback.current_status = 'BlindGrasp: preparing action execution'
        self._feedback.percent_completed = 0.0

        self._server.publish_feedback(self._feedback)
        
        rospy.loginfo(rospy.get_caller_id() + ': Requested blind grasp of object %s'.format(goal.object_id))

        # check that preempt has not been requested by the client
        # this needs refinement for the next iteration after Y2 review
        if self._server.is_preempt_requested():
            rospy.loginfo('BlindGrasp: preempted')
            self._server.set_preempted()
            return

        self._feedback.current_phase = 'BlindGrasp: computing gripper pose'
        self._feedback.current_status = 'BlindGrasp: preparing action execution'
        self._feedback.percent_completed = 0.3
        self._server.publish_feedback(self._feedback)

        d = goal.heap_bounding_cylinder.height/2.0

        pose = PoseStamped()
        pose.header.stamp = rospy.Time.now()
        pose.header.frame_id = goal.heap_center_pose.header.frame_id
        pose.pose.position.x = goal.heap_center_pose.pose.position.x
        pose.pose.position.x = goal.heap_center_pose.pose.position.y
        pose.pose.position.x = goal.heap_center_pose.pose.position.z + d + _dist_2_hand
        pose.pose.orientation.w = 0.0
        pose.pose.orientation.x = -1.0
        pose.pose.orientation.y = 0.0
        pose.pose.orientation.z = 0.0

        '''
        if goal.heap_bounding_box.x > _span:
            d_ = goal.heap_bounding_cylinder.diameter/2.0
            pose.pose.position.x = pose.pose.position.x + d_
        '''

        self._feedback.current_phase = 'BlindGrasp: moving gripper'
        self._feedback.current_status = 'BlindGrasp: executing action'
        self._feedback.percent_completed = 0.6
        self._server.publish_feedback(self._feedback)

        roscpp_initialize(sys.argv)
        group = MoveGroupCommander('arm')
        group.set_end_pose_reference_frame(goal.heap_center_pose.header.frame_id)
        group.clear_pose_targets()
        group.set_start_state_to_current_state()
        group.set_pose_target(pose)
        plan = group.plan()

        if self.is_empty(plan):
            self._feedback.current_phase = 'BlindGrasp: aborted - no plan found'
            self._feedback.current_status = 'BlindGrasp: aborted action execution'
            self._feedback.percent_completed = 1
            self._server.publish_feedback(self._feedback)

            self._result.result_status = 'BlindGrasp: failed to grasp object %s'.format(goal.object_id) 
            rospy.loginfo('BlindGrasp: failed')
            self.server.set_succeeded(self._result)
           
        else:
            self._feedback.current_phase = 'BlindGrasp: grasping'
            self._feedback.current_status = 'BlindGrasp: executing action'
            self._feedback.percent_completed = 9
            self._server.publish_feedback(self._feedback)

            self._prepareGrasp()
            group.go(wait=True)
            self._closeFingers(1.0)

            # lift object
            group.clear_pose_targets()
            group.set_start_state_to_current_state()
            pose.pose.position.z = pose.pose.position.z + 0.3
            group.set_pose_target(pose)
            group.plan()
            group.go(wait=True)
            
            self._feedback.current_phase = 'BlindGrasp: grasping succeeded'
            self._feedback.current_status = 'BlindGrasp: finished action execution'
            self._feedback.percent_completed = 1
            self._server.publish_feedback(self._feedback)


            self._result.result_status = 'BlindGrasp: grasped object %s'.format(goal.object_id) 
            rospy.loginfo('BlindGrasp: succeeded')
            self.server.set_succeeded(self._result)            
            

    def is_empty(self, plan):
        if len(plan.joint_trajectory.points) == 0 and
            len(plan.multi_dof_joint_trajectory.points) == 0:
            return False
        return True
