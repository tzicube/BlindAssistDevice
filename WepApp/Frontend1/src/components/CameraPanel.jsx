import { useEffect, useState } from "react";

const frames = [
  "/mock/frame1.jpg",
  "/mock/frame2.jpg",
  "/mock/frame3.jpg",
  "/mock/frame4.jpg",
];

export default function CameraPanel({ detections }) {
  const [frameIndex, setFrameIndex] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setFrameIndex((prev) => (prev + 1) % frames.length);
    }, 100);

    return () => clearInterval(timer);
  }, []);

  return (
    <div className="bg-white rounded shadow p-4 h-full">

      <h2 className="font-bold text-xl mb-4">
        Live Camera / YOLO Detection
      </h2>

      <div className="bg-black h-96 rounded overflow-hidden">

        <img
          src={frames[frameIndex]}
          alt="Camera"
          className="w-full h-full object-cover"
        />

      </div>

      <div className="bg-red-100 border border-red-400 rounded p-3 mt-4">
        ⚠ Obstacle detected
      </div>

      <div className="flex gap-2 mt-4 flex-wrap">
        {detections.map((item) => (
          <div
            key={item.id}
            className="bg-blue-100 px-3 py-1 rounded"
          >
            {item.label}
          </div>
        ))}
      </div>

    </div>
  );
}