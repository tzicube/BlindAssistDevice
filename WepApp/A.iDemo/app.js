const objectInput = document.getElementById("objectInput");
const objectSuggestions = document.getElementById("objectSuggestions");
const cameraSelect = document.getElementById("cameraSelect");
const cameraInput = document.getElementById("cameraInput");
const searchForm = document.getElementById("searchForm");
const startButton = document.getElementById("startButton");
const stopButton = document.getElementById("stopButton");
const refreshButton = document.getElementById("refreshButton");
const cameraPreviewFrame = document.getElementById("cameraPreviewFrame");
const cameraPreviewImage = document.getElementById("cameraPreview");
const videoPlaceholder = document.getElementById("videoPlaceholder");
const statusMessage = document.getElementById("statusMessage");
const streamBadge = document.getElementById("streamBadge");
const activeObjectValue = document.getElementById("activeObjectValue");
const activeCameraValue = document.getElementById("activeCameraValue");
const activeStateValue = document.getElementById("activeStateValue");
const previewElement = cameraPreviewFrame || cameraPreviewImage;

const DEFAULT_API_ORIGIN = "http://127.0.0.1:8000";
let apiOrigin = DEFAULT_API_ORIGIN;
let currentStreamUrl = "";
let lastRequestedTarget = "";
let lastRequestedCamera = "0";
let hasRetriedWithCameraZero = false;

function getBackendOverride() {
  const params = new URLSearchParams(window.location.search);
  const backend = params.get("backend");
  return backend ? backend.trim() : "";
}

function getApiOriginCandidates() {
  const candidates = [];
  const backendOverride = getBackendOverride();

  if (backendOverride) {
    candidates.push(backendOverride);
  }

  if (window.location.protocol !== "file:") {
    candidates.push(window.location.origin);
  }

  if (!candidates.includes(DEFAULT_API_ORIGIN)) {
    candidates.push(DEFAULT_API_ORIGIN);
  }

  return [...new Set(candidates)];
}

async function probeApiOrigin(candidate) {
  const response = await fetch(new URL("/", candidate), {
    headers: {
      Accept: "application/json",
    },
  });
  const contentType = response.headers.get("content-type") || "";
  return response.ok && contentType.includes("application/json");
}

async function resolveApiOrigin() {
  for (const candidate of getApiOriginCandidates()) {
    try {
      const isValidApi = await probeApiOrigin(candidate);
      if (isValidApi) {
        apiOrigin = candidate;
        return candidate;
      }
    } catch (error) {
      // Continue to the next candidate.
    }
  }

  throw new Error(
    "Khong tim thay backend Django. Hay chay server tai http://127.0.0.1:8000 " +
      "hoac mo trang bang /demo/ tu chinh Django."
  );
}

function buildApiUrl(path, query = {}) {
  const url = new URL(path, apiOrigin);

  for (const [key, value] of Object.entries(query)) {
    url.searchParams.set(key, value);
  }

  return url;
}

function setStatus(message, type = "info") {
  statusMessage.textContent = message;
  statusMessage.className = `status${type === "info" ? "" : ` ${type}`}`;
}

function setStreamBadge(label, isLive = false) {
  streamBadge.textContent = label;
  streamBadge.className = `badge${isLive ? " live" : ""}`;
}

function setPreviewState(isActive) {
  videoPlaceholder.classList.toggle("hidden", isActive);
  stopButton.disabled = !isActive;
}

function setBusy(isBusy) {
  startButton.disabled = isBusy;
  refreshButton.disabled = isBusy;
  objectInput.disabled = isBusy;
  cameraSelect.disabled = isBusy;
  cameraInput.disabled = isBusy;
}

function stopStream() {
  currentStreamUrl = "";
  if (previewElement) {
    previewElement.removeAttribute("src");
    previewElement.src = cameraPreviewFrame ? "about:blank" : "";
  }
  setPreviewState(false);
  setStreamBadge("Da dung");
  if (activeStateValue) {
    activeStateValue.textContent = "Da dung";
  }
}

async function fetchJson(url) {
  const response = await fetch(url, {
    headers: {
      Accept: "application/json",
    },
  });
  const contentType = response.headers.get("content-type") || "";
  const responseText = await response.text();

  if (!contentType.includes("application/json")) {
    throw new Error(
      "API tra ve HTML thay vi JSON. Ban dang mo frontend bang sai server. " +
        "Hay mo http://127.0.0.1:8000/demo/."
    );
  }

  let payload;
  try {
    payload = JSON.parse(responseText);
  } catch (error) {
    throw new Error("Server tra ve du lieu khong hop le.");
  }

  if (!response.ok) {
    throw new Error(payload.error || "Server returned an unexpected response.");
  }

  return payload;
}

function syncCameraInputFromSelect() {
  cameraInput.value = cameraSelect.value || "0";
}

function syncCameraSelectFromInput() {
  const desiredValue = cameraInput.value.trim();
  const existingOption = Array.from(cameraSelect.options).find(
    (option) => option.value === desiredValue
  );

  if (existingOption) {
    cameraSelect.value = desiredValue;
    return;
  }

  if (!desiredValue) {
    return;
  }

  const option = document.createElement("option");
  option.value = desiredValue;
  option.textContent = `Camera ${desiredValue}`;
  cameraSelect.appendChild(option);
  cameraSelect.value = desiredValue;
}

