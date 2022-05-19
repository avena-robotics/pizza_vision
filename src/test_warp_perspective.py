import cv2
import imutils
import json
import numpy as np
import pytesseract
import time

from utils import build_intel_handle, calculate_rotation, compare_string, distance_2d


if __name__ == '__main__':
    # Serial number of Intel camera
    serial = "037522060116"
    # Get intel camera handle
    intel_handle = build_intel_handle(serial)

    # DEFINE HELPERS OBJECTS AND CONSTANTS
    # Image ROI boundaries
    lower_y = 30
    lower_x = 240
    upper_x = 1850
    # Dilation kernel for reflections mask
    disk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    # Dilation kernel for thresholded image
    dil_kernel = 4
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (dil_kernel, dil_kernel))
    # Number of iterations of dilation
    number_of_iterations = 3
    # Reflections threshold
    reflections_threshold = 244
    # Adaptive thresholding parameters
    window = 21
    c = 25
    # CCA params
    min_component_area = 4e3
    max_component_area = 25e3

    # Full ketchup mid
    shape0_full_ketchup_mid = 23
    shape1_full_ketchup_mid = 83
    v1 = [shape0_full_ketchup_mid, shape1_full_ketchup_mid]

    pts1 = np.float32([[140, 5], [1900, 10], [335, 1057], [1675, 1060]])
    pts2 = np.float32([[0, 0], [1410, 10], [0, 1000], [1410, 1000]])

    M = cv2.getPerspectiveTransform(pts1, pts2)

    # Infinite loop to analyze images
    while True:
        # Measure the time
        start = time.perf_counter()
        # Get camera data
        frames = intel_handle.wait_for_frames(timeout_ms=2000)
        # Get color frame from camera data
        color_frame = frames.get_color_frame()
        # Convert color frame to numpy (opencv)
        img = np.asanyarray(color_frame.get_data())
        img_warped = cv2.warpPerspective(img, M, (1410, 1000))
        # Crop ROI
        cv2.imshow("img", img)
        cv2.imshow("img_warped", img_warped)
        if cv2.waitKey(1) & 0xff == ord('q'):
            break
        