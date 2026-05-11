const cameraSelect = document.getElementById("cameraSelect");
const startButton = document.getElementById("startButton");
const cameraPreview = document.getElementById("cameraPreview");
const videoPlaceholder = document.getElementById("videoPlaceholder");
const statusMessage = document.getElementById("statusMessage");

let currentStream = null;

function setStatus(message, type = "info") {
  statusMessage.textContent = message;
  statusMessage.className = `status${type === "info" ? "" : ` ${type}`}`;
}

function setPreviewState(isActive) {
  videoPlaceholder.classList.toggle("hidden", isActive);
}

function stopCurrentStream() {
  if (!currentStream) {
    return;
  }

  const streamToStop = currentStream;
  currentStream = null;

  for (const track of streamToStop.getTracks()) {
    track.stop();
  }

  cameraPreview.srcObject = null;
  setPreviewState(false);
}

function createCameraLabel(device, index) {
  return device.label || `Camera ${index + 1}`;
}

async function getCameraDevices() {
  const devices = await navigator.mediaDevices.enumerateDevices();
  return devices.filter((device) => device.kind === "videoinput");
}

function fillCameraOptions(devices, preferredDeviceId = "") {
  cameraSelect.innerHTML = "";

  for (const [index, device] of devices.entries()) {
    const option = document.createElement("option");
    option.value = device.deviceId;
    option.textContent = createCameraLabel(device, index);
    cameraSelect.appendChild(option);
  }

  const canRestoreSelection = devices.some(
    (device) => device.deviceId === preferredDeviceId
  );

  if (canRestoreSelection) {
    cameraSelect.value = preferredDeviceId;
  } else if (devices.length > 0) {
    cameraSelect.value = devices[0].deviceId;
  }
}

async function refreshCameraList(
  preferredDeviceId = cameraSelect.value,
  { suppressStatus = false } = {}
) {
  const devices = await getCameraDevices();

  if (devices.length === 0) {
    cameraSelect.innerHTML = '<option value="">No camera detected</option>';
    cameraSelect.disabled = true;
    startButton.disabled = true;
    setStatus("No camera was detected on this device.", "error");
    return [];
  }

  fillCameraOptions(devices, preferredDeviceId);
  cameraSelect.disabled = false;
  startButton.disabled = false;

  if (suppressStatus) {
    return devices;
  }

  const hasLabels = devices.some((device) => device.label);
  if (hasLabels) {
    setStatus("Select a camera, then press Start Camera.");
  } else {
    setStatus(
      "Select a camera, then press Start Camera. Camera names may appear after permission is granted."
    );
  }

  return devices;
}

function getSelectedCameraName() {
  return cameraSelect.options[cameraSelect.selectedIndex]?.textContent || "camera";
}

function buildErrorMessage(error) {
  switch (error.name) {
    case "NotAllowedError":
      return "Camera access was blocked. Please allow permission in the browser and try again.";
    case "NotFoundError":
      return "The selected camera is no longer available.";
    case "NotReadableError":
      return "The selected camera is busy or cannot be read right now.";
    case "OverconstrainedError":
      return "The selected camera could not satisfy the requested constraints.";
    default:
      return "Unable to start the selected camera. Please try again.";
  }
}

function buildVideoConstraints(deviceId = "") {
  const baseConstraints = {
    width: { ideal: 1280 },
    height: { ideal: 720 }
  };

  if (!deviceId) {
    return baseConstraints;
  }

  return {
    ...baseConstraints,
    deviceId: { exact: deviceId }
  };
}

function bindStreamLifecycle(stream) {
  const [track] = stream.getVideoTracks();

  if (!track) {
    return;
  }

  track.addEventListener("ended", () => {
    if (currentStream !== stream) {
      return;
    }

    stopCurrentStream();
    setStatus("The camera stream ended. Select a camera and start again.", "error");
  });
}

async function startCamera() {
  const selectedDeviceId = cameraSelect.value;
  startButton.disabled = true;
  setStatus("Requesting camera access...");

  const constraints = {
    audio: false,
    video: buildVideoConstraints(selectedDeviceId)
  };

  try {
    stopCurrentStream();

    const stream = await navigator.mediaDevices.getUserMedia(constraints);
    currentStream = stream;
    bindStreamLifecycle(stream);
    cameraPreview.srcObject = stream;
    await cameraPreview.play();
    setPreviewState(true);

    const activeTrack = stream.getVideoTracks()[0];
    const activeDeviceId = activeTrack.getSettings().deviceId || selectedDeviceId;

    await refreshCameraList(activeDeviceId, { suppressStatus: true });

    if (activeDeviceId) {
      cameraSelect.value = activeDeviceId;
    }

    if (selectedDeviceId) {
      setStatus(`Live preview started from ${getSelectedCameraName()}.`, "success");
    } else {
      setStatus(
        "Live preview started from the default camera. You can now pick a specific camera if more than one is available.",
        "success"
      );
    }
  } catch (error) {
    stopCurrentStream();
    setStatus(buildErrorMessage(error), "error");
  } finally {
    startButton.disabled = false;
  }
}

async function initCameraLayer() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    cameraSelect.disabled = true;
    startButton.disabled = true;
    setStatus("This browser does not support camera access through getUserMedia().", "error");
    return;
  }

  try {
    await refreshCameraList();
  } catch (error) {
    cameraSelect.disabled = true;
    startButton.disabled = true;
    setStatus("Unable to read the camera list from this browser.", "error");
  }
}

startButton.addEventListener("click", startCamera);

if (navigator.mediaDevices?.addEventListener) {
  navigator.mediaDevices.addEventListener("devicechange", async () => {
    const preferredDeviceId =
      currentStream?.getVideoTracks?.()[0]?.getSettings?.().deviceId || cameraSelect.value;

    try {
      await refreshCameraList(preferredDeviceId, { suppressStatus: Boolean(currentStream) });
    } catch (error) {
      setStatus("Camera list changed, but the browser could not refresh it.", "error");
    }
  });
}

window.addEventListener("beforeunload", stopCurrentStream);
window.addEventListener("DOMContentLoaded", initCameraLayer);
