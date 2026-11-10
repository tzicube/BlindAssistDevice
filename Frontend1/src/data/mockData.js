export const dashboardData = {
  online: true,

  battery: 82,

  location: {
    current: {
      lat: 25.033,
      lng: 121.5654,
    },

    destination: {
      name: "Home",
      lat: 25.04,
      lng: 121.57,
    },
  },

  navigation: {
    distance: "1.2 km",
    eta: "18 min",
    nextInstruction: "Go straight 120m",
  },

  places: [
    {
      id: 1,
      name: "Home",
      address: "123 Main St",
    },

    {
      id: 2,
      name: "School",
      address: "MCU",
    },

    {
      id: 3,
      name: "Hospital",
      address: "City Hospital",
    },
  ],

  detections: [
    {
      id: 1,
      label: "Person",
      confidence: 0.95,
    },

    {
      id: 2,
      label: "Obstacle",
      confidence: 0.89,
    },
  ],
};