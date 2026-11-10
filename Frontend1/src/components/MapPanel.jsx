import { useEffect, useMemo, useRef, useState } from "react";
import L from "leaflet";
import {
  CircleMarker,
  MapContainer,
  Marker,
  Popup,
  TileLayer,
  useMapEvents,
} from "react-leaflet";
import {
  LuCrosshair,
  LuLocateFixed,
  LuMaximize2,
  LuMinimize2,
  LuNavigation,
  LuSave,
  LuX,
} from "react-icons/lu";
import api from "../services/api";

const DEFAULT_MAP_CENTER = [24.9878, 121.3438];
const DEFAULT_MAP_ZOOM = 18;

function normalizeHeading(value) {
  if (value === null || value === undefined || value === "") return null;
  const heading = Number(value);
  return Number.isFinite(heading) ? ((heading % 360) + 360) % 360 : null;
}

function createHeadingIcon(heading) {
  const hasHeading = heading !== null;
  const rotation = hasHeading ? heading : 0;
  const arrowColor = hasHeading ? "#ffffff" : "#bfdbfe";

  return L.divIcon({
    className: "",
    iconSize: [48, 48],
    iconAnchor: [24, 24],
    html: `
      <div style="position:relative;width:48px;height:48px;display:grid;place-items:center;">
        <div style="position:absolute;inset:3px;border-radius:999px;background:rgba(37,99,235,.22);animation:pulse 2s cubic-bezier(.4,0,.6,1) infinite;"></div>
        <div style="position:relative;width:38px;height:38px;border:3px solid white;border-radius:999px;background:#2563eb;box-shadow:0 5px 16px rgba(15,23,42,.3);display:grid;place-items:center;">
          <svg viewBox="0 0 24 24" width="25" height="25" aria-hidden="true" style="transform:rotate(${rotation}deg);transition:transform .55s cubic-bezier(.22,1,.36,1);transform-origin:center;">
            <path d="M12 2 L19 21 L12 17 L5 21 Z" fill="${arrowColor}" stroke="#1d4ed8" stroke-width="1" stroke-linejoin="round"></path>
          </svg>
        </div>
      </div>
    `,
  });
}

function normalizeCoordinate(value, minimum, maximum) {
  const coordinate = Number(value);
  return Number.isFinite(coordinate) && coordinate >= minimum && coordinate <= maximum
    ? coordinate
    : null;
}

function getCurrentPosition(location) {
  if (!location) return null;

  const lat = normalizeCoordinate(location.latitude, -90, 90);
  const lng = normalizeCoordinate(location.longitude, -180, 180);
  return lat === null || lng === null ? null : { lat, lng };
}

function MapController({
  currentPosition,
  expanded,
  following,
  onSelectPosition,
  setExpanded,
  setFollowing,
}) {
  const map = useMapEvents({
    click(event) {
      if (!expanded) {
        setExpanded(true);
        return;
      }

      onSelectPosition({
        name: "",
        lat: event.latlng.lat,
        lng: event.latlng.lng,
      });
    },
    dragstart() {
      setFollowing(false);
    },
  });

  const currentLat = currentPosition?.lat;
  const currentLng = currentPosition?.lng;

  useEffect(() => {
    if (!following || currentLat === undefined || currentLng === undefined) return;

    map.setView([currentLat, currentLng], map.getZoom(), {
      animate: true,
    });
  }, [currentLat, currentLng, following, map]);

  useEffect(() => {
    const animationFrame = window.requestAnimationFrame(() => {
      map.invalidateSize({ pan: false });
    });

    return () => window.cancelAnimationFrame(animationFrame);
  }, [expanded, map]);

  return null;
}

