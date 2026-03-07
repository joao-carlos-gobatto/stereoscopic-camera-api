import cv2
import numpy as np
import matplotlib.pyplot as plt

def show(img, gray=False):
    plt.figure(figsize=(6,6))
    if gray:
        plt.imshow(img, cmap='gray')
    else:
        plt.imshow(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    plt.axis("off")
    plt.show()

stereoRectificationMap = "stereoMap.xml"
cv_file = cv2.FileStorage()
cv_file.open(stereoRectificationMap, cv2.FileStorage_READ)
Q = cv_file.getNode('q_matrix').mat()
stereoMapL_x = cv_file.getNode('stereoMapL_x').mat()
stereoMapL_y = cv_file.getNode('stereoMapL_y').mat()
stereoMapR_x = cv_file.getNode('stereoMapR_x').mat()
stereoMapR_y = cv_file.getNode('stereoMapR_y').mat()

print("Map Lx:", stereoMapL_x.dtype)
print("Map Ly:", stereoMapL_y.dtype)
print("Map Rx:", stereoMapR_x.dtype)
print("Map Ry:", stereoMapR_y.dtype)

imgL = cv2.imread("test_images/left/measured.jpg")
imgR = cv2.imread("test_images/right/measured.jpg")
grayL = cv2.cvtColor(imgL, cv2.COLOR_BGR2GRAY)
grayR = cv2.cvtColor(imgR, cv2.COLOR_BGR2GRAY)

height, width = grayL.shape
print(f"Original shape: {height}x{width}")

# Remap as before
rect_grayL = cv2.remap(grayL, stereoMapL_x, stereoMapL_y, cv2.INTER_LANCZOS4, cv2.BORDER_CONSTANT, 0)
rect_grayR = cv2.remap(grayR, stereoMapR_x, stereoMapR_y, cv2.INTER_LANCZOS4, cv2.BORDER_CONSTANT, 0)

# Compute validity masks based on map coordinates (valid if within original image bounds)
maskL = (stereoMapL_x >= 0) & (stereoMapL_x < width) & (stereoMapL_y >= 0) & (stereoMapL_y < height)
maskR = (stereoMapR_x >= 0) & (stereoMapR_x < width) & (stereoMapR_y >= 0) & (stereoMapR_y < height)

# Function to get bounding box ROI from mask
def get_bounding_box(mask):
    rows, cols = np.where(mask)
    if len(rows) == 0:
        return 0, 0, 0, 0
    min_y = np.min(rows)
    max_y = np.max(rows)
    min_x = np.min(cols)
    max_x = np.max(cols)
    return min_x, min_y, max_x - min_x + 1, max_y - min_y + 1

roiL = get_bounding_box(maskL)
roiR = get_bounding_box(maskR)

# Compute common ROI (intersection)
crop_x = max(roiL[0], roiR[0])
crop_y = max(roiL[1], roiR[1])
crop_w = min(roiL[0] + roiL[2], roiR[0] + roiR[2]) - crop_x
crop_h = min(roiL[1] + roiL[3], roiR[1] + roiR[3]) - crop_y

print(f"Common ROI: x={crop_x}, y={crop_y}, w={crop_w}, h={crop_h}")

if crop_w > 0 and crop_h > 0:
    rect_grayL = rect_grayL[crop_y:crop_y + crop_h, crop_x:crop_x + crop_w]
    rect_grayR = rect_grayR[crop_y:crop_y + crop_h, crop_x:crop_x + crop_w]
else:
    print("No valid common ROI found. Check calibration.")
    # Fallback to original if no ROI

print(rect_grayL.shape)
print(rect_grayR.shape)
print(rect_grayL.dtype, rect_grayL.shape)
print(rect_grayR.dtype, rect_grayR.shape)

combined = np.hstack((rect_grayL, rect_grayR))
for i in range(0, combined.shape[0], 40):
    cv2.line(combined, (0, i), (combined.shape[1], i), 255, 1)
show(combined, gray=True)

# Adjust Q for the crop (shift principal points)
cx = -Q[0, 3]
cy = -Q[1, 3]
Q[0, 3] = - (cx - crop_x)
Q[1, 3] = - (cy - crop_y)
# No need to adjust cx' diff, as crop is the same for both

stereo = cv2.StereoSGBM_create(
    minDisparity=0,
    numDisparities=16*4,  # 64; increase to 128 or 256 if close objects (high disparities)
    blockSize=7,
    P1=8*1*7**2,
    P2=32*1*7**2,
    uniquenessRatio=5,
    speckleWindowSize=50,
    speckleRange=1
)

disparity = stereo.compute(rect_grayL, rect_grayR).astype(np.float32) / 16.0
print("min:", np.min(disparity))
print("max:", np.max(disparity))

# Optional: Mask invalid disparities for better vis (set to 0 or NaN)
disparity[disparity <= 0] = np.nan  # Or 0 for black

disp_vis = cv2.normalize(disparity, None, 0, 255, cv2.NORM_MINMAX)
disp_vis = np.nan_to_num(disp_vis).astype(np.uint8)  # Handle NaNs
show(disp_vis, gray=True)

# To generate point cloud (your goal)
points3d = cv2.reprojectImageTo3D(disparity, Q)
# Filter invalid points (e.g., where disparity <= 0 or points3d[:,:,2] == inf)
valid = (disparity > 0) & np.isfinite(points3d[:,:,2])
points3d_valid = points3d[valid]
# Now points3d_valid is your point cloud (Nx3 array); save to PLY or visualize with matplotlib/PCL