function fillCameraOptions(cameras, preferredCamera = "0") {
  cameraSelect.innerHTML = "";

  if (cameras.length === 0) {
    const option = document.createElement("option");
    option.value = "0";
    option.textContent = "Camera 0";
    cameraSelect.appendChild(option);
  } else {
    for (const camera of cameras) {
      const option = document.createElement("option");
      option.value = String(camera.index);
      option.textContent = camera.label;
      cameraSelect.appendChild(option);
    }
  }

  const canRestore = Array.from(cameraSelect.options).some(
    (option) => option.value === String(preferredCamera)
  );

  cameraSelect.value = canRestore ? String(preferredCamera) : cameraSelect.options[0].value;
  syncCameraInputFromSelect();
}

function fillObjectSuggestions(objects) {
  objectSuggestions.innerHTML = "";

  for (const objectName of objects) {
    const option = document.createElement("option");
    option.value = objectName;
    objectSuggestions.appendChild(option);
  }
}

async function refreshCameraList() {
  const currentValue = cameraInput.value || cameraSelect.value || "0";
  const data = await fetchJson(buildApiUrl("/api/cameras/"));
  fillCameraOptions(data.cameras, currentValue || data.default_camera_index || 0);
  return data.cameras;
}

async function loadObjectSuggestions() {
  const data = await fetchJson(buildApiUrl("/api/detectable-objects/"));
  fillObjectSuggestions(data.objects);
}

function updateActiveSummary(targetLabel, cameraIndex, stateLabel) {
  if (activeObjectValue) {
    activeObjectValue.textContent = targetLabel;
  }
  if (activeCameraValue) {
    activeCameraValue.textContent = String(cameraIndex);
  }
  if (activeStateValue) {
    activeStateValue.textContent = stateLabel;
  }
}

async function requestObjectSearch(targetLabel, cameraIndex) {
  if (!targetLabel) {
    setStatus("Hay nhap ten do vat truoc khi bat dau tim.", "error");
    objectInput.focus();
    return;
  }

  lastRequestedTarget = targetLabel;
  lastRequestedCamera = String(cameraIndex);
  setBusy(true);
  setStatus("Dang gui yeu cau tim do vat toi server...");
  setStreamBadge("Dang khoi tao");

  try {
    syncCameraSelectFromInput();
    const streamUrl = buildApiUrl("/webcam/alignment-stream/", {
      target: targetLabel,
      camera: cameraIndex,
      ts: Date.now(),
    });

    currentStreamUrl = streamUrl.toString();
    if (!previewElement) {
      throw new Error("Khong tim thay khung preview. Hay tai lai trang bang Ctrl + F5.");
    }

    previewElement.src = currentStreamUrl;
    setPreviewState(true);
    setStreamBadge("Dang chay", true);
    updateActiveSummary(targetLabel, cameraIndex, "Dang tim");
    setStatus("Dang mo stream tim do vat tu server...", "success");
  } catch (error) {
    stopStream();
    setStatus(error.message, "error");
  } finally {
    setBusy(false);
  }
}

async function startObjectSearch(event) {
  event.preventDefault();
  hasRetriedWithCameraZero = false;

  const targetLabel = objectInput.value.trim();
  const cameraIndex = cameraInput.value.trim() || cameraSelect.value || "0";
  await requestObjectSearch(targetLabel, cameraIndex);
}

async function handleRefreshClick() {
  setBusy(true);
  setStatus("Dang quet lai camera dau vao tren server...");

  try {
    const cameras = await refreshCameraList();
    if (cameras.length === 0) {
      setStatus("Khong tim thay camera nao tu server. Ban van co the thu Camera 0.", "error");
      return;
    }

    setStatus("Da cap nhat danh sach camera tu server.", "success");
  } catch (error) {
    setStatus(error.message, "error");
  } finally {
    setBusy(false);
  }
}

async function initObjectFinder() {
  setPreviewState(false);
  setStreamBadge("Chua chay");
  updateActiveSummary("bottle", 0, "San sang");

  try {
    await resolveApiOrigin();
    await Promise.all([refreshCameraList(), loadObjectSuggestions()]);
    setStatus("Server da san sang. Nhap do vat, chon camera roi bam bat dau.");
  } catch (error) {
    setStatus(error.message, "error");
  }
}

cameraSelect.addEventListener("change", syncCameraInputFromSelect);
cameraInput.addEventListener("change", syncCameraSelectFromInput);
if (previewElement) {
  previewElement.addEventListener("load", () => {
    if (!currentStreamUrl) {
      return;
    }

    setStatus("Stream YOLO dang chay. Server dang tim do vat ban yeu cau.", "success");
  });

  previewElement.addEventListener("error", () => {
    if (!currentStreamUrl) {
      return;
    }

    if (lastRequestedCamera !== "0" && !hasRetriedWithCameraZero) {
      hasRetriedWithCameraZero = true;
      cameraInput.value = "0";
      syncCameraSelectFromInput();
      updateActiveSummary(lastRequestedTarget || "bottle", 0, "Thu lai Camera 0");
      setStatus("Camera da chon khong len. Dang thu lai bang Camera 0...", "error");
      requestObjectSearch(lastRequestedTarget || objectInput.value.trim() || "bottle", "0");
      return;
    }

    stopStream();
    setStatus("Stream bi ngat hoac camera khong con san sang tren server.", "error");
  });
}
refreshButton.addEventListener("click", handleRefreshClick);
stopButton.addEventListener("click", () => {
  stopStream();
  setStatus("Da dung stream tim do vat.", "info");
});
searchForm.addEventListener("submit", startObjectSearch);
window.addEventListener("DOMContentLoaded", initObjectFinder);
