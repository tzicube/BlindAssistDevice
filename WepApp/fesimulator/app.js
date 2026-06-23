const DEFAULT_SERVER_BASE_URL = "http://localhost:8765";
const DEFAULT_IMAGE_PATH = "/api/image";
const POLL_INTERVAL_MS = 100;

const elements = {
  serverBaseUrl: document.getElementById("serverBaseUrl"),
  imagePath: document.getElementById("imagePath"),
  previewShell: document.getElementById("previewShell"),
  previewOverlay: document.getElementById("previewOverlay"),
  liveImage: document.getElementById("liveImage"),
  viewerStatus: document.getElementById("viewerStatus"),
  imageMeta: document.getElementById("imageMeta"),
  frameCount: document.getElementById("frameCount"),
  lastUpdate: document.getElementById("lastUpdate"),
  activityLog: document.getElementById("activityLog"),
};

let isPolling = true;
let nextPollTimer = null;
let currentImageUrl = null;
let receivedFrameCount = 0;
let lastLoggedError = "";
let pollInFlight = false;
let hasSuccessfulFrame = false;

elements.serverBaseUrl.value = DEFAULT_SERVER_BASE_URL;
elements.imagePath.value = DEFAULT_IMAGE_PATH;

function nowLabel() {
  return new Date().toLocaleTimeString("vi-VN", { hour12: false });
}

function logActivity(message, level = "info") {
  const line = `[${nowLabel()}] [${level.toUpperCase()}] ${message}`;
  const entry = document.createElement("div");
  entry.className = `log-line log-${level}`;
  entry.textContent = line;

  elements.activityLog.prepend(entry);
  while (elements.activityLog.childElementCount > 120) {
    elements.activityLog.removeChild(elements.activityLog.lastChild);
  }

  console[level === "error" ? "error" : "log"](line);
}

function setStatus(message, tone = "idle") {
  elements.viewerStatus.textContent = message;
  elements.viewerStatus.dataset.tone = tone;
}

function buildEndpoint(baseUrl, path) {
  const trimmedBase = baseUrl.trim().replace(/\/+$/, "");
  const normalizedPath = path.trim().startsWith("/")
    ? path.trim()
    : `/${path.trim()}`;

  if (!trimmedBase) {
    throw new Error("Server base URL khong duoc de trong");
  }

  return `${trimmedBase}${normalizedPath}`;
}

function formatBytes(byteCount) {
  if (byteCount < 1024) {
    return `${byteCount} B`;
  }

  if (byteCount < 1024 * 1024) {
    return `${(byteCount / 1024).toFixed(1)} KB`;
  }

  return `${(byteCount / (1024 * 1024)).toFixed(2)} MB`;
}

function updateLastUpdateLabel(date = new Date()) {
  elements.lastUpdate.textContent = date.toLocaleTimeString("vi-VN", {
    hour12: false,
  });
}

function updatePreviewState(isLive, overlayText = "") {
  elements.previewShell.dataset.live = isLive ? "true" : "false";
  if (overlayText) {
    elements.previewOverlay.textContent = overlayText;
  }
}

function revokeCurrentImageUrl() {
  if (currentImageUrl) {
    URL.revokeObjectURL(currentImageUrl);
    currentImageUrl = null;
  }
}

function scheduleNextPoll(pollStartedAt = performance.now()) {
  if (!isPolling) {
    return;
  }

  const elapsedMs = performance.now() - pollStartedAt;
  const nextDelayMs = Math.max(0, POLL_INTERVAL_MS - elapsedMs);
  nextPollTimer = window.setTimeout(pollLatestImage, nextDelayMs);
}

async function pollLatestImage() {
  if (pollInFlight || !isPolling) {
    return;
  }

  pollInFlight = true;
  nextPollTimer = null;
  const pollStartedAt = performance.now();
  const endpoint = buildEndpoint(
    elements.serverBaseUrl.value,
    elements.imagePath.value
  );

  setStatus("Dang lay frame moi nhat tu server...", "busy");

  try {
    const response = await fetch(endpoint, {
      method: "GET",
      cache: "no-store",
      headers: {
        Accept: "image/jpeg",
      },
    });

    if (response.status === 404) {
      updatePreviewState(false, "Dang cho server co frame dau tien trong RAM...");
      setStatus("Server chua co last_image. Dang tiep tuc doi...", "busy");
      elements.imageMeta.textContent =
        "GET /api/image dang tra ve 404 vi chua co frame nao duoc stream len server.";

      if (lastLoggedError !== "404") {
        lastLoggedError = "404";
        logActivity("GET /api/image -> 404. Dang cho frame dau tien.", "info");
      }
      return;
    }

    if (!response.ok) {
      throw new Error(`Server error: ${response.status}`);
    }

    const imageBlob = await response.blob();
    revokeCurrentImageUrl();
    currentImageUrl = URL.createObjectURL(imageBlob);
    elements.liveImage.src = currentImageUrl;

    receivedFrameCount += 1;
    hasSuccessfulFrame = true;
    lastLoggedError = "";
    elements.frameCount.textContent = String(receivedFrameCount);
    updateLastUpdateLabel();
    updatePreviewState(true);
    elements.imageMeta.textContent =
      `Nhan frame ${receivedFrameCount}: ${formatBytes(imageBlob.size)} | Poll interval ${POLL_INTERVAL_MS}ms`;
    setStatus("Dang hien thi last_image moi nhat tu server.", "ok");

    if (receivedFrameCount === 1 || receivedFrameCount % 20 === 0) {
      logActivity(
        `Nhan frame ${receivedFrameCount} tu GET /api/image (${formatBytes(imageBlob.size)}).`,
        "success"
      );
    }
  } catch (error) {
    if (!hasSuccessfulFrame) {
      updatePreviewState(false, "Khong lay duoc anh tu server. Dang thu lai...");
    }
    setStatus(`Lay anh that bai: ${error.message}`, "error");
    elements.imageMeta.textContent =
      "Kiem tra lai server URL, route /api/image, va xem server da dang chay hay chua.";

    if (lastLoggedError !== error.message) {
      lastLoggedError = error.message;
      logActivity(`GET /api/image loi: ${error.message}`, "error");
    }
  } finally {
    pollInFlight = false;
    scheduleNextPoll(pollStartedAt);
  }
}

window.addEventListener("beforeunload", () => {
  isPolling = false;
  if (nextPollTimer) {
    window.clearTimeout(nextPollTimer);
  }
  revokeCurrentImageUrl();
});

setStatus("Dang bat polling GET /api/image moi 100ms...", "busy");
elements.imageMeta.textContent =
  "Viewer se tu dong poll anh tu server ngay khi trang duoc mo.";
updatePreviewState(false, "Dang cho server co frame dau tien trong RAM...");
updateLastUpdateLabel(new Date(0));
elements.lastUpdate.textContent = "--:--:--";
logActivity("FE simulator da san sang. Dang bat polling GET /api/image @ 10 FPS.", "success");
pollLatestImage();
