import { useEffect, useState } from "react";

import Header from "../components/Header";
import MapPanel from "../components/MapPanel";
import CameraPanel from "../components/CameraPanel";
import SavedPlaces from "../components/SavedPlaces";

import api from "../services/api";

export default function Dashboard() {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  // =========================================================
  // SAVED PLACES - SINGLE SOURCE OF TRUTH
  // =========================================================

  const [savedPlaces, setSavedPlaces] = useState(() => {
    const saved = localStorage.getItem("savedPlaces");

    if (!saved) {
      return [];
    }

    try {
      const parsed = JSON.parse(saved);

      return Array.isArray(parsed)
        ? parsed
        : [];
    } catch (err) {
      console.error(
        "Failed to load saved places:",
        err
      );

      return [];
    }
  });

  // =========================================================
  // SAVE SAVED PLACES TO LOCALSTORAGE
  // =========================================================

  useEffect(() => {
    localStorage.setItem(
      "savedPlaces",
      JSON.stringify(savedPlaces)
    );
  }, [savedPlaces]);

  // =========================================================
  // LOAD DASHBOARD
  // =========================================================

  const loadDashboard = async () => {
    try {
      setError("");

      const data =
        await api.getDashboardStatus();

      setDashboard(data);
    } catch (err) {
      console.error(err);

      setError(
        "Unable to connect backend."
      );

      setDashboard({
        battery: 95,
        online: false,
        gps: "Unavailable",
        signal: "Disconnected",
        time: new Date().toLocaleTimeString(),
        navigation: {},
        detections: [],
        systemStatus: "Offline",
      });
    } finally {
      setLoading(false);
    }
  };

  // =========================================================
  // LOAD BACKEND STATUS
  // =========================================================

  useEffect(() => {
    loadDashboard();

    const interval = setInterval(
      loadDashboard,
      1000
    );

    return () =>
      clearInterval(interval);
  }, []);

  // =========================================================
  // LOADING
  // =========================================================

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        Loading...
      </div>
    );
  }

  // =========================================================
  // DELETE SAVED PLACE
  // =========================================================

  const handleDeletePlace = (placeId) => {
    setSavedPlaces((prev) =>
      prev.filter(
        (place) => place.id !== placeId
      )
    );
  };

  // =========================================================
  // DASHBOARD
  // =========================================================

  return (
    <>
      <div className="min-h-screen bg-white">

        {/* =================================================
            HEADER
        ================================================== */}

        <Header
          battery={dashboard.battery}
          online={dashboard.online}
          gps={dashboard.gps}
          signal={dashboard.signal}
          time={dashboard.time}
        />

        <div className="grid grid-cols-12 gap-4 p-4">

          {/* =================================================
              MAP
          ================================================== */}

          <div className="col-span-4">
            <MapPanel
              navigation={
                dashboard.navigation || {}
              }
              markers={savedPlaces}
              setMarkers={setSavedPlaces}
            />
          </div>

          {/* =================================================
              CAMERA
          ================================================== */}

          <div className="col-span-5">
            <CameraPanel
              detections={
                dashboard.detections || []
              }
            />
          </div>

          {/* =================================================
              SAVED PLACES
          ================================================== */}

          <div className="col-span-3">
            <SavedPlaces
              places={savedPlaces}
              onDelete={handleDeletePlace}
            />
          </div>

        </div>

      </div>
    </>
  );
}

// import { useEffect, useState } from "react";

// import Header from "../components/Header";
// import MapPanel from "../components/MapPanel";
// import CameraPanel from "../components/CameraPanel";
// import SavedPlaces from "../components/SavedPlaces";
// // import StatusBar from "../components/StatusBar";

// import api from "../services/api";

// export default function Dashboard() {
//   const [dashboard, setDashboard] = useState(null);
//   const [loading, setLoading] = useState(true);
//   const [error, setError] = useState("");

