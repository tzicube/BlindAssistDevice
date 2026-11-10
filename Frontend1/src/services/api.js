const PAGE_HOST = window.location.hostname || "localhost";
const API_HOST = ["localhost", "::1", "[::1]"].includes(PAGE_HOST)
  ? "127.0.0.1"
  : PAGE_HOST;
const API_URL =
  import.meta.env.VITE_API_URL ||
  `http://${API_HOST}:8787`;
const GEOCODING_URL =
  import.meta.env.VITE_GEOCODING_URL ||
  "https://nominatim.openstreetmap.org/reverse";
const reverseGeocodeCache = new Map();

async function request(path, options = {}) {
  const response = await fetch(
    `${API_URL}${path}`,
    {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {}),
      },
      ...options,
    }
  );

  if (!response.ok) {
    throw new Error(
      `API Error ${response.status}`
    );
  }

  return response.json();
}

export const api = {
  getDashboardStatus() {
    return request("/api/status");
  },

  getSavedPlaces() {
    return request("/api/places");
  },

  createSavedPlace(place) {
    return request("/api/places", {
      method: "POST",
      body: JSON.stringify(place),
    });
  },

  deleteSavedPlace(placeId) {
    return request(
      `/api/places/${placeId}`,
      {
        method: "DELETE",
      }
    );
  },

  async reverseGeocode(latitude, longitude) {
    const cacheKey = `${Number(latitude).toFixed(5)},${Number(longitude).toFixed(5)}`;
    if (reverseGeocodeCache.has(cacheKey)) {
      return reverseGeocodeCache.get(cacheKey);
    }

    const url = new URL(GEOCODING_URL);
    url.searchParams.set("format", "jsonv2");
    url.searchParams.set("lat", latitude);
    url.searchParams.set("lon", longitude);
    url.searchParams.set("zoom", "18");
    url.searchParams.set("addressdetails", "1");
    url.searchParams.set("accept-language", "zh-TW,zh-Hant,zh,en");

    const response = await fetch(url, {
      headers: { Accept: "application/json" },
    });
    if (!response.ok) {
      throw new Error(`Reverse geocoding failed with status ${response.status}`);
    }

    const result = await response.json();
    const address = String(result.display_name || "").trim();
    if (!address) {
      throw new Error("No address was found for this position");
    }

    reverseGeocodeCache.set(cacheKey, address);
    return address;
  },
};

export default api;
