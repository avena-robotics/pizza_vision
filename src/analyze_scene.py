import json
import numpy as np
import cv2


from utils import distance_2d

# Globals for helper
global x_first, y_first, x_second, y_second


# Helper function for distance measuring
def click_event(event, x, y, _, __):
    global x_first, y_first, x_second, y_second
    if event == cv2.EVENT_LBUTTONDOWN:
        x_first = x
        y_first = y
        print("First point set to", x_first, y_first)
    if event == cv2.EVENT_RBUTTONDOWN:
        x_second = x
        y_second = y
        print("Second point set to", x_second, y_second)
    if event == cv2.EVENT_MBUTTONDOWN:
        print(distance_2d([x_first, y_first], [x_second, y_second]))


# Read scene data
with open(r"C:\Users\Robo\Desktop\software\pizza_vision\demo_scenes\fat_scene_10_03.json", "r") as f:
    data = json.load(f)

# Read scene image
img = cv2.imread(r"C:\Users\Robo\Desktop\software\pizza_vision\demo_scenes\fat_scene_10_03.png")


# Different colors for different objects for drawing purposes
ketchup_color = (255, 0, 0)
circle_color = (0, 255, 0)
barcode_color = (0, 0, 255)
backstring_color = (255, 255, 255)

# PARAMS
# Threshold for first and third scenario distances
lower_distance_threshold = 140
upper_distance_threshold = 160
# Threshold for X|upside_down rule
acceptance_threshold = 40

# Second scenario offsets
x_offset = 22
y_offset = 85
offset_vector = np.array([x_offset, y_offset]).reshape((1, 2))

# Fourth scenario offsets
# Distance from barcode to back side string
barcode_backside_string_distance_threshold = 100

# Define what data we want

# First scenario, ketchup + circle
ketchup_centers = []
circle_centers = []
ketchup_upside_down = []
ketchup_angles = []
# Second scenario, ketchup lefts without circles
ketchup_without_circle_centers = []


# Third scenario, no 'p' ketchup and rest of circles
no_p_ketchup_centers = []
no_p_ketchup_upside_down = []
circle_centers_left = []
no_p_ketchup_distance_modificators = []

# Fourth scenario, backside, barcode and backstring
barcode_centers = []
backside_string_centers = []

# Iterate over all elements of the scene
for item in data:
    if item["Name"] == "Ketchup":
        # First scenario
        if item["p_visible"] and item["K_visible"]:
            ketchup_centers.append(item["Center"])
            ketchup_upside_down.append(item["Upside_down"])
        # Store all angles for second scenario
            ketchup_angles.append(item["Angle"])
        # Third scenario ketchup part
        elif not item["p_visible"] and item["K_visible"]:
            no_p_ketchup_centers.append(item["Center"])
            no_p_ketchup_upside_down.append(item["Upside_down"])
            no_p_ketchup_distance_modificators.append(item["distance_to_add"])
    if item["Name"] == "Circle":
        circle_centers.append(item["Center"])
    # Backside data
    # Barcodes
    if item["Name"] == "Barcode":
        barcode_centers.append(item["Center"])
    # Back-strings
    if item["Name"] == "Backside String":
        backside_string_centers.append(item["Center"])


# Second scenario ketchups and third scenario circles  depend on former scenarios, and thus can not be
# assigned directly in the first loop

# Check first scenario
first_scenario_grasps = []

# Copy data to erase
ketchup_without_circle_centers = ketchup_centers.copy()
circle_centers_left = circle_centers.copy()
ketchup_without_circle_angles = ketchup_angles.copy()

# Iterate over all pairs
for k, (kc, ud, ka) in enumerate(zip(ketchup_centers, ketchup_upside_down, ketchup_angles)):
    for c, cc in enumerate(circle_centers):
        # Check the X|upside_down rule
        if ud:
            if not (kc[0] < (cc[0] + acceptance_threshold)):
                continue
        else:
            if not (kc[0] > (cc[0] - acceptance_threshold)):
                continue
        # Compute distance
        distance = distance_2d(kc, cc)

        # Check distance rule
        if lower_distance_threshold < distance < upper_distance_threshold:
            # If fulfilled, add tuple of points to the list
            first_scenario_grasps.append((kc, cc))

            # And remove items which should not be analyzed in the next scenarios
            ketchup_without_circle_centers.remove(kc)
            circle_centers_left.remove(cc)
            ketchup_without_circle_angles.remove(ka)
    # TODO: One circle corresponds to one ketchup, but we do not know to which one a priori, and the first
    #  match fulfilling rule might not be good

