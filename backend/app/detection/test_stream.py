import cv2

cap = cv2.VideoCapture("rtsp://155.138.128.95:8554/live/phone")

while True:
    ret, frame = cap.read()
    if not ret:
        print("failed")
        break
    print(frame.shape)