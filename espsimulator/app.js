const QUERY_PARAMETERS = new URLSearchParams(window.location.search);
const CONFIGURED_SERVER_BASE_URL = QUERY_PARAMETERS.get("server")?.trim();
const PAGE_HOST = window.location.hostname || "localhost";
const API_HOST = ["localhost", "::1", "[::1]"].includes(PAGE_HOST)
  ? "127.0.0.1"
  : PAGE_HOST;
const DEFAULT_SERVER_BASE_URL =
  CONFIGURED_SERVER_BASE_URL || `http://${API_HOST}:8787`;
const DEFAULT_VIDEOFRAME_PATH = "/api/videoframe";
const DEFAULT_RECOGNIZE_PATH = "/api/recognize";
const DEFAULT_TELEMETRY_API_URL = `${DEFAULT_SERVER_BASE_URL.replace(/\/+$/, "")}/api/telemetry`;
const VIDEO_WIDTH = 320;
const VIDEO_HEIGHT = 240;
const VIDEO_FPS = 30;
const AUTO_STREAM_INTERVAL_MS = Math.round(1000 / VIDEO_FPS);
const TELEMETRY_INTERVAL_MS = 5000;

const elements = {
  serverBaseUrl: document.getElementById("serverBaseUrl"),
  videoframePath: document.getElementById("videoframePath"),
  recognizePath: document.getElementById("recognizePath"),
  gpsLatitude: document.getElementById("gpsLatitude"),
  gpsLongitude: document.getElementById("gpsLongitude"),
  telemetryAddress: document.getElementById("telemetryAddress"),
  telemetryHeading: document.getElementById("telemetryHeading"),
  telemetryBattery: document.getElementById("telemetryBattery"),
  telemetryApiUrl: document.getElementById("telemetryApiUrl"),
  sendTelemetryButton: document.getElementById("sendTelemetryButton"),
  telemetryStatus: document.getElementById("telemetryStatus"),
  telemetryMeta: document.getElementById("telemetryMeta"),
  previewShell: document.getElementById("previewShell"),
  powerButton: document.getElementById("powerButton"),
  powerButtonState: document.getElementById("powerButtonState"),
  recognizeButton: document.getElementById("recognizeButton"),
  recognizeButtonState: document.getElementById("recognizeButtonState"),
  streamStatus: document.getElementById("streamStatus"),
  recognizeStatus: document.getElementById("recognizeStatus"),
  frameMeta: document.getElementById("frameMeta"),
  audioMeta: document.getElementById("audioMeta"),
  responseMeta: document.getElementById("responseMeta"),
  activityLog: document.getElementById("activityLog"),
  cameraPreview: document.getElementById("cameraPreview"),
  frameCanvas: document.getElementById("frameCanvas"),
  frameCounter: document.getElementById("frameCounter"),
  recordingIndicator: document.getElementById("recordingIndicator"),
  responseAudio: document.getElementById("responseAudio"),
};

let cameraStream = null;
let autoStreamTimer = null;
let frameRequestInFlight = false;
let streamedFrameCount = 0;
let hasStreamedFrame = false;
let recognizeRequestInFlight = false;
let lastStreamErrorMessage = "";
let telemetryTimer = null;
let telemetryRequestInFlight = false;

let recordingStream = null;
let recordingContext = null;
let recordingSourceNode = null;
let recordingProcessorNode = null;
let recordingSilenceNode = null;
let recordingBuffers = [];
let recordingSampleRate = 44100;
let recordingStartTime = 0;
let recordingTicker = null;
let isRecording = false;
let currentResponseAudioBlob = null;
let currentResponseAudioUrl = null;

elements.serverBaseUrl.value = DEFAULT_SERVER_BASE_URL;
elements.videoframePath.value = DEFAULT_VIDEOFRAME_PATH;
elements.recognizePath.value = DEFAULT_RECOGNIZE_PATH;
elements.telemetryApiUrl.value = DEFAULT_TELEMETRY_API_URL;

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

function setStatus(element, message, tone = "idle") {
  element.textContent = message;
  element.dataset.tone = tone;
}

