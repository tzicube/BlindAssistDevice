import { useEffect, useState } from "react";
import {
  LuCamera,
  LuRadio,
  LuScanLine,
  LuTriangleAlert,
} from "react-icons/lu";

const CAMERA_HOST = window.location.hostname || "localhost";
const API_BASE =
  import.meta.env.VITE_CAMERA_URL ||
  `http://${CAMERA_HOST}:8787`;
const CAMERA_FPS = Math.max(
  1,
  Number.parseInt(import.meta.env.VITE_CAMERA_FPS || "30", 30) || 30,
);
const CAMERA_FRAME_INTERVAL_MS = 1000 / CAMERA_FPS;

const MOCK_FRAMES = [
  "/mock/frame1.jpg",
  "/mock/frame2.jpg",
  "/mock/frame3.jpg",
  "/mock/frame4.jpg",
];

const CAMERA_STATUS = {
  live: {
    label: "Live feed",
    message: "Living frames from the ESP32 camera",
    dot: "bg-emerald-400",
  },
  waiting: {
    label: "Waiting for camera",
    message: "Server connected; no ESP32 frame has arrived yet",
    dot: "bg-amber-400",
  },
  checking: {
    label: "Connecting",
    message: "Checking the camera server",
    dot: "bg-blue-400",
  },
  fallback: {
    label: "Preview mode",
    message: "Camera server is offline; showing sample frames",
    dot: "bg-slate-400",
  },
};

export default function CameraPanel({ detections }) {
  const [imageUrl, setImageUrl] = useState(MOCK_FRAMES[0]);
  const [cameraState, setCameraState] = useState("checking");

  useEffect(() => {
    let cancelled = false;
    let timer;
    let frameIndex = 0;
    let objectUrl;

    const showMockFrame = (state) => {
      setImageUrl(MOCK_FRAMES[frameIndex % MOCK_FRAMES.length]);
      setCameraState(state);
      frameIndex += 1;
      timer = window.setTimeout(loadFrame, 3500);
    };

    const loadFrame = async () => {
      const frameStartedAt = performance.now();
      try {
        const response = await fetch(
          `${API_BASE}/api/image?t=${Date.now()}`,
          { cache: "no-store" },
        );

        if (!response.ok) {
          if (response.status === 404) {
            if (!cancelled) showMockFrame("waiting");
            return;
          }
          throw new Error(`Camera API returned ${response.status}`);
        }

        const nextObjectUrl = URL.createObjectURL(await response.blob());
        if (cancelled) {
          URL.revokeObjectURL(nextObjectUrl);
          return;
        }

        if (objectUrl) URL.revokeObjectURL(objectUrl);
        objectUrl = nextObjectUrl;
        setImageUrl(objectUrl);
        setCameraState("live");
        const elapsed = performance.now() - frameStartedAt;
        timer = window.setTimeout(
          loadFrame,
          Math.max(0, CAMERA_FRAME_INTERVAL_MS - elapsed),
        );
      } catch {
        if (cancelled) return;
        if (objectUrl) {
          URL.revokeObjectURL(objectUrl);
          objectUrl = undefined;
        }
        showMockFrame("fallback");
      }
    };

    loadFrame();

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, []);

  const status = CAMERA_STATUS[cameraState];
  const detectionList = Array.isArray(detections) ? detections : [];

  return (
    <section className="panel-card h-full overflow-hidden" aria-labelledby="camera-title">
      <div className="flex flex-col gap-3 border-b border-slate-100 px-5 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6 2xl:px-7 2xl:py-5">
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-2xl bg-blue-50 text-blue-600">
            <LuCamera className="h-5 w-5" aria-hidden="true" />
          </span>
          <div>
            <h2 id="camera-title" className="text-lg font-semibold text-slate-950">
              Camera view
            </h2>
            <p className="text-sm text-slate-500">ESP32 frame and object detection</p>
          </div>
        </div>

        <div className="flex items-center gap-2 rounded-full bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-700" aria-live="polite">
          <span className={`h-2 w-2 rounded-full ${status.dot}`} />
          {status.label}
        </div>
      </div>

      <div className="p-4 sm:p-6 2xl:p-7">
        <figure className="relative mx-auto aspect-[4/3] w-full overflow-hidden rounded-2xl bg-slate-950 shadow-inner">
          <img
            src={imageUrl}
            alt="Latest camera frame"
            className="h-full w-full select-none object-contain"
            draggable={false}
          />
          <figcaption className="absolute inset-x-0 bottom-0 flex items-end justify-between bg-gradient-to-t from-slate-950/80 via-slate-950/20 to-transparent px-4 pb-3 pt-12 text-xs text-white/90">
            <span className="flex items-center gap-1.5">
              <LuRadio className="h-3.5 w-3.5" aria-hidden="true" />
              {status.message}
            </span>
            <span className="rounded-full bg-black/35 px-2.5 py-1 font-medium tabular-nums backdrop-blur">
              320 × 240 · 4:3 · {CAMERA_FPS} FPS
            </span>
          </figcaption>
        </figure>

        <div className="mt-4">
        </div>
      </div>
    </section>
  );
}
