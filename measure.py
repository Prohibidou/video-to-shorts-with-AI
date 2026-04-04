import cv2

# Load image
img = cv2.imread("frame_3400.jpg")

# The video player is a large mainly black rectangle.
# Let's crop x=0 to x=860? Let's check
# we can just write out a few crops
crop1 = img[140:710, 0:1015] # y_start:y_end, x_start:x_end
cv2.imwrite("test_crop.jpg", crop1)