export default function MapPanel({
  currentLocation,
  navigation,
  markers,
  setMarkers,
}) {
  const [selectedMarker, setSelectedMarker] = useState(null);
  const [markerName, setMarkerName] = useState("");
  const [markerAddress, setMarkerAddress] = useState("");
  const [addressError, setAddressError] = useState("");
  const [addressLoading, setAddressLoading] = useState(false);
  const [saveError, setSaveError] = useState("");
  const [saving, setSaving] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [following, setFollowing] = useState(true);
  const geocodeTimerRef = useRef(null);
  const geocodeRequestRef = useRef(0);

  const currentPosition = getCurrentPosition(currentLocation);
  const currentHeading = normalizeHeading(
    currentLocation?.heading ?? navigation?.heading,
  );
  const currentHeadingIcon = useMemo(
    () => createHeadingIcon(currentHeading),
    [currentHeading],
  );
  const validMarkers = markers.flatMap((marker) => {
    const lat = normalizeCoordinate(marker.lat ?? marker.latitude, -90, 90);
    const lng = normalizeCoordinate(marker.lng ?? marker.longitude, -180, 180);
    return lat === null || lng === null ? [] : [{ ...marker, lat, lng }];
  });
  const hasNavigation = Boolean(
    navigation?.distance || navigation?.eta || navigation?.nextInstruction,
  );

  useEffect(() => {
    if (!expanded) return undefined;

    const previousOverflow = document.body.style.overflow;
    const handleKeyDown = (event) => {
      if (event.key === "Escape") {
        setExpanded(false);
        setFollowing(true);
      }
    };

    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [expanded]);

  useEffect(
    () => () => {
      window.clearTimeout(geocodeTimerRef.current);
      geocodeRequestRef.current += 1;
    },
    [],
  );

  const handleSelectPosition = (position) => {
    window.clearTimeout(geocodeTimerRef.current);
    const requestId = geocodeRequestRef.current + 1;
    geocodeRequestRef.current = requestId;
    setSelectedMarker(position);
    setMarkerName("");
    setMarkerAddress("");
    setAddressError("");
    setAddressLoading(true);
    setSaveError("");

    geocodeTimerRef.current = window.setTimeout(async () => {
      try {
        const address = await api.reverseGeocode(position.lat, position.lng);
        if (geocodeRequestRef.current === requestId) {
          setMarkerAddress(address);
        }
      } catch (error) {
        console.error("Failed to look up address:", error);
        if (geocodeRequestRef.current === requestId) {
          setAddressError("Address lookup failed. Enter the address manually.");
        }
      } finally {
        if (geocodeRequestRef.current === requestId) {
          setAddressLoading(false);
        }
      }
    }, 1100);
  };

  const handleSaveMarker = async () => {
    const name = markerName.trim();
    const address = markerAddress.trim();
    if (!selectedMarker || !name || !address || addressLoading || saving) return;

    setSaving(true);
    setSaveError("");
    try {
      const savedPlace = await api.createSavedPlace({
        ...selectedMarker,
        name,
        address,
      });
      setMarkers((previous) => [...previous, savedPlace]);
      setSelectedMarker(null);
      setMarkerName("");
      setMarkerAddress("");
    } catch (error) {
      console.error("Failed to save place:", error);
      setSaveError("Could not save this place. Check the backend and try again.");
    } finally {
      setSaving(false);
    }
  };

  const handleCancel = () => {
    window.clearTimeout(geocodeTimerRef.current);
    geocodeRequestRef.current += 1;
    setSelectedMarker(null);
    setMarkerName("");
    setMarkerAddress("");
    setAddressError("");
    setAddressLoading(false);
    setSaveError("");
  };

  const initialCenter = currentPosition
    ? [currentPosition.lat, currentPosition.lng]
    : DEFAULT_MAP_CENTER;

  const sectionClassName = expanded
    ? "panel-card fixed inset-3 z-[1000] flex flex-col overflow-hidden shadow-2xl sm:inset-6"
    : "panel-card h-full overflow-hidden";

  return (
    <>
      {expanded && (
        <button
          type="button"
          className="fixed inset-0 z-[999] cursor-default bg-slate-950/55 backdrop-blur-sm"
          onClick={() => {
            setExpanded(false);
            setFollowing(true);
          }}
          aria-label="Close expanded map"
        />
      )}

      <section className={sectionClassName} aria-labelledby="map-title">
      <div className="flex shrink-0 items-center justify-between gap-3 border-b border-slate-100 px-5 py-4 sm:px-6 2xl:px-7 2xl:py-5">
        <div className="flex items-center gap-3">
          <span className="grid h-10 w-10 place-items-center rounded-2xl bg-emerald-50 text-emerald-700">
            <LuNavigation className="h-5 w-5" aria-hidden="true" />
          </span>
          <div>
            <h2 id="map-title" className="text-lg font-semibold text-slate-950">
              Live location
            </h2>
            <p className="text-sm text-slate-500">
              The map follows the device automatically
            </p>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {expanded && !following && currentPosition && (
            <button
              type="button"
              onClick={() => setFollowing(true)}
              className="inline-flex min-h-9 items-center gap-2 rounded-xl border border-blue-200 bg-blue-50 px-3 text-xs font-semibold text-blue-700 transition hover:bg-blue-100"
              title="Center the map on the device"
            >
              <LuLocateFixed className="h-4 w-4" aria-hidden="true" />
              Recenter
            </button>
          )}
          {/* <span className="hidden rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600 sm:inline-flex">
            {expanded ? "Hold left mouse to drag" : `${markers.length} saved`}
          </span> */}
          {expanded && (
            <button
              type="button"
              onClick={() => {
                setExpanded(false);
                setFollowing(true);
              }}
              className="icon-button"
              aria-label="Minimize map"
              title="Minimize map (Esc)"
            >
              <LuMinimize2 className="h-4 w-4" aria-hidden="true" />
            </button>
          )}
        </div>
      </div>

      <div className={expanded ? "min-h-0 flex-1 overflow-y-auto p-4 sm:p-6" : "p-4 sm:p-6 2xl:p-7"}>
        <div
          className={
            expanded
              ? "relative h-[65vh] min-h-[360px] w-full overflow-hidden rounded-2xl border border-slate-200 bg-slate-100 shadow-inner"
              : "relative aspect-[545/477] w-full overflow-hidden rounded-2xl border border-slate-200 bg-slate-100 shadow-inner"
          }
        >
          <MapContainer
            center={initialCenter}
            zoom={DEFAULT_MAP_ZOOM}
            minZoom={3}
            maxZoom={20}
            dragging
            scrollWheelZoom="center"
            doubleClickZoom="center"
            touchZoom="center"
            boxZoom={false}
            keyboard={false}
            className="h-full w-full"
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />

            <MapController
              currentPosition={currentPosition}
              expanded={expanded}
              following={following}
              onSelectPosition={handleSelectPosition}
              setExpanded={setExpanded}
              setFollowing={setFollowing}
            />

            {validMarkers.map((marker, index) => (
              <CircleMarker
                key={marker.id ?? `${marker.lat}-${marker.lng}-${index}`}
                center={[marker.lat, marker.lng]}
                radius={8}
                pathOptions={{
                  color: "#ffffff",
                  fillColor: "#f43f5e",
                  fillOpacity: 1,
                  opacity: 1,
                  weight: 3,
                }}
                bubblingMouseEvents={false}
              >
                <Popup>
                  <strong>{marker.name}</strong>
                  {marker.address && (
                    <>
                      <br />
                      {marker.address}
                    </>
                  )}
                  <br />
                  {marker.lat.toFixed(6)}, {marker.lng.toFixed(6)}
                </Popup>
              </CircleMarker>
            ))}

            {selectedMarker && (
              <CircleMarker
                center={[selectedMarker.lat, selectedMarker.lng]}
                radius={9}
                pathOptions={{
                  color: "#ffffff",
                  dashArray: "4 3",
                  fillColor: "#2563eb",
                  fillOpacity: 0.9,
                  weight: 3,
                }}
                interactive={false}
              />
            )}

            {currentPosition && (
              <Marker
                position={[currentPosition.lat, currentPosition.lng]}
                icon={currentHeadingIcon}
                interactive={false}
                zIndexOffset={1000}
              />
            )}
          </MapContainer>

          {currentPosition && following && (
            <div
              className="pointer-events-none absolute left-1/2 top-1/2 z-[500] -translate-x-1/2 -translate-y-1/2"
              aria-hidden="true"
            >
              <span className="block h-14 w-14 animate-ping rounded-full bg-blue-500/15" />
            </div>
          )}

          {!expanded && (
            <div className="pointer-events-none absolute right-3 top-3 z-[900] inline-flex items-center gap-2 rounded-xl bg-slate-950/80 px-3 py-2 text-xs font-semibold text-white shadow-lg backdrop-blur">
              <LuMaximize2 className="h-4 w-4" aria-hidden="true" />
              Click to expand
            </div>
          )}

          {!expanded && currentPosition && (
            <button
              type="button"
              onClick={() => setFollowing(true)}
              disabled={following}
              className="absolute bottom-3 right-3 z-[900] inline-flex min-h-10 items-center gap-2 rounded-xl border border-blue-200 bg-white/95 px-3 text-xs font-semibold text-blue-700 shadow-lg backdrop-blur transition hover:bg-blue-50 disabled:cursor-default disabled:border-slate-200 disabled:text-slate-400"
              title={following ? "Map is centered on the device" : "Center the map on the device"}
            >
              <LuLocateFixed className="h-4 w-4" aria-hidden="true" />
              Recenter
            </button>
          )}
        </div>

        <div className="mt-4 flex items-start gap-3 rounded-2xl bg-slate-50 p-4">
          <LuCrosshair className="mt-0.5 h-4 w-4 shrink-0 text-blue-600" aria-hidden="true" />
          <div className="min-w-0 text-sm">
            <p className="font-medium text-slate-800">
              {currentPosition
                ? following
                  ? "Current device position"
                  : "Exploring map — location follow paused"
                : "Waiting for GPS position"}
            </p>
            {currentPosition ? (
              <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-xs text-slate-500">
                <span>{currentPosition.lat.toFixed(6)}, {currentPosition.lng.toFixed(6)}</span>
                <span className="font-sans font-semibold text-blue-700">
                  {currentHeading === null
                    ? "Waiting for heading"
                    : `${currentLocation?.direction || navigation?.direction || ""} ${currentHeading.toFixed(0)}°`.trim()}
                </span>
              </div>
            ) : (
              <p className="mt-0.5 text-xs text-slate-500">
                The map will center itself after the backend receives a location.
              </p>
            )}
          </div>
        </div>

        {selectedMarker && (
          <div className="mt-4 rounded-2xl border border-blue-100 bg-blue-50/70 p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="font-semibold text-slate-900">Save this place</p>
                <p className="mt-1 font-mono text-xs text-slate-500">
                  {selectedMarker.lat.toFixed(6)}, {selectedMarker.lng.toFixed(6)}
                </p>
              </div>
              <button
                type="button"
                onClick={handleCancel}
                className="icon-button"
                aria-label="Cancel saving place"
              >
                <LuX className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>

            <div className="mt-3 flex flex-col gap-2 sm:flex-row">
              <input
                type="text"
                value={markerName}
                onChange={(event) => setMarkerName(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") handleSaveMarker();
                }}
                placeholder="Place name, e.g. Home"
                className="min-w-0 flex-1 rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100"
                autoFocus
              />
              <textarea
                value={markerAddress}
                onChange={(event) => {
                  setMarkerAddress(event.target.value);
                  setAddressError("");
                }}
                placeholder={addressLoading ? "Looking up address…" : "Address"}
                disabled={addressLoading}
                rows={2}
                className="min-w-0 flex-[2] resize-none rounded-xl border border-slate-300 bg-white px-3.5 py-2.5 text-sm text-slate-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-100 disabled:cursor-wait disabled:bg-slate-50"
                aria-label="Place address"
              />
              <button
                type="button"
                onClick={handleSaveMarker}
                disabled={
                  !markerName.trim() ||
                  !markerAddress.trim() ||
                  addressLoading ||
                  saving
                }
                className="primary-button"
              >
                <LuSave className="h-4 w-4" aria-hidden="true" />
                {saving ? "Saving…" : "Save place"}
              </button>
            </div>
            {addressLoading && (
              <p className="mt-2 text-sm text-blue-700">Looking up the street address…</p>
            )}
            {addressError && <p className="mt-2 text-sm text-amber-700">{addressError}</p>}
            {saveError && <p className="mt-2 text-sm text-rose-700">{saveError}</p>}
          </div>
        )}

        {hasNavigation && (
          <div className="mt-4 grid grid-cols-1 gap-3 rounded-2xl border border-slate-200 p-4 sm:grid-cols-3">
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Distance</p>
              <p className="mt-1 font-semibold text-slate-800">{navigation.distance || "—"}</p>
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">ETA</p>
              <p className="mt-1 font-semibold text-slate-800">{navigation.eta || "—"}</p>
            </div>
            <div>
              <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Next</p>
              <p className="mt-1 font-semibold text-slate-800">{navigation.nextInstruction || "—"}</p>
            </div>
          </div>
        )}
      </div>
      </section>
    </>
  );
}
