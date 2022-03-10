import cv2
import imutils
import json
import numpy as np
import pytesseract
import time

from utils import build_intel_handle, calculate_rotation, compare_string, distance_2d


if __name__ == '__main__':
    # Serial number of Intel camera
    serial = "121622061205"
    # Get intel camera handle
    intel_handle = build_intel_handle(serial)

    # DEFINE HELPERS OBJECTS AND CONSTANTS
    # Image ROI boundaries
    lower_y = 80
    lower_x = 390
    upper_x = 1800
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
        # Crop ROI
        img = img[lower_y:, lower_x:upper_x]
        # Convert to grayscale
        img_grayscale = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # Get specularity mask
        _, specularity_mask = cv2.threshold(img_grayscale, reflections_threshold, 255, cv2.THRESH_BINARY)
        # Dilate specularity mask
        specularity_mask = cv2.dilate(specularity_mask, disk, iterations=2)
        # Remove reflections
        img_grayscale = cv2.inpaint(img_grayscale, specularity_mask, 5, cv2.INPAINT_NS)
        # Adaptive thresholding
        thresh_adaptive = cv2.adaptiveThreshold(img_grayscale, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                                cv2.THRESH_BINARY_INV, window, c)
        # Perform morphological operation on thresholded image
        dilated_threshold = cv2.dilate(thresh_adaptive, kernel, iterations=number_of_iterations)

        # Connected Components Analysis
        output = cv2.connectedComponentsWithStats(dilated_threshold, 8, cv2.CV_32S)
        # Unpack tuple
        (numLabels, labels, stats, centroids) = output

        # Iterate over components. Start from 1 because 0 is a background
        list_of_items = []
        for i in range(1, numLabels):
            # Skip component if its area is too small or too big
            if stats[i, cv2.CC_STAT_AREA] < min_component_area or stats[i, cv2.CC_STAT_AREA] > max_component_area:
                continue
            # Get area of component
            x = stats[i, cv2.CC_STAT_LEFT]
            y = stats[i, cv2.CC_STAT_TOP]
            w = stats[i, cv2.CC_STAT_WIDTH]
            h = stats[i, cv2.CC_STAT_HEIGHT]
            # Get center of component
            (cX, cY) = centroids[i]

            image_grayscale_copy = img_grayscale.copy()
            # get the area to analyze
            patch = image_grayscale_copy[y:y + h, x:x + w]

            # Binarize patch
            _, thresh_patch = cv2.threshold(patch, 0, 255, cv2.THRESH_OTSU, cv2.THRESH_BINARY)
            # Dilate to close contours
            thresh_patch_dilated = cv2.dilate(thresh_patch, kernel, iterations=1)
            # Find EXTERNAL contours
            contours_path, _ = cv2.findContours(thresh_patch_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            # Sort contours from the biggest one to the smallest one
            contours_path = sorted(contours_path, key=lambda cnt: cv2.contourArea(cnt), reverse=True)
            # Prepare a canvas for the mask
            masked_image = np.zeros(patch.shape, dtype=np.uint8)
            # Draw the biggest contour area
            cv2.drawContours(masked_image, [contours_path[0]], -1, 255, -1, cv2.LINE_AA)
            # Get the object contoured by the biggest contour
            thresh_patch_masked = cv2.bitwise_and(thresh_patch, masked_image)
            # Get AABB of the biggest contour
            x_cnt, y_cnt, w_cnt, h_cnt = cv2.boundingRect(contours_path[0])
            # Get RBB of the biggest contour
            min_rect = cv2.minAreaRect(contours_path[0])
            # Convert RBB to the box points. First one is the most left, rest clockwise
            box_crop = cv2.boxPoints(min_rect)
            # Compute parameters of RBB from its box points
            angle, lower, second, slope = calculate_rotation(box_crop)
            # Crop the area of AABB from thresholded patch
            to_rotate = thresh_patch[y_cnt:y_cnt + h_cnt, x_cnt:x_cnt + w_cnt]
            # Rotate patch to get strings vertically for OCR
            rotated_crop = imutils.rotate_bound(to_rotate, -angle * 180 / np.pi)
            # Dilate binary image to close contours
            rotated_crop_dilated = cv2.dilate(rotated_crop, kernel, iterations=1)
            # Get contours of rotated candidate
            rotated_crop_contours, _ = cv2.findContours(rotated_crop_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            # Sort contours to get the biggest one
            rotated_crop_contours = sorted(rotated_crop_contours, key=lambda contour: cv2.contourArea(contour))
            # Tight the AABB, it will be possible smallest after alignment
            x_candidate, y_candidate, w_candidate, h_candidate = cv2.boundingRect(rotated_crop_contours[-1])
            final_path_to_analyze = rotated_crop[y_candidate:y_candidate + h_candidate,
                                                 x_candidate:x_candidate + w_candidate]

            # ANALYZE OBJECTNESS OF THE FINAL CROP
            # Examine region for "KETCHUP"
            # Options:
            # * is upside down
            # * is K visible
            # * is p visible
            # * center
            # * angle

            # Examine region for CIRCLE
            # Options:
            # * center

            # Examine region for BARCODE
            # Options:
            # * Angle
            # * Center

            # Examine region for BACKSTRING
            # Options:
            # * Center

            # Computer aspect ratio of the area
            aspect_ratio = final_path_to_analyze.shape[1] / final_path_to_analyze.shape[0]
            # Compute solidity of the area
            solidity = cv2.countNonZero(final_path_to_analyze) / (final_path_to_analyze.shape[0] *
                                                                  final_path_to_analyze.shape[1])
            # Check for Circle
            is_circle = False
            circle_dictionary = {}
            # Threshold aspect ratio and solidity
            if 1.1 > aspect_ratio > 0.9 and solidity < 0.8:
                is_circle = True
            # If circle fill dict to be saved
            if is_circle:
                circle_dictionary["Name"] = "Circle"
                circle_dictionary["Center"] = (int(cX), int(cY))
                list_of_items.append(circle_dictionary)
            if is_circle:
                continue

            # Check for Barcode
            is_barcode = False
            barcode_dictionary = {}
            # Threshold aspect ratio and solidity
            if 1.6 > aspect_ratio > 1.3 and solidity > 0.7:
                is_barcode = True

            # If barcode fill dict to be saved
            if is_barcode:
                barcode_dictionary["Name"] = "Barcode"
                barcode_dictionary["Center"] = (int(cX), int(cY))
                barcode_dictionary["Angle"] = angle
                list_of_items.append(barcode_dictionary)
            if is_barcode:
                continue

            # Check for backside string
            is_backside_string = False
            backside_string_dictionary = {}
            # Threshold aspect ratio and solidity
            if 3.25 > aspect_ratio > 2.9 and 0.55 > solidity > 0.45:
                is_backside_string = True

            # If backside string fill dict to be saved
            if is_backside_string:
                backside_string_dictionary["Name"] = "Backside String"
                backside_string_dictionary["Center"] = (int(cX), int(cY))
                list_of_items.append(backside_string_dictionary)
            if is_backside_string:
                continue

            # Check for Ketchup
            is_ketchup = False
            ketchup_string = ""
            ketchup_dictionary = {}

            # Detect possible text and check if its "Ketchup"
            text_normal = pytesseract.image_to_string(cv2.bitwise_not(final_path_to_analyze), lang='eng',
                                                      config='--psm 7')
            if_text_normal = compare_string(text_normal)
            if if_text_normal:
                is_ketchup = True
                ketchup_dictionary["Upside_down"] = False
                ketchup_string = text_normal
            # If not, rotate patch upside down and try again
            else:
                text_upside_down = pytesseract.image_to_string(cv2.rotate(cv2.bitwise_not(final_path_to_analyze),
                                                                          cv2.ROTATE_180), lang='eng', config='--psm 7')
                if_text_upside_down = compare_string(text_upside_down)
                if if_text_upside_down:
                    is_ketchup = True
                    ketchup_dictionary["Upside_down"] = True
                    ketchup_string = text_upside_down
            # If this is the ketchup continue analysis
            if is_ketchup:
                # Is K visible?
                if ketchup_string[0] == 'K' or ketchup_string[0] == 'k':
                    ketchup_dictionary["K_visible"] = True
                else:
                    ketchup_dictionary["K_visible"] = False
                # Is p visible?
                if ketchup_string[-2] == 'P' or ketchup_string[-2] == 'p':
                    ketchup_dictionary["p_visible"] = True
                else:
                    ketchup_dictionary["p_visible"] = False
                if not ketchup_dictionary["p_visible"]:
                    v2 = [final_path_to_analyze.shape[0] / 2, final_path_to_analyze.shape[1] / 2]
                    distance = distance_2d(v1, v2)
                    ketchup_dictionary["distance_to_add"] = distance
                # Save results to dict
                ketchup_dictionary["Name"] = "Ketchup"
                ketchup_dictionary["Angle"] = angle
                ketchup_dictionary["Ketchup_string"] = ketchup_string
                ketchup_dictionary["Center"] = (int(cX), int(cY))
                list_of_items.append(ketchup_dictionary)
        end = time.perf_counter()
        print(f"Inference took {end - start} seconds!")
        # Save data to the JSON file
        print("Preview of items")
        for item in list_of_items:
            print(item)
        name = input("Name for JSON. If dont want to save press ENTER")
        if name:
            print("Saving data JSON...")
            with open("/home/avena/PycharmProjects/ketchup_binpicking/output/" + name + '.json', 'w') as f:
                json.dump(list_of_items, f, indent=3)
            print("Saving photo for this JSON...")
            cv2.imwrite("/home/avena/PycharmProjects/ketchup_binpicking/output/" + name + '.png', img)
            input("Data saved! Press ENTER to continue!")