# Draw first scenario results (BLUE)
first_scenario_draw = img.copy()
for grasp in first_scenario_grasps:
    cv2.line(first_scenario_draw, grasp[0], grasp[1], (255, 0, 0), 2, cv2.LINE_AA)

# Display results
print(f"Grasps found in the first scenario: {len(first_scenario_grasps)}! Press any key to move to the next scenario!")
cv2.imshow("First scenario grasps", first_scenario_draw)
cv2.waitKey(0)

# Second scenario
second_scenario_grasps = []

for kc, ka in zip(ketchup_without_circle_centers, ketchup_without_circle_angles):
    # Build rotation matrix from the rotation angle
    rotation_matrix = np.array([[np.cos(ka), -np.sin(ka)],
                                [np.sin(ka), np.cos(ka)]])
    # Calculate actual offset vector
    actual_offset_vector = offset_vector @ rotation_matrix
    # Move grasp points from the center to desired locations
    grasp_point_one = (int(kc[0] + actual_offset_vector[0][1]), int(kc[1] + actual_offset_vector[0][0]))
    grasp_point_two = (int(kc[0] - actual_offset_vector[0][1]), int(kc[1] - actual_offset_vector[0][0]))
    # Add grasp points to the list
    second_scenario_grasps.append((grasp_point_one, grasp_point_two))

# Draw second scenario results (GREEN)
for grasp in second_scenario_grasps:
    cv2.line(first_scenario_draw, grasp[0], grasp[1], (0, 255, 0), 2, cv2.LINE_AA)

print(f"Grasps found in the second scenario: {len(second_scenario_grasps)}! "
      f"Press any key to move to the next scenario!")
cv2.imshow("Second scenario grasps", first_scenario_draw)
cv2.waitKey(0)

# Third Scenario
third_scenario_grasps = []
for kc, ud, dm in zip(no_p_ketchup_centers, no_p_ketchup_upside_down, no_p_ketchup_distance_modificators):
    for cc in circle_centers_left:
        if ud:
            if not (kc[0] < (cc[0] + acceptance_threshold)):
                continue
        else:
            if not (kc[0] > (cc[0] - acceptance_threshold)):
                continue
        # Compute distance
        distance = distance_2d(kc, cc) + dm
        if lower_distance_threshold < distance < upper_distance_threshold:
            # If fulfilled, add tuple of points to the list
            third_scenario_grasps.append((kc, cc))

# Draw third scenario results (RED)
for grasp in third_scenario_grasps:
    cv2.line(first_scenario_draw, grasp[0], grasp[1], (0, 0, 255), 2, cv2.LINE_AA)
print(f"Grasps found in the third scenario: {len(third_scenario_grasps)}! Press any key to move to the next scenario!")
cv2.imshow("Third scenario grasps", first_scenario_draw)
cv2.waitKey(0)

# Fourth Scenario
fourth_scenario_grasps = []
# Check all pairs barcode + string
for bc in barcode_centers:
    for bsc in backside_string_centers:
        distance = distance_2d(bc, bsc)
        # Check if distance is smaller than the threshold
        if distance < barcode_backside_string_distance_threshold:
            fourth_scenario_grasps.append((bc, bsc))

# Visualize results of the fourth scenario
for grasp in fourth_scenario_grasps:
    cv2.line(first_scenario_draw, grasp[0], grasp[1], (255, 255, 255), 2, cv2.LINE_AA)
print(f"Grasps found in the fourth scenario: {len(fourth_scenario_grasps)}! "
      f"Press any key to move to the next scenario!")
cv2.imshow("Fourth scenario grasps", first_scenario_draw)
cv2.waitKey(0)

cv2.destroyAllWindows()
