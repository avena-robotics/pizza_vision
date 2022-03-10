import math
import numpy as np
import pyrealsense2 as rs
import time


def build_intel_handle(serial: str):
    """
    Function returning Inteal Realsense handler with specific parameters

    Input:
        @param :serial Serial number of the camera

    Ourput:
        Handler
    """
    # Create camera config object
    camera_config = rs.config()

    # Set resolution of the stream
    camera_config.enable_stream(rs.stream.color, 1920, 1080, rs.format.bgr8, 30)

    # Enable device
    camera_config.enable_device(serial)
    camera_handle = rs.pipeline()
    camera_pipeline_profile = camera_handle.start(camera_config)
    camera_device = camera_pipeline_profile.get_device()
    # Turn on advanced mode
    advanced_mode = rs.rs400_advanced_mode(camera_device)
    
    # Set desired options
    sensors = camera_device.query_sensors()
    for sensor in sensors:
        if rs.sensor.as_color_sensor(sensor):
            sensor.set_option(rs.option.enable_auto_exposure, 1)
            sensor.set_option(rs.option.enable_auto_white_balance, 1)

    # Sleep short time to stabilize camera
    time.sleep(1)
    # Return handler
    return camera_handle

def calculate_rotation(box_points: np.ndarray):
    """
    Function calculating rotation of the plate.

    Input:
        @param :box_points Array of box points, where point at index 0 is the lowest one
        and rest are organized counterclockwise starting from the lowest one.
    
    Output:
        Rotation angle in radians
    """
    # Take points from rotated bounding box
    lowest = box_points[3]
    nghbr1 = box_points[0]
    nghbr2 = box_points[2]
    # Compute distance between lowest point and each neighbor
    distance_lowest_nghbr1 = np.linalg.norm(lowest - nghbr1)
    distance_lowest_nghbr2 = np.linalg.norm(lowest - nghbr2)

    # Try longer edge
    if distance_lowest_nghbr1 < distance_lowest_nghbr2:
        second_point = nghbr2
    else:
        second_point = nghbr1

    # Compute coeficients of line Ax + b
    slope = (lowest[1] - second_point[1]) / (lowest[0] - second_point[0])

    # Compute angle of slope
    angle = np.arctan2(slope, 1)

    # Return value
    return angle, lowest, second_point, slope

def compare_string(s: str):
    """
    Function to decide if output of tesseract is "ketchup"

    Input:
        @param: s string to be analyzed

    Output:
        Boolean
    """

    # If string is empty nothing to compare
    if not s:
        return False

    # convert to lower letters to unify strings
    s = s.lower()

    # check for 3 characters long similarities
    if 'ket' in s or 'etc' in s or 'tch' in s or 'chu' in s or 'hup' in s:
        return True
    return False


def distance_2d(v1, v2):
    """
    Function computing 2D Euclidean distance.

    Input:
        @param :v1 first 2d vector
        @param :v2 second 2d vector

    Output:
        Euclidean distance of two 2d vectors.
    """
    return math.sqrt((v1[0] - v2[0])**2 + (v1[1] - v2[1])**2)