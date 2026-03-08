import { useEffect, useRef } from "react";

export default function Stream() {
  const videoRef = useRef(null);
  const pcRef = useRef(null);

  useEffect(() => {
    let stopped = false;

    async function start() {
      const pc = new RTCPeerConnection();
      pcRef.current = pc;

      pc.addTransceiver("video", { direction: "recvonly" });
      pc.addTransceiver("audio", { direction: "recvonly" });

      pc.ontrack = (event) => {
        if (!videoRef.current) return;
        videoRef.current.srcObject = event.streams[0];
      };

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      const res = await fetch("http://155.138.128.95:8889/live/phone/whep", {
        method: "POST",
        headers: {
          "Content-Type": "application/sdp",
        },
        body: offer.sdp,
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`WHEP POST failed: ${res.status} ${text}`);
      }

      const answerSdp = await res.text();

      if (stopped) return;

      await pc.setRemoteDescription({
        type: "answer",
        sdp: answerSdp,
      });
    }

    start().catch((err) => {
      console.error("Failed to start stream:", err);
    });

    return () => {
      stopped = true;
      if (pcRef.current) {
        pcRef.current.close();
        pcRef.current = null;
      }
    };
  }, []);

  return (
    <video
      ref={videoRef}
      autoPlay
      playsInline
      muted
      className="w-full h-full object-cover rounded-xl bg-black"
    />
  );
}