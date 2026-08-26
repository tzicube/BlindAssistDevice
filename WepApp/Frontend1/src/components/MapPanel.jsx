
// import { useEffect, useRef, useState } from "react";

// export default function MapPanel({ navigation }) {
//   const imgRef = useRef(null);

//   const [markers, setMarkers] = useState([]);
//     useEffect(() => {
//   const savedPlaces =
//     localStorage.getItem("savedPlaces");

//   if (!savedPlaces) {
//     return;
//   }

//   try {
//     const parsedPlaces =
//       JSON.parse(savedPlaces);

//     if (Array.isArray(parsedPlaces)) {
//       setMarkers(parsedPlaces);
//     }
//   } catch (error) {
//     console.error(
//       "Failed to load saved places:",
//       error
//     );
//   }
// }, []);
//   // Marker đang được chọn để đặt tên
//   const [selectedMarker, setSelectedMarker] = useState(null);

//   // Tên địa điểm đang nhập
//   const [markerName, setMarkerName] = useState("");

//   // 4 góc của ảnh map
//   const MAP_CORNER = {
//     topLeft: {
//       lat: 24.991972,
//       lng: 121.339250,
//     },

//     topRight: {
//       lat: 24.992056,
//       lng: 121.348889,
//     },

//     bottomLeft: {
//       lat: 24.983667,
//       lng: 121.338333,
//     },

//     bottomRight: {
//       lat: 24.983639,
//       lng: 121.349361,
//     },
//   };

//   // =========================================================
//   // CLICK MAP
//   // PIXEL → LAT/LNG → MARKER
//   // =========================================================

//   const handleClick = (e) => {
//     const rect =
//       imgRef.current.getBoundingClientRect();

//     const x =
//       e.clientX - rect.left;

//     const y =
//       e.clientY - rect.top;

//     const xPercent =
//       x / rect.width;

//     const yPercent =
//       y / rect.height;

//     const {
//       topLeft,
//       topRight,
//       bottomLeft,
//       bottomRight,
//     } = MAP_CORNER;

//     // ---------- Latitude ----------

//     const latTop =
//       topLeft.lat +
//       xPercent *
//         (topRight.lat - topLeft.lat);

//     const latBottom =
//       bottomLeft.lat +
//       xPercent *
//         (bottomRight.lat - bottomLeft.lat);

//     const lat =
//       latTop +
//       yPercent *
//         (latBottom - latTop);

//     // ---------- Longitude ----------

//     const lngTop =
//       topLeft.lng +
//       xPercent *
//         (topRight.lng - topLeft.lng);

//     const lngBottom =
//       bottomLeft.lng +
//       xPercent *
//         (bottomRight.lng - bottomLeft.lng);

//     const lng =
//       lngTop +
//       yPercent *
//         (lngBottom - lngTop);

//     const newMarker = {
//       id: Date.now(),
//       name: "",
//       xPercent,
//       yPercent,
//       lat,
//       lng,
//     };

//     setMarkers((prev) => [
//       ...prev,
//       newMarker,
//     ]);

//     console.log(
//       "Latitude:",
//       lat.toFixed(6),
//       "Longitude:",
//       lng.toFixed(6)
//     );
//   };

//   // =========================================================
//   // CLICK MARKER
//   // =========================================================

//   const handleMarkerClick = (e, marker) => {
//     // Không để click marker truyền xuống ảnh map
//     e.stopPropagation();

//     setSelectedMarker(marker);
//     setMarkerName(marker.name || "");
//   };

//   // =========================================================
//   // SAVE MARKER
//   // =========================================================

//   const handleSaveMarker = () => {
//     if (!selectedMarker) {
//       return;
//     }

//     const name =
//       markerName.trim();

//     if (!name) {
//       return;
//     }

//     const updatedMarkers =
//       markers.map((marker) =>
//         marker.id === selectedMarker.id
//           ? {
//               ...marker,
//               name,
//             }
//           : marker
//       );

//     setMarkers(updatedMarkers);

//     // Lưu tạm vào localStorage
//     localStorage.setItem(
//       "savedPlaces",
//       JSON.stringify(updatedMarkers)
//     );

//     // Đóng form
//     setSelectedMarker(null);
//     setMarkerName("");

//     console.log(
//       "Saved place:",
//       name
//     );
//   };

//   // =========================================================
//   // CANCEL
//   // =========================================================

//   const handleCancelMarker = () => {
//     setSelectedMarker(null);
//     setMarkerName("");
//   };

//   return (
//     <div className="bg-white rounded shadow p-4 h-full">

//       <h2 className="font-bold text-xl mb-4">
//         Live Location
//       </h2>

//       {/* =====================================================
//           MAP
//       ====================================================== */}

//       <div className="bg-gray-200 rounded overflow-hidden flex justify-center">

//         <div className="relative inline-block">

//           <img
//             ref={imgRef}
//             src="/mock/map1.png"
//             alt="Map"
//             className="max-h-[500px] select-none cursor-crosshair"
//             onClick={handleClick}
//           />

