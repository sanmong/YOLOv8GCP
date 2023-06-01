import cv2
import asyncio
import numpy as np
import supervision as sv
from aiohttp import web
from av import VideoFrame
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from aiortc.contrib.media import MediaPlayer
from ultralytics import YOLO  


box_annotator = sv.BoxAnnotator(thickness=2, text_thickness=2, text_scale=1)

class YOLOTrack(VideoStreamTrack):
    def __init__(self, track):
        super().__init__() 
        self.track = track
        self.yolo_model = YOLO(weights="best.pt", device="gpu")
        
    async def recv(self):
        frame = await self.track.recv()

        img = frame.to_ndarray(format="bgr24")

        result = self.yolo_model(img, agnostic_nms=True)[0]

        detections = sv.Detections.from_yolov8(result)

        labels = [f"{self.yolo_model.model.names[class_id]} {confidence:0.2f}" for _, _, confidence, class_id, _ in detections]
        print(labels)

        # Annotate the image using box_annotator. Please replace it with your implementation if different.
        img = box_annotator.annotate(scene=img, detections=detections, labels=labels)

        # Convert back the image to VideoFrame
        new_frame = VideoFrame.from_ndarray(img, format="bgr24")
        new_frame.pts = frame.pts
        new_frame.time_base = frame.time_base

        return new_frame


async def index(request):
    content = open("index.html", "r").read()
    return web.Response(content_type="text/html", text=content)

pcs = set()

async def offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])

    pc = RTCPeerConnection()
    pcs.add(pc)

    @pc.on("iceconnectionstatechange")
    async def on_iceconnectionstatechange():
        if pc.iceConnectionState == "failed":
            await pc.close()
            pcs.discard(pc)

    await pc.setRemoteDescription(offer)
    for t in pc.getTransceivers():
        if t.receiver.track.kind == "video":
            pc.addTrack(YOLOTrack(t.receiver.track))

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)

    return web.json_response(
        {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
    )

app = web.Application()
app.router.add_get("/", index)
app.router.add_post("/offer", offer)

web.run_app(app, access_log=None, port=8080, ssl_context=None)