function setRecordingIndicator(message, state = "idle") {
  elements.recordingIndicator.textContent = message;
  elements.recordingIndicator.dataset.state = state;
}

function updateFrameMeta(message) {
  elements.frameMeta.textContent = message;
}

function updateAudioMeta(message) {
  elements.audioMeta.textContent = message;
}

function updateResponseMeta(message) {
  elements.responseMeta.textContent = message;
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

function formatDurationMs(durationMs) {
  return `${(durationMs / 1000).toFixed(1)}s`;
}

function cameraSupportIssue() {
  if (!window.isSecureContext) {
    return "Webcam bi chan vi trang khong o secure context. Mo simulator bang http://127.0.0.1:8790 trong Chrome/Edge, hoac dung HTTPS.";
  }

  if (!navigator.mediaDevices?.getUserMedia) {
    return "Trang hien tai khong duoc cap API webcam. Hay mo lai simulator bang origin Live Server da tung duoc cap quyen camera.";
  }

  return "";
}

function describeMediaError(error) {
  const supportIssue = cameraSupportIssue();
  if (supportIssue) {
    return supportIssue;
  }

  if (error?.name === "NotAllowedError" || error?.name === "SecurityError") {
    return "Quyen camera bi tu choi. Cho phep Camera cho 127.0.0.1 trong trinh duyet, tai lai trang, roi bam Power.";
  }
  if (error?.name === "NotFoundError" || error?.name === "DevicesNotFoundError") {
    return "Khong tim thay webcam. Kiem tra camera da ket noi va duoc Windows nhan dien.";
  }
  if (error?.name === "NotReadableError" || error?.name === "TrackStartError") {
    return "Webcam dang bi ung dung khac su dung hoac driver khong mo duoc camera.";
  }

  return error?.message || "Khong mo duoc webcam.";
}

function syncUi() {
  const powerOn = Boolean(cameraStream);

  elements.previewShell.dataset.online = powerOn ? "true" : "false";
  elements.powerButton.disabled = recognizeRequestInFlight;
  elements.powerButton.dataset.state = powerOn ? "on" : "off";
  elements.powerButtonState.textContent = powerOn ? "STREAMING" : "OFF";

  if (recognizeRequestInFlight) {
    elements.recognizeButton.dataset.state = "busy";
    elements.recognizeButtonState.textContent = "WAIT";
  } else if (isRecording) {
    elements.recognizeButton.dataset.state = "recording";
    elements.recognizeButtonState.textContent = "SEND";
  } else {
    elements.recognizeButton.dataset.state = hasStreamedFrame ? "ready" : "idle";
    elements.recognizeButtonState.textContent = hasStreamedFrame ? "READY" : "IDLE";
  }

  elements.recognizeButton.disabled =
    recognizeRequestInFlight || !powerOn || (!isRecording && !hasStreamedFrame);
}

function drawVideoToCanvas() {
  const canvas = elements.frameCanvas;
  const context = canvas.getContext("2d");

  canvas.width = VIDEO_WIDTH;
  canvas.height = VIDEO_HEIGHT;
  context.fillStyle = "#08131f";
  context.fillRect(0, 0, VIDEO_WIDTH, VIDEO_HEIGHT);

  const sourceWidth = elements.cameraPreview.videoWidth;
  const sourceHeight = elements.cameraPreview.videoHeight;

  if (!sourceWidth || !sourceHeight) {
    throw new Error("Camera chua co frame de chup");
  }

  const scale = Math.min(VIDEO_WIDTH / sourceWidth, VIDEO_HEIGHT / sourceHeight);
  const targetWidth = sourceWidth * scale;
  const targetHeight = sourceHeight * scale;
  const offsetX = (VIDEO_WIDTH - targetWidth) / 2;
  const offsetY = (VIDEO_HEIGHT - targetHeight) / 2;

  context.drawImage(
    elements.cameraPreview,
    offsetX,
    offsetY,
    targetWidth,
    targetHeight
  );
}

function waitForCameraFrame(timeoutMs = 1500) {
  if (elements.cameraPreview.videoWidth && elements.cameraPreview.videoHeight) {
    return Promise.resolve();
  }

  return new Promise((resolve, reject) => {
    let settled = false;

    function cleanup() {
      window.clearTimeout(timeoutId);
      elements.cameraPreview.removeEventListener("loadeddata", handleReady);
      elements.cameraPreview.removeEventListener("canplay", handleReady);
    }

    function handleReady() {
      if (settled) {
        return;
      }

      if (elements.cameraPreview.videoWidth && elements.cameraPreview.videoHeight) {
        settled = true;
        cleanup();
        resolve();
      }
    }

    const timeoutId = window.setTimeout(() => {
      if (settled) {
        return;
      }

      settled = true;
      cleanup();
      reject(new Error("Camera chua xuat frame dau tien"));
    }, timeoutMs);

    elements.cameraPreview.addEventListener("loadeddata", handleReady);
    elements.cameraPreview.addEventListener("canplay", handleReady);
  });
}

function canvasToJpegBlob() {
  return new Promise((resolve, reject) => {
    elements.frameCanvas.toBlob(
      (blob) => {
        if (!blob) {
          reject(new Error("Khong tao duoc JPEG tu camera preview"));
          return;
        }

        resolve(blob);
      },
      "image/jpeg",
      0.9
    );
  });
}

async function captureFrameFromCamera() {
  if (!cameraStream) {
    throw new Error("Power chua bat");
  }

  drawVideoToCanvas();
  return canvasToJpegBlob();
}

async function sendFrameBlob(frameBlob) {
  const endpoint = buildEndpoint(
    elements.serverBaseUrl.value,
    elements.videoframePath.value
  );

  frameRequestInFlight = true;
  setStatus(elements.streamStatus, "Dang stream frame len server...", "busy");

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "image/jpeg",
      },
      body: frameBlob,
    });

    const contentType = response.headers.get("content-type") || "";
    let payload = null;

    if (contentType.includes("application/json")) {
      payload = await response.json();
    }

    if (!response.ok) {
      const message =
        payload?.error || payload?.message || `Server error: ${response.status}`;
      throw new Error(message);
    }

    streamedFrameCount += 1;
    hasStreamedFrame = true;
    lastStreamErrorMessage = "";
    elements.frameCounter.textContent = String(streamedFrameCount);
    updateFrameMeta(
      `Dang stream ${VIDEO_WIDTH}x${VIDEO_HEIGHT} @ ${VIDEO_FPS} FPS. Frame moi nhat: ${formatBytes(frameBlob.size)}`
    );
    setStatus(
      elements.streamStatus,
      `Power dang mo. Last image da duoc cap nhat, tong ${streamedFrameCount} frame.`,
      "ok"
    );
    syncUi();
  } finally {
    frameRequestInFlight = false;
  }
}

