import { useCallback, useEffect, useRef, useState } from "react";
import { useQueryClient } from '@tanstack/react-query';

export default function useWebSocket(
  { reconnectDelayMs = 1000, maxReconnectDelayMs = 15000, shouldReconnect = true, onMessage } = {}
) {
  const queryClient = useQueryClient();
  const wsRef = useRef(null);
  const timerRef = useRef(null);
  const mountedRef = useRef(false);
  const retryDelayRef = useRef(reconnectDelayMs);
  const onMessageRef = useRef(onMessage);
  const firstMessageRef = useRef(true);

  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  const [readyState, setReadyState] = useState(WebSocket.CLOSED);

  const clearTimer = () => {
    if (timerRef.current) {
      clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  };

  const connect = useCallback(() => {
    clearTimer();
    const existing = wsRef.current;
    if (existing && (existing.readyState === WebSocket.OPEN || existing.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const ws = new WebSocket(`ws://localhost:8000/alert`);
    wsRef.current = ws;
    setReadyState(ws.readyState);

    ws.onopen = () => {
      retryDelayRef.current = reconnectDelayMs;
      setReadyState(WebSocket.OPEN);
    };

    ws.onmessage = (e) => {
      let data = e.data;
      try {
        data = JSON.parse(e.data);
        onMessage(data);

        if (firstMessageRef.current) {
          firstMessageRef.current = false;
        }

        console.log(data);

        if (data?.type === "event") {
          queryClient.setQueryData(['cameras'], (prev) =>
            prev?.map((camera) =>
              String(camera.id) === String(data.event.camera_id)
                ? {
                    ...camera,
                    last_detected_at: data.event.occurred_at ?? new Date().toISOString(),
                  }
                : camera
            )
          );
        } else if (data?.type === "camera") {
          queryClient.setQueryData(['cameras'], (prev) => {
            if (!prev) return prev;
            return prev.map((camera) =>
              String(camera.id) === String(data.event.camera_id)
                ? { ...camera, ...data.camera }
                : camera
            );
          });
        } else if (data?.type === "event_analysis") {
          // Gemini description arrived — update matching event in the events cache
          queryClient.setQueryData(['events'], (prev) => {
            if (!prev) return prev;
            return prev.map((event) =>
              String(event.id) === String(data.event_id)
                ? { ...event, description: data.description }
                : event
            );
          });
        }

      } catch {
        data = null;
      }
    };

    ws.onerror = () => {};

    ws.onclose = (e) => {
      console.log("WS closed:", e.code, e.reason, e.wasClean);
      setReadyState(WebSocket.CLOSED);
      if (!mountedRef.current) return;
      if (!shouldReconnect) return;
      const delay = retryDelayRef.current;
      retryDelayRef.current = Math.min(delay * 1.5, maxReconnectDelayMs);
      timerRef.current = setTimeout(connect, delay);
    };
  }, [reconnectDelayMs, maxReconnectDelayMs, shouldReconnect]);

  useEffect(() => {
    mountedRef.current = true;
    connect();
    return () => {
      mountedRef.current = false;
      clearTimer();
      wsRef.current?.close();
    };
  }, [connect]);

  return ({ isOpen: readyState === WebSocket.OPEN });
}
  }, [connect]);

  return ({isOpen: readyState === WebSocket.OPEN});
}
