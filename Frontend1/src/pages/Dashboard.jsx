import { useEffect, useRef, useState } from "react";
import { LuCircleAlert } from "react-icons/lu";

import CameraPanel from "../components/CameraPanel";
import CautionModal from "../components/CautionModal";
import Header from "../components/Header";
import MapPanel from "../components/MapPanel";
import SavedPlaces from "../components/SavedPlaces";
import api from "../services/api";

const OFFLINE_DASHBOARD = {
  backendOnline: false,
  online: false,
  address: "",
  heading: null,
  direction: null,
  gps: "Waiting for device",
  time: "--:--:--",
  navigation: {},
  detections: [],
  location: null,
};

export default function Dashboard() {
  const [dashboard, setDashboard] = useState(null);
  const [savedPlaces, setSavedPlaces] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeCaution, setActiveCaution] = useState(null);
  const shownCautionId = useRef(null);

  useEffect(() => {
    let active = true;
    let dashboardRequestInFlight = false;

    const loadDashboard = async () => {
      if (dashboardRequestInFlight) return;
      dashboardRequestInFlight = true;
      try {
        const data = await api.getDashboardStatus();
        if (active) {
          setDashboard(data);
          setError("");
          const cautionId = data.caution?.id;
          if (cautionId && cautionId !== shownCautionId.current) {
            shownCautionId.current = cautionId;
            setActiveCaution(data.caution);
          }
        }
      } catch (requestError) {
        console.error(requestError);
        if (active) {
          setDashboard(OFFLINE_DASHBOARD);
          setError("The dashboard cannot reach the backend. Retrying automatically.");
        }
      } finally {
        dashboardRequestInFlight = false;
        if (active) setLoading(false);
      }
    };

    const loadSavedPlaces = async () => {
      try {
        const places = await api.getSavedPlaces();
        if (active) setSavedPlaces(Array.isArray(places) ? places : []);
      } catch (requestError) {
        console.error("Failed to load saved places:", requestError);
        if (active) setSavedPlaces([]);
      }
    };

    const initialLoad = window.setTimeout(() => {
      loadDashboard();
      loadSavedPlaces();
    }, 0);
    const interval = window.setInterval(loadDashboard, 1000);

    return () => {
      active = false;
      window.clearTimeout(initialLoad);
      window.clearInterval(interval);
    };
  }, []);

  const handleDeletePlace = async (placeId) => {
    try {
      await api.deleteSavedPlace(placeId);
      setSavedPlaces((previous) =>
        previous.filter((place) => place.id !== placeId),
      );
    } catch (requestError) {
      console.error("Failed to delete saved place:", requestError);
      setError("Could not delete that place. Please try again.");
    }
  };

  if (loading) {
    return (
      <div className="grid min-h-screen place-items-center bg-slate-50">
        <div className="text-center">
          <span className="mx-auto block h-9 w-9 animate-spin rounded-full border-4 border-blue-100 border-t-blue-600" />
          <p className="mt-4 text-sm font-medium text-slate-600">Preparing your dashboard…</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <Header
        online={dashboard.online}
        backendOnline={dashboard.backendOnline}
        address={dashboard.address}
        heading={dashboard.heading}
        direction={dashboard.direction}
        gps={dashboard.gps}
        time={dashboard.time}
      />

      {activeCaution && (
        <CautionModal
          caution={activeCaution}
          onClose={() => setActiveCaution(null)}
        />
      )}

      <main className="mx-auto w-full max-w-none px-3 py-4 sm:px-4 sm:py-5 lg:px-5 lg:py-6 2xl:px-6">
        {error && (
          <div className="mb-5 flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3.5 text-sm text-rose-800" role="alert">
            <LuCircleAlert className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            <p>{error}</p>
          </div>
        )}

        <div className="grid gap-4 lg:min-h-[calc(100dvh-9rem)] lg:grid-cols-12 lg:items-stretch lg:gap-5 2xl:gap-6">
          <div className="min-w-0 lg:col-span-4">
            <MapPanel
              currentLocation={dashboard.location}
              navigation={dashboard.navigation || {}}
              markers={savedPlaces}
              setMarkers={setSavedPlaces}
            />
          </div>
          <div className="min-w-0 lg:col-span-5">
            <CameraPanel detections={dashboard.detections || []} />
          </div>
          <div className="min-w-0 lg:col-span-3">
            <SavedPlaces places={savedPlaces} onDelete={handleDeletePlace} />
          </div>
        </div>
      </main>
    </div>
  );
}