function startAutoStreamLoop() {
  if (autoStreamTimer) {
    return;
  }

  autoStreamTimer = window.setInterval(async () => {
    if (!cameraStream || frameRequestInFlight) {
      return;
    }

    try {
      const frameBlob = await captureFrameFromCamera();
      await sendFrameBlob(frameBlob);
    } catch (error) {
      setStatus(elements.streamStatus, `Stream loi: ${error.message}`, "error");
      if (lastStreamErrorMessage !== error.message) {
        lastStreamErrorMessage = error.message;
        logActivity(`Stream loi: ${error.message}`, "error");
      }
    }
  }, AUTO_STREAM_INTERVAL_MS);
}

function stopAutoStreamLoop() {
  if (!autoStreamTimer) {
    return;
  }

  window.clearInterval(autoStreamTimer);
  autoStreamTimer = null;
}

async function powerOn() {
  if (cameraStream) {
    return;
  }

  const supportIssue = cameraSupportIssue();
  if (supportIssue) {
    throw new Error(supportIssue);
  }

  logActivity("Dang bat Power va xin quyen camera.", "info");
  hasStreamedFrame = false;
  lastStreamErrorMessage = "";
  syncUi();

  let stream;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: VIDEO_WIDTH },
        height: { ideal: VIDEO_HEIGHT },
        frameRate: { ideal: VIDEO_FPS, max: VIDEO_FPS },
      },
      audio: false,
    });
  } catch (error) {
    throw new Error(describeMediaError(error), { cause: error });
  }

  cameraStream = stream;
  elements.cameraPreview.srcObject = stream;
  await elements.cameraPreview.play();
  await waitForCameraFrame();

  setStatus(elements.streamStatus, `Power da bat. Dang khoi dong stream ${VIDEO_FPS} FPS...`, "busy");
  updateFrameMeta("Dang doi frame dau tien tu webcam.");
  syncUi();

  startAutoStreamLoop();
  await sendFrameBlob(await captureFrameFromCamera());
  startTelemetryLoop();
  void sendTelemetryUpdate({ automatic: true });
  logActivity(`Power ON. ESP simulator dang stream lien tuc ${VIDEO_FPS} FPS.`, "success");
}

