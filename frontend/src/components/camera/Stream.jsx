import { useEffect, useRef } from "react";

export default function WebRTCPlayer({ streamUrl }) {
  const videoRef = useRef(null);

  useEffect(() => {
    const pc = new RTCPeerConnection({
      iceServers: [{ urls: "stun:stun.l.google.com:19302" }]
    });

    const stream = new MediaStream();

    videoRef.current.srcObject = stream;

    pc.ontrack = (event) => {
      stream.addTrack(event.track);
    };

    async function start() {
      const offer = await pc.createOffer({
        offerToReceiveVideo: true,
        offerToReceiveAudio: true
      });

      await pc.setLocalDescription(offer);

      const res = await fetch(streamUrl, {
        method: "POST",
        headers: {
          "Content-Type": "application/sdp"
        },
        body: offer.sdp
      });

      const answer = await res.text();

      await pc.setRemoteDescription({
        type: "answer",
        sdp: answer
      });
    }

    start();

    return () => pc.close();
  }, [streamUrl]);

  return (
    <video
      ref={videoRef}
      autoPlay
      playsInline
      controls
      className="w-full h-full"
    />
  );
}