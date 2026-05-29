import { useEffect, useRef, useState } from "react";

import "../styles/camera.css";

function CameraView() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [detection, setDetection] = useState(null);

  // =========================
  // OPEN CAMERA
  // =========================
  useEffect(() => {
    let stream = null;

    async function startCamera() {
      try {
        stream =
          await navigator.mediaDevices.getUserMedia({
            video: {
              width: 640,
              height: 480,
            },
            audio: false,
          });

        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }

        setLoading(false);
      } catch (err) {
        console.error(err);

        setError("Cannot access webcam");

        setLoading(false);
      }
    }

    startCamera();

    return () => {
      if (stream) {
        stream
          .getTracks()
          .forEach((track) => {
            track.stop();
          });
      }
    };
  }, []);

  // =========================
  // LOAD JSON
  // =========================
  useEffect(() => {
    async function loadJson() {
      try {
        const response = await fetch(
          import.meta.env.VITE_HOST
        );

        const json = await response.json();

        setDetection(json);
      } catch (err) {
        console.error(err);
      }
    }

    loadJson();

    const interval = setInterval(() => {
      loadJson();
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  // =========================
  // DRAW DETECTION BOX
  // =========================
  useEffect(() => {
    if (!detection) return;

    const canvas = canvasRef.current;

    if (!canvas) return;

    const ctx = canvas.getContext("2d");

    if (!ctx) return;

    ctx.clearRect(
      0,
      0,
      canvas.width,
      canvas.height
    );

    ctx.strokeStyle = "#22c55e";

    ctx.lineWidth = 4;

    ctx.strokeRect(
      detection.x,
      detection.y,
      detection.width,
      detection.height
    );

    ctx.font = "24px Arial";

    ctx.fillStyle = "#22c55e";

    ctx.fillText(
      detection.label,
      detection.x,
      detection.y - 10
    );
  }, [detection]);

  // =========================
  // LOADING
  // =========================
  if (loading) {
    return (
      <div className="camera-card">
        <h1>Opening Camera...</h1>
      </div>
    );
  }

  // =========================
  // ERROR
  // =========================
  if (error) {
    return (
      <div className="camera-card">
        <h1 style={{ color: "red" }}>
          {error}
        </h1>
      </div>
    );
  }

  // =========================
  // MAIN UI
  // =========================
  return (
    <div className="camera-card">
      <div className="camera-header">
        <h2>📷 Camera / Kết quả</h2>
      </div>

      <div className="camera-wrapper">
        {/* VIDEO */}
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          width={640}
          height={480}
          className="camera-video"
        />

        {/* CANVAS */}
        <canvas
          ref={canvasRef}
          width={640}
          height={480}
          className="camera-canvas"
        />
      </div>
    </div>
  );
}

export default CameraView;  