async function cleanupRecordingGraph() {
  if (recordingTicker) {
    window.clearInterval(recordingTicker);
    recordingTicker = null;
  }

  recordingProcessorNode?.disconnect();
  recordingSourceNode?.disconnect();
  recordingSilenceNode?.disconnect();

  recordingStream?.getTracks().forEach((track) => track.stop());
  recordingStream = null;

  if (recordingContext) {
    await recordingContext.close();
  }

  recordingContext = null;
  recordingSourceNode = null;
  recordingProcessorNode = null;
  recordingSilenceNode = null;
}

async function cancelRecording(reason) {
  if (!isRecording) {
    return;
  }

  isRecording = false;
  recordingBuffers = [];
  await cleanupRecordingGraph();
  setRecordingIndicator("Chua ghi am.", "idle");
  updateAudioMeta(reason);
  setStatus(elements.recognizeStatus, reason, "idle");
  syncUi();
  logActivity(reason, "info");
}

async function powerOff() {
  if (!cameraStream) {
    return;
  }

  if (isRecording) {
    await cancelRecording("Power da tat nen phien ghi am hien tai da bi huy.");
  }

  stopAutoStreamLoop();
  stopTelemetryLoop();
  cameraStream.getTracks().forEach((track) => track.stop());
  cameraStream = null;
  elements.cameraPreview.srcObject = null;
  hasStreamedFrame = false;
  lastStreamErrorMessage = "";
  elements.responseAudio.pause();
  elements.responseAudio.currentTime = 0;

  if (!recognizeRequestInFlight) {
    setStatus(elements.recognizeStatus, "Power dang tat. Bam Power de stream lai.", "idle");
  }

  setStatus(elements.streamStatus, "Power da tat. Webcam va stream da dung.", "idle");
  updateFrameMeta("Khong co frame nao duoc gui khi Power OFF.");
  syncUi();
  logActivity("Power OFF. Da dung stream camera.", "info");
}

async function togglePower() {
  if (recognizeRequestInFlight) {
    throw new Error("Dang doi audio response, vui long cho xong");
  }

  if (cameraStream) {
    await powerOff();
    return;
  }

  await powerOn();
}

function mergeFloat32Buffers(buffers) {
  const totalLength = buffers.reduce((sum, buffer) => sum + buffer.length, 0);
  const merged = new Float32Array(totalLength);
  let offset = 0;

  for (const buffer of buffers) {
    merged.set(buffer, offset);
    offset += buffer.length;
  }

  return merged;
}

