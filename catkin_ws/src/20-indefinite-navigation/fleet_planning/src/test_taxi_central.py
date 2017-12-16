#!/usr/bin/env python

from taxi_central_node import *
from fleet_planning.srv import *
from std_msgs.msg import Int16MultiArray
from duckietown_msgs.msg import SourceTargetNodes
import unittest
from fleet_planning.message_serialization import LocalizationMessageSerializer

class TestTaxiCentral(unittest.TestCase):

    def test_duckiebot_location_update(self):
        rospy.init_node('test_node')

        duckiebot = Duckiebot('paco')
        start = 5
        stop = 12
        other = 7
        request = CustomerRequest(start, stop)

        # nothing to do, idle
        self.assertEqual(duckiebot.taxi_state, TaxiState.IDLE)

        # new request!
        duckiebot.assign_customer_request(request)

        self.assertEqual(duckiebot._customer_request, request)
        self.assertEqual(duckiebot.taxi_state, TaxiState.GOING_TO_CUSTOMER)

        # now duckiebot is at customer start location
        self.assertEqual(duckiebot.update_location_check_target_reached(start, other), TaxiState.WITH_CUSTOMER)
        self.assertEqual(duckiebot.taxi_state, TaxiState.WITH_CUSTOMER)

        # now duckiebot is at any other location
        self.assertEqual(duckiebot.update_location_check_target_reached(other, stop), None)
        self.assertEqual(duckiebot.taxi_state, TaxiState.WITH_CUSTOMER)

        # now duckiebot is at customer target location
        self.assertEqual(duckiebot.update_location_check_target_reached(stop, other), TaxiState.IDLE)
        self.assertEqual(duckiebot.taxi_state, TaxiState.IDLE)

        # customer request removed
        self.assertEqual(duckiebot.pop_customer_request(), request)
        self.assertEqual(duckiebot._customer_request, None)

    def test_taxi_central_node(self):
        # startup node
        script_dir = os.path.dirname(__file__)
        map_path = os.path.abspath(script_dir)
        csv_filename = 'tiles_lab'

        taxi_central_node = TaxiCentralNode(map_path, csv_filename)
        taxi_central_node._fleet_planning_strategy = FleetPlanningStrategy.DEACTIVATED


        # register customer request
        request_msg = SourceTargetNodes(8, 9)
        taxi_central_node._register_customer_request(request_msg)
        self.assertTrue(isinstance(taxi_central_node._pending_customer_requests[0], CustomerRequest))

        # location update handling
        robot_name = 'paco'

        message = LocalizationMessageSerializer.serialize(robot_name, 9, [11, 13, 15])
        taxi_central_node._location_update(ByteMultiArray(ByteMultiArray,message))
        # robot is registered now
        self.assertTrue(robot_name in taxi_central_node._registered_duckiebots)
        request = taxi_central_node._pending_customer_requests.pop()
        taxi_central_node._registered_duckiebots[robot_name].assign_customer_request(request)
        self.assertTrue(taxi_central_node._registered_duckiebots[robot_name].taxi_state == TaxiState.GOING_TO_CUSTOMER)
        self.assertTrue(len(taxi_central_node._idle_duckiebots()) == 0)

        # set timer to shorter period, test robot time out deregistration
        taxi_central_node.TIME_OUT_CRITERIUM = 1.0
        self._time_out_timer = rospy.Timer(rospy.Duration.from_sec(taxi_central_node.TIME_OUT_CRITERIUM),
                                           taxi_central_node._check_time_out)
        rospy.sleep(1.2)
        # removed bcs of time out
        self.assertTrue(robot_name not in taxi_central_node._registered_duckiebots)

        # request shall be pending again
        self.assertTrue(len(taxi_central_node._pending_customer_requests) == 1)

    def test_location_update(self):
        rospy.wait_for_service('send_location_information')
        fake_location = rospy.ServiceProxy('send_location_information', VirtualDuckiebotLocation)
        fake_location('susi', 5, '7,11,13')


if __name__ == '__main__':
    import rostest
    PKG = 'fleet_planning'
    rostest.rosrun(PKG, 'test_taxi_central', TestTaxiCentral)