//   // =========================================================
//   // SAVED PLACES - SINGLE SOURCE OF TRUTH
//   // =========================================================

//   const [savedPlaces, setSavedPlaces] = useState(() => {
//     const saved = localStorage.getItem("savedPlaces");

//     if (!saved) {
//       return [];
//     }

//     try {
//       const parsed = JSON.parse(saved);

//       return Array.isArray(parsed)
//         ? parsed
//         : [];
//     } catch (err) {
//       console.error(
//         "Failed to load saved places:",
//         err
//       );

//       return [];
//     }
//   });

//   // =========================================================
//   // SAVE SAVED PLACES TO LOCALSTORAGE
//   // =========================================================

//   useEffect(() => {
//     localStorage.setItem(
//       "savedPlaces",
//       JSON.stringify(savedPlaces)
//     );
//   }, [savedPlaces]);

//   // =========================================================
//   // LOAD DASHBOARD
//   // =========================================================

//   const loadDashboard = async () => {
//     try {
//       setError("");

//       const data =
//         await api.getDashboardStatus();

//       setDashboard(data);
//     } catch (err) {
//       console.error(err);

//       setError(
//         "Unable to connect backend."
//       );

//       setDashboard({
//         battery: 95,
//         online: false,
//         gps: "Unavailable",
//         signal: "Disconnected",
//         time: new Date().toLocaleTimeString(),
//         navigation: {},
//         detections: [],
//         systemStatus: "Offline",
//       });
//     } finally {
//       setLoading(false);
//     }
//   };

//   // =========================================================
//   // LOAD BACKEND STATUS
//   // =========================================================

//   useEffect(() => {
//     loadDashboard();

//     const interval = setInterval(
//       loadDashboard,
//       1000
//     );

//     return () =>
//       clearInterval(interval);
//   }, []);

//   // =========================================================
//   // LOADING
//   // =========================================================

//   if (loading) {
//     return (
//       <div className="min-h-screen flex items-center justify-center">
//         Loading...
//       </div>
//     );
//   }

//   // =========================================================
//   // DASHBOARD
//   // =========================================================
//   const handleDeletePlace = (placeId) => {
//   setSavedPlaces((prev) =>
//     prev.filter((place) => place.id !== placeId)
//   );
// };
//   return (
//     <>
//       {/* Backend error notification is temporarily hidden */}

//       {/* <div className="min-h-screen bg-gray-100"> */}
//         <div className="min-h-screen bg-white">
//         {/* =================================================
//             HEADER
//         ================================================== */}

//         <Header
//           battery={dashboard.battery}
//           online={dashboard.online}
//           gps={dashboard.gps}
//           signal={dashboard.signal}
//           time={dashboard.time}
//         />

//         <div className="grid grid-cols-12 gap-4 p-4">

//           {/* =================================================
//               MAP
//           ================================================== */}

//           <div className="col-span-4">
//             <MapPanel
//               navigation={
//                 dashboard.navigation || {}
//               }
//               markers={savedPlaces}
//               setMarkers={setSavedPlaces}
//             />
//           </div>

//           {/* =================================================
//               CAMERA
//           ================================================== */}

//           <div className="col-span-5">
//             <CameraPanel
//               detections={
//                 dashboard.detections || []
//               }
//             />
//           </div>

//           {/* =================================================
//               SAVED PLACES
//           ================================================== */}

//           <div className="col-span-3">
//             <SavedPlaces
//               places={savedPlaces}
//               onDelete={handleDeletePlace}
//             />
//           </div>

//         </div>

//         {/* =================================================
//             STATUS BAR
//         ================================================== */}

//         <StatusBar
//           lastUpdate={dashboard.time}
//           gps={dashboard.gps}
//           signal={dashboard.signal}
//           navigation={
//             dashboard.navigation || {}
//           }
//           systemStatus={
//             dashboard.systemStatus
//           }
//         />

//       </div>
//     </>
//   );
// }