function encodeWav(samples, sampleRate) {
  const buffer = new ArrayBuffer(44 + samples.length * 2);
  const view = new DataView(buffer);

  function writeString(offset, value) {
    for (let index = 0; index < value.length; index += 1) {
      view.setUint8(offset + index, value.charCodeAt(index));
    }
  }

  writeString(0, "RIFF");
  view.setUint32(4, 36 + samples.length * 2, true);
  writeString(8, "WAVE");
  writeString(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeString(36, "data");
  view.setUint32(40, samples.length * 2, true);

  let offset = 44;
  for (let index = 0; index < samples.length; index += 1) {
    const sample = Math.max(-1, Math.min(1, samples[index]));
    view.setInt16(offset, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true);
    offset += 2;
  }

  return new Blob([view], { type: "audio/wav" });
}

async function startRecording() {
  if (isRecording) {
    return;
  }

  logActivity("Nhan nut Recognize lan 1. Dang bat microphone.", "info");
  elements.responseAudio.pause();
  elements.responseAudio.currentTime = 0;

  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
    },
    video: false,
  });

  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) {
    stream.getTracks().forEach((track) => track.stop());
    throw new Error("Trinh duyet khong ho tro Web Audio");
  }

  recordingStream = stream;
  recordingContext = new AudioContextClass();
  await recordingContext.resume();
  recordingSampleRate = recordingContext.sampleRate;
  recordingBuffers = [];
  recordingSourceNode = recordingContext.createMediaStreamSource(recordingStream);
  recordingProcessorNode = recordingContext.createScriptProcessor(4096, 1, 1);
  recordingSilenceNode = recordingContext.createGain();
  recordingSilenceNode.gain.value = 0;

  recordingProcessorNode.onaudioprocess = (event) => {
    if (!isRecording) {
      return;
    }

    const channelData = event.inputBuffer.getChannelData(0);
    recordingBuffers.push(new Float32Array(channelData));
  };

  recordingSourceNode.connect(recordingProcessorNode);
  recordingProcessorNode.connect(recordingSilenceNode);
  recordingSilenceNode.connect(recordingContext.destination);

  isRecording = true;
  recordingStartTime = Date.now();
  setRecordingIndicator("Dang ghi cau hoi...", "recording");
  updateAudioMeta("Nut Recognize dang ghi am. Bam lai mot lan nua de gui.");
  setStatus(
    elements.recognizeStatus,
    "Dang ghi cau hoi. Nut Recognize se gui audio khi bam lan tiep theo.",
    "busy"
  );
  syncUi();

  recordingTicker = window.setInterval(() => {
    updateAudioMeta(`Dang ghi: ${formatDurationMs(Date.now() - recordingStartTime)}`);
  }, 200);

  logActivity("Microphone da bat, dang ghi cau hoi.", "success");
}

async function stopRecordingAndBuildWav() {
  if (!isRecording) {
    throw new Error("Chua co phien ghi am nao");
  }

  isRecording = false;
  const durationMs = Date.now() - recordingStartTime;
  const capturedBuffers = recordingBuffers;
  const capturedSampleRate = recordingSampleRate;
  recordingBuffers = [];

  await cleanupRecordingGraph();

  const mergedSamples = mergeFloat32Buffers(capturedBuffers);
  if (!mergedSamples.length) {
    throw new Error("Khong thu duoc du lieu audio. Thu lai giup anh.");
  }

  const wavBlob = encodeWav(mergedSamples, capturedSampleRate);
  setRecordingIndicator("Da ghi xong.", "ready");
  updateAudioMeta(
    `Da khoa audio WAV: ${formatBytes(wavBlob.size)}, thoi luong ${formatDurationMs(durationMs)}`
  );
  syncUi();
  return {
    wavBlob,
    durationMs,
  };
}

async function sendRecognizeRequest(audioBlob, durationMs) {
  const endpoint = buildEndpoint(
    elements.serverBaseUrl.value,
    elements.recognizePath.value
  );

  recognizeRequestInFlight = true;
  syncUi();
  setStatus(
    elements.recognizeStatus,
    `Dang gui ${formatDurationMs(durationMs)} audio len server...`,
    "busy"
  );

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "audio/wav",
      },
      body: audioBlob,
    });

    const contentType = response.headers.get("content-type") || "";

    if (!response.ok || !contentType.includes("audio/wav")) {
      let message = `Server error: ${response.status}`;

      if (contentType.includes("application/json")) {
        const errorPayload = await response.json();
        message = errorPayload.error || errorPayload.message || message;
      }

      throw new Error(message);
    }

    currentResponseAudioBlob = await response.blob();

    if (currentResponseAudioUrl) {
      URL.revokeObjectURL(currentResponseAudioUrl);
    }

    currentResponseAudioUrl = URL.createObjectURL(currentResponseAudioBlob);
    elements.responseAudio.src = currentResponseAudioUrl;
    elements.responseAudio.load();

    updateResponseMeta(
      `Server tra ve ${formatBytes(currentResponseAudioBlob.size)} audio WAV. Dang thu phat ngay.`
    );
    setStatus(
      elements.recognizeStatus,
      "Nhan response thanh cong. Dang phat loa neu trinh duyet cho phep.",
      "ok"
    );
    logActivity(
      `POST ${endpoint} thanh cong, response ${formatBytes(currentResponseAudioBlob.size)}.`,
      "success"
    );

    try {
      await elements.responseAudio.play();
    } catch (error) {
      logActivity(
        `Trinh duyet chan auto play (${error.message}). Bam Play de nghe thu cong.`,
        "info"
      );
    }
  } finally {
    recognizeRequestInFlight = false;
    syncUi();
  }
}

