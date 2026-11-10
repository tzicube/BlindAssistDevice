const WS_HOST = window.location.hostname || "localhost";
const WS_URL =
  import.meta.env.VITE_WS_URL || `ws://${WS_HOST}:8787/ws`;

export function createWebSocket(onMessage) {
  const socket = new WebSocket(WS_URL);

  socket.onopen = () => {
    console.log("WebSocket Connected");
  };

  socket.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      onMessage?.(data);
    } catch (err) {
      console.error(err);
    }
  };

  socket.onerror = (err) => {
    console.error(err);
  };

  socket.onclose = () => {
    console.log("WebSocket Closed");
  };

  return socket;
}
