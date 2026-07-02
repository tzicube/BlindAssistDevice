import { useEffect, useState } from "react";

import Header from "../components/Header";
import MapPanel from "../components/MapPanel";
import CameraPanel from "../components/CameraPanel";
import SavedPlaces from "../components/SavedPlaces";
import StatusBar from "../components/StatusBar";

import api from "../services/api";

export default function Dashboard() {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadDashboard = async () => {
  try {
    setError("");

    const data = await api.getDashboardStatus();

    setDashboard(data);
  } catch (err) {
    console.error(err);

    setError("Unable to connect backend.");

    setDashboard({
      battery: 95,
      online: false,
      gps: "Unavailable",
      signal: "Disconnected",
      time: new Date().toLocaleTimeString(),
      navigation: {},
      detections: [],
      places: [],
      systemStatus: "Offline",
    });
  } finally {
    setLoading(false);
  }
};

  useEffect(() => {
    loadDashboard();

    const interval = setInterval(loadDashboard, 1000);

    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        Loading...
      </div>
    );
  }

  {error && (
    <div className="bg-red-100 text-red-600 p-2 text-center">
      {error}
    </div>
  )}
    return (
    <div className="min-h-screen bg-gray-100">
      <Header
        battery={dashboard.battery}
        online={dashboard.online}
        gps={dashboard.gps}
        signal={dashboard.signal}
        time={dashboard.time}
      />

      <div className="grid grid-cols-12 gap-4 p-4">
        <div className="col-span-4">
          <MapPanel navigation={dashboard.navigation} />
        </div>

        <div className="col-span-5">
          <CameraPanel detections={dashboard.detections} />
        </div>

        <div className="col-span-3">
          <SavedPlaces places={dashboard.places} />
        </div>
      </div>

      <StatusBar
        lastUpdate={dashboard.time}
        gps={dashboard.gps}
        signal={dashboard.signal}
        navigation={dashboard.navigation}
        systemStatus={dashboard.systemStatus}
      />
    </div>
  );
}