async function handleRecognizeButtonPress() {
  if (!cameraStream) {
    throw new Error("Can bat Power truoc khi dung Recognize");
  }

  if (recognizeRequestInFlight) {
    return;
  }

  if (!hasStreamedFrame && !isRecording) {
    throw new Error("Can doi server nhan frame dau tien truoc");
  }

  if (!isRecording) {
    await startRecording();
    return;
  }

  logActivity("Nhan nut Recognize lan 2. Dang khoa audio va gui len server.", "info");
  const { wavBlob, durationMs } = await stopRecordingAndBuildWav();
  await sendRecognizeRequest(wavBlob, durationMs);
}

function resolveTelemetryEndpoint() {
  const enteredUrl = elements.telemetryApiUrl.value.trim() || DEFAULT_TELEMETRY_API_URL;
  let url;

  try {
    url = new URL(enteredUrl);
  } catch {
    throw new Error(`Enter a valid API URL, for example ${DEFAULT_TELEMETRY_API_URL}`);
  }

  const path = url.pathname.replace(/\/+$/, "") || "/";
  if (url.port === "5173" || path === "/") {
    url.protocol = "http:";
    url.port = "8787";
    url.pathname = "/api/telemetry";
    url.search = "";
    url.hash = "";
    elements.telemetryApiUrl.value = url.href;
  }

  if (url.port !== "8787" || url.pathname.replace(/\/+$/, "") !== "/api/telemetry") {
    throw new Error(`Use the backend endpoint ${DEFAULT_TELEMETRY_API_URL}`);
  }

  return url.href;
}

function startTelemetryLoop() {
  if (telemetryTimer) {
    return;
  }

  telemetryTimer = window.setInterval(() => {
    void sendTelemetryUpdate({ automatic: true });
  }, TELEMETRY_INTERVAL_MS);
}

function stopTelemetryLoop() {
  if (!telemetryTimer) {
    return;
  }

  window.clearInterval(telemetryTimer);
  telemetryTimer = null;
}