//           {/* =================================================
//               MARKERS
//           ================================================== */}

//           {markers.map((marker) => (
//             <div
//               key={marker.id}
//               className="absolute"
//               style={{
//                 left: `${marker.xPercent * 100}%`,
//                 top: `${marker.yPercent * 100}%`,
//                 transform:
//                   "translate(-50%, -50%)",
//               }}
//               onClick={(e) =>
//                 handleMarkerClick(
//                   e,
//                   marker
//                 )
//               }
//             >
//               <div className="w-4 h-4 rounded-full bg-red-600 border-2 border-white shadow cursor-pointer" />

//               {/* Tên marker nếu đã lưu */}
//               {marker.name && (
//                 <div className="absolute left-1/2 bottom-5 -translate-x-1/2 whitespace-nowrap bg-black text-white text-xs px-2 py-1 rounded">
//                   {marker.name}
//                 </div>
//               )}
//             </div>
//           ))}

//         </div>
//       </div>

//       {/* =====================================================
//           SAVE MARKER FORM
//       ====================================================== */}

//       {selectedMarker && (
//         <div className="mt-4 p-4 border rounded bg-gray-50">

//           <h3 className="font-bold mb-2">
//             Save Place
//           </h3>

//           <p className="text-sm text-gray-500 mb-2">
//             Latitude:{" "}
//             {selectedMarker.lat.toFixed(6)}
//           </p>

//           <p className="text-sm text-gray-500 mb-3">
//             Longitude:{" "}
//             {selectedMarker.lng.toFixed(6)}
//           </p>

//           <input
//             type="text"
//             value={markerName}
//             onChange={(e) =>
//               setMarkerName(e.target.value)
//             }
//             placeholder="Enter place name"
//             className="w-full border rounded px-3 py-2 mb-3"
//           />

//           <div className="flex gap-2">

//             <button
//               onClick={handleSaveMarker}
//               disabled={!markerName.trim()}
//               className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
//             >
//               Save
//             </button>

//             <button
//               onClick={handleCancelMarker}
//               className="bg-gray-300 px-4 py-2 rounded"
//             >
//               Cancel
//             </button>

//           </div>
//         </div>
//       )}

//       {/* =====================================================
//           NAVIGATION INFO
//       ====================================================== */}

//       <div className="grid grid-cols-3 gap-4 mt-4">

//         <div>
//           <p className="text-gray-500">
//             Distance
//           </p>

//           <h3 className="font-bold">
//             {navigation.distance}
//           </h3>
//         </div>

//         <div>
//           <p className="text-gray-500">
//             ETA
//           </p>

//           <h3 className="font-bold">
//             {navigation.eta}
//           </h3>
//         </div>

//         <div>
//           <p className="text-gray-500">
//             Next
//           </p>

//           <h3 className="font-bold">
//             {navigation.nextInstruction}
//           </h3>
//         </div>

//       </div>

//     </div>
//   );
// }
import { useRef, useState } from "react";

