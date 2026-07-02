const API_URL =
  import.meta.env.VITE_API_URL || "http://localhost:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    throw new Error(`API Error ${response.status}`);
  }

  return response.json();
}

export const api = {
  getDashboardStatus() {
    return request("/api/status");
  },

  getObjects() {
    return request("/api/objects");
  },

  getSavedPlaces() {
    return request("/api/places");
  },

  startNavigation(destination) {
    return request("/api/navigation/start", {
      method: "POST",
      body: JSON.stringify({
        destination,
      }),
    });
  },
  getCameraFrame() {
  return request("/api/camera");
},
};

export default api;