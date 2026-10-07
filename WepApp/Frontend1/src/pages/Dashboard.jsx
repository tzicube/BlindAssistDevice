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

   
  
  const [savedPlaces, setSavedPlaces] =
  useState([]);
  
  const loadSavedPlaces = async () => {
  try {
    const places =
      await api.getSavedPlaces();

    setSavedPlaces(
      Array.isArray(places)
        ? places
        : []
    );
  } catch (err) {
    console.error(
      "Failed to load saved places:",
      err
    );

    setSavedPlaces([]);
  }
  };
  
  useEffect(() => {
  loadDashboard();
  loadSavedPlaces();

  const interval = setInterval(
    loadDashboard,
    1000
  );

  return () =>
    clearInterval(interval);
  }, []);
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

  const handleDeletePlace = async (placeId) => {
  try {
    await api.deleteSavedPlace(placeId);

    setSavedPlaces((prev) =>
      prev.filter(
        (place) => place.id !== placeId
      )
    );
  } catch (err) {
    console.error(
      "Failed to delete saved place:",
      err
    );
  }
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