export default function MapPanel({
  navigation,
  markers,
  setMarkers,
}) {
  const imgRef = useRef(null);

  // Marker đang được chọn để đặt tên
  const [selectedMarker, setSelectedMarker] =
    useState(null);

  // Tên địa điểm đang nhập
  const [markerName, setMarkerName] =
    useState("");

  // =========================================================
  // 4 GÓC STATIC MAP
  // =========================================================

  const MAP_CORNER = {
    topLeft: {
      lat: 24.991972,
      lng: 121.339250,
    },

    topRight: {
      lat: 24.992056,
      lng: 121.348889,
    },

    bottomLeft: {
      lat: 24.983667,
      lng: 121.338333,
    },

    bottomRight: {
      lat: 24.983639,
      lng: 121.349361,
    },
  };

  // =========================================================
  // CLICK MAP
  // PIXEL → LAT/LNG → MARKER
  // =========================================================

  const handleClick = (e) => {
    if (!imgRef.current) {
      return;
    }

    const rect =
      imgRef.current.getBoundingClientRect();

    const x =
      e.clientX - rect.left;

    const y =
      e.clientY - rect.top;

    const xPercent =
      x / rect.width;

    const yPercent =
      y / rect.height;

    const {
      topLeft,
      topRight,
      bottomLeft,
      bottomRight,
    } = MAP_CORNER;

    // =====================================================
    // LATITUDE
    // =====================================================

    const latTop =
      topLeft.lat +
      xPercent *
        (topRight.lat - topLeft.lat);

    const latBottom =
      bottomLeft.lat +
      xPercent *
        (bottomRight.lat - bottomLeft.lat);

    const lat =
      latTop +
      yPercent *
        (latBottom - latTop);

    // =====================================================
    // LONGITUDE
    // =====================================================

    const lngTop =
      topLeft.lng +
      xPercent *
        (topRight.lng - topLeft.lng);

    const lngBottom =
      bottomLeft.lng +
      xPercent *
        (bottomRight.lng - bottomLeft.lng);

    const lng =
      lngTop +
      yPercent *
        (lngBottom - lngTop);

    // =====================================================
    // CREATE NEW MARKER
    // =====================================================

    const newMarker = {
      id: Date.now(),
      name: "",
      xPercent,
      yPercent,
      lat,
      lng,
    };

    setMarkers((prev) => [
      ...prev,
      newMarker,
    ]);

    console.log(
      "Latitude:",
      lat.toFixed(6),
      "Longitude:",
      lng.toFixed(6)
    );
  };

  // =========================================================
  // CLICK MARKER
  // =========================================================

  const handleMarkerClick = (
    e,
    marker
  ) => {
    // Không để click marker kích hoạt click map
    e.stopPropagation();

    setSelectedMarker(marker);
    setMarkerName(
      marker.name || ""
    );
  };

  // =========================================================
  // SAVE MARKER NAME
  // =========================================================

  const handleSaveMarker = () => {
    if (!selectedMarker) {
      return;
    }

    const name =
      markerName.trim();

    if (!name) {
      return;
    }

    const updatedMarkers =
      markers.map((marker) =>
        marker.id === selectedMarker.id
          ? {
              ...marker,
              name,
            }
          : marker
      );

    // Dashboard là nơi giữ state chung
    setMarkers(updatedMarkers);

    // Đóng form
    setSelectedMarker(null);
    setMarkerName("");

    console.log(
      "Saved place:",
      name
    );
  };

  // =========================================================
  // CANCEL
  // =========================================================

  const handleCancelMarker = () => {
    setSelectedMarker(null);
    setMarkerName("");
  };

  return (
    <div className="bg-white rounded shadow p-4 h-full">

      {/* =====================================================
          TITLE
      ====================================================== */}

      <h2 className="font-bold text-xl mb-4">
        Live Location
      </h2>

      {/* =====================================================
          MAP
      ====================================================== */}

      <div className="bg-gray-200 rounded overflow-hidden flex justify-center">

        <div className="relative inline-block">

          <img
            ref={imgRef}
            src="/mock/map1.png"
            alt="Map"
            className="max-h-[500px] select-none cursor-crosshair"
            onClick={handleClick}
          />

          {/* =================================================
              SAVED MARKERS
          ================================================== */}

          {markers.map((marker) => (
            <div
              key={marker.id}
              className="absolute"
              style={{
                left: `${
                  marker.xPercent * 100
                }%`,

                top: `${
                  marker.yPercent * 100
                }%`,

                transform:
                  "translate(-50%, -50%)",
              }}
              onClick={(e) =>
                handleMarkerClick(
                  e,
                  marker
                )
              }
            >
              {/* Marker */}
              <div className="w-4 h-4 rounded-full bg-red-600 border-2 border-white shadow cursor-pointer" />

              {/* Marker name */}
              {marker.name && (
                <div className="absolute left-1/2 bottom-5 -translate-x-1/2 whitespace-nowrap bg-black text-white text-xs px-2 py-1 rounded">
                  {marker.name}
                </div>
              )}
            </div>
          ))}

        </div>
      </div>

      {/* =====================================================
          SAVE MARKER FORM
      ====================================================== */}

      {selectedMarker && (
        <div className="mt-4 p-4 border rounded bg-gray-50">

          <h3 className="font-bold mb-2">
            Save Place
          </h3>

          <p className="text-sm text-gray-500 mb-2">
            Latitude:{" "}
            {selectedMarker.lat.toFixed(6)}
          </p>

          <p className="text-sm text-gray-500 mb-3">
            Longitude:{" "}
            {selectedMarker.lng.toFixed(6)}
          </p>

          <input
            type="text"
            value={markerName}
            onChange={(e) =>
              setMarkerName(
                e.target.value
              )
            }
            placeholder="Enter place name"
            className="w-full border rounded px-3 py-2 mb-3"
          />

          <div className="flex gap-2">

            {/* SAVE */}
            <button
              onClick={handleSaveMarker}
              disabled={
                !markerName.trim()
              }
              className="bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
            >
              Save
            </button>

            {/* CANCEL */}
            <button
              onClick={
                handleCancelMarker
              }
              className="bg-gray-300 px-4 py-2 rounded"
            >
              Cancel
            </button>

          </div>
        </div>
      )}

      {/* =====================================================
          NAVIGATION INFO
      ====================================================== */}

      <div className="grid grid-cols-3 gap-4 mt-4">

        <div>
          <p className="text-gray-500">
            Distance
          </p>

          <h3 className="font-bold">
            {navigation?.distance ||
              "--"}
          </h3>
        </div>

        <div>
          <p className="text-gray-500">
            ETA
          </p>

          <h3 className="font-bold">
            {navigation?.eta ||
              "--"}
          </h3>
        </div>

        <div>
          <p className="text-gray-500">
            Next
          </p>

          <h3 className="font-bold">
            {navigation?.nextInstruction ||
              "--"}
          </h3>
        </div>

      </div>

    </div>
  );
}