async function sendTelemetryUpdate({ automatic = false } = {}) {
  if (telemetryRequestInFlight) {
    return;
  }

  if (!elements.gpsLatitude.value.trim() || !elements.gpsLongitude.value.trim()) {
    setStatus(elements.telemetryStatus, "Enter both latitude and longitude.", "error");
    return;
  }

  const latitude = Number(elements.gpsLatitude.value);
  const longitude = Number(elements.gpsLongitude.value);
  const address = elements.telemetryAddress.value.trim();
  const heading = Number(elements.telemetryHeading.value);
  const battery = Number(elements.telemetryBattery.value);
  let endpoint;

  try {
    endpoint = resolveTelemetryEndpoint();
  } catch (error) {
    setStatus(elements.telemetryStatus, error.message, "error");
    return;
  }

  if (!Number.isFinite(latitude) || latitude < -90 || latitude > 90) {
    setStatus(elements.telemetryStatus, "Latitude must be between -90 and 90.", "error");
    return;
  }

  if (!Number.isFinite(longitude) || longitude < -180 || longitude > 180) {
    setStatus(elements.telemetryStatus, "Longitude must be between -180 and 180.", "error");
    return;
  }

  if (!address) {
    setStatus(elements.telemetryStatus, "Dia chi khong duoc de trong.", "error");
    return;
  }

  if (!Number.isFinite(heading) || heading < 0 || heading >= 360) {
    setStatus(elements.telemetryStatus, "Phuong huong phai tu 0 den duoi 360 do.", "error");
    return;
  }

  if (!Number.isFinite(battery) || battery < 0 || battery > 100) {
    setStatus(elements.telemetryStatus, "Muc pin phai tu 0 den 100%.", "error");
    return;
  }

  telemetryRequestInFlight = true;
  elements.sendTelemetryButton.disabled = true;
  setStatus(elements.telemetryStatus, `Dang gui telemetry den ${endpoint}...`, "busy");

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        latitude,
        longitude,
        address,
        heading,
        battery,
        source: "esp-simulator",
      }),
    });
    const result = await response.json();

    if (!response.ok) {
      throw new Error(result.message || `Server error: ${response.status}`);
    }

    const telemetry = result.telemetry || {};
    setStatus(elements.telemetryStatus, "Backend da nhan telemetry.", "ok");
    elements.telemetryMeta.textContent =
      `${automatic ? "Auto" : "Manual"}: ${latitude.toFixed(6)}, ${longitude.toFixed(6)} · ${telemetry.direction || "--"} ${heading.toFixed(1)}° · pin ${battery.toFixed(0)}%`;
    logActivity(
      `Telemetry sent: ${telemetry.direction || "--"} ${heading.toFixed(1)}°, pin ${battery.toFixed(0)}%.`,
      "success"
    );
  } catch (error) {
    setStatus(elements.telemetryStatus, `Telemetry update failed: ${error.message}`, "error");
    logActivity(`Telemetry update failed: ${error.message}`, "error");
  } finally {
    telemetryRequestInFlight = false;
    elements.sendTelemetryButton.disabled = false;
  }
}

elements.sendTelemetryButton.addEventListener("click", () => {
  void sendTelemetryUpdate();
});

elements.powerButton.addEventListener("click", async () => {
  try {
    await togglePower();
  } catch (error) {
    setStatus(elements.streamStatus, `Power loi: ${error.message}`, "error");
    logActivity(`Power loi: ${error.message}`, "error");
  }
});

elements.recognizeButton.addEventListener("click", async () => {
  try {
    await handleRecognizeButtonPress();
  } catch (error) {
    setStatus(elements.recognizeStatus, `Recognize loi: ${error.message}`, "error");
    logActivity(`Recognize loi: ${error.message}`, "error");
    syncUi();
  }
});

window.addEventListener("beforeunload", () => {
  stopAutoStreamLoop();
  stopTelemetryLoop();

  if (cameraStream) {
    cameraStream.getTracks().forEach((track) => track.stop());
    cameraStream = null;
  }

  if (recordingTicker) {
    window.clearInterval(recordingTicker);
  }

  recordingProcessorNode?.disconnect();
  recordingSourceNode?.disconnect();
  recordingSilenceNode?.disconnect();
  recordingStream?.getTracks().forEach((track) => track.stop());
  recordingContext?.close();

  if (currentResponseAudioUrl) {
    URL.revokeObjectURL(currentResponseAudioUrl);
  }
});

setStatus(
  elements.streamStatus,
  `Power OFF. Bam nut Power de bat task stream ${VIDEO_FPS} FPS.`,
  "idle"
);
setStatus(
  elements.recognizeStatus,
  "Recognize se san sang sau khi server nhan duoc frame dau tien.",
  "idle"
);
setRecordingIndicator("Chua ghi am.", "idle");
updateFrameMeta(
  cameraSupportIssue() ||
    "ESP simulator se stream webcam thanh JPEG 320x240 len /api/videoframe."
);
updateAudioMeta("Recognize: bam lan 1 de ghi, bam lan 2 de gui audio WAV.");
updateResponseMeta("Audio response tu server se phat ngay tai day.");
setStatus(elements.telemetryStatus, "Chua gui telemetry.", "idle");
elements.telemetryMeta.textContent = "Power ON se gui ngay, sau do ESP simulator tu gui moi 5 giay.";
elements.frameCounter.textContent = "0";
syncUi();
logActivity("ESP simulator da san sang. Hai task se chay dung nhu thiet bi that.", "success");
