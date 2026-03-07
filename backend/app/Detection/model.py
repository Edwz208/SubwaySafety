from ultralytics import YOLO
_model = None
def get_model() -> YOLO:
  """
  Returns a singleton YOLOv8-Pose model instance.
  Loads once on first call, reuses on every subsequent call.
  """
  global _model
  if _model is None:
    _model = YOLO("yolov8n-pose.pt")
  return _model 