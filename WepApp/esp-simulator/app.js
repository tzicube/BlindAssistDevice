const DEFAULT_SERVER_BASE_URL = "http://localhost:8765";
const DEFAULT_VIDEOFRAME_PATH = "/api/videoframe";
const DEFAULT_RECOGNIZE_PATH = "/api/recognize";
const VIDEO_WIDTH = 320;
const VIDEO_HEIGHT = 240;
const AUTO_STREAM_INTERVAL_MS = 100;

const elements = {
  serverBaseUrl: document.getElementById("serverBaseUrl"),
  videoframePath: document.getElementById("videoframePath"),
  recognizePath: document.getElementById("recognizePath"),
  streamStatus: document.getElementById("streamStatus"),
  recognizeStatus: document.getElementById("recognizeStatus"),
  frameMeta: document.getElementById("frameMeta"),
  audioMeta: document.getElementById("audioMeta"),
  responseMeta: document.getElementById("responseMeta"),
  activityLog: document.getElementById("activityLog"),
  cameraPreview: document.getElementById("cameraPreview"),
  imagePreview: document.getElementById("imagePreview"),
  frameCanvas: document.getElementById("frameCanvas"),
  startCameraButton: document.getElementById("startCameraButton"),
  stopCameraButton: document.getElementById("stopCameraButton"),
  sendFrameButton: document.getElementById("sendFrameButton"),
  autoStreamCheckbox: document.getElementById("autoStreamCheckbox"),
  imageFileInput: document.getElementById("imageFileInput"),
  frameCounter: document.getElementById("frameCounter"),
  uploadImageButton: document.getElementById("uploadImageButton"),
  recordingIndicator: document.getElementById("recordingIndicator"),
  recordButton: document.getElementById("recordButton"),
  stopRecordButton: document.getElementById("stopRecordButton"),
  audioFileInput: document.getElementById("audioFileInput"),
  sendRecognizeButton: document.getElementById("sendRecognizeButton"),
  responseAudio: document.getElementById("responseAudio"),
  downloadResponseButton: document.getElementById("downloadResponseButton"),
};

let cameraStream = null;
let autoStreamTimer = null;
let frameRequestInFlight = false;
let recognizeRequestInFlight = false;
let lastPreparedFrameBlob = null;
let preparedFrameSource = "";
let streamedFrameCount = 0;
let uploadedImageBitmap = null;
let uploadedImagePreviewUrl = null;

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
let currentRequestAudioBlob = null;
let currentRequestAudioName = "";
let currentResponseAudioBlob = null;
let currentResponseAudioUrl = null;

elements.serverBaseUrl.value = DEFAULT_SERVER_BASE_URL;
elements.videoframePath.value = DEFAULT_VIDEOFRAME_PATH;
elements.recognizePath.value = DEFAULT_RECOGNIZE_PATH;

function nowLabel() {
  return new Date().toLocaleTimeString("vi-VN", {
    hour12: false,
  });
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

function showCameraPreview() {
  elements.cameraPreview.hidden = false;
  elements.imagePreview.hidden = true;
}

function showImagePreview(previewUrl) {
  elements.imagePreview.src = previewUrl;
  elements.imagePreview.hidden = false;
  elements.cameraPreview.hidden = true;
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

function setFrameButtonsState() {
  const hasCamera = Boolean(cameraStream);
  const hasPreparedFrame = Boolean(lastPreparedFrameBlob);

  elements.stopCameraButton.disabled = !hasCamera;
  elements.autoStreamCheckbox.disabled = !hasCamera;
  elements.sendFrameButton.disabled = !hasCamera && !uploadedImageBitmap;
  elements.uploadImageButton.disabled = !elements.imageFileInput.files.length;

  if (!hasCamera && elements.autoStreamCheckbox.checked) {
    elements.autoStreamCheckbox.checked = false;
  }

  if (!hasPreparedFrame && !hasCamera && !uploadedImageBitmap) {
    updateFrameMeta("Chua co frame nao san sang de gui.");
  }
}

function setRecordingButtonsState() {
  elements.recordButton.disabled = isRecording;
  elements.stopRecordButton.disabled = !isRecording;
  elements.sendRecognizeButton.disabled =
    recognizeRequestInFlight || !currentRequestAudioBlob;
}

function setRecordingIndicator(message, state = "idle") {
  elements.recordingIndicator.textContent = message;
  elements.recordingIndicator.dataset.state = state;
}

function resetPreparedFrame(sourceLabel = "") {
  lastPreparedFrameBlob = null;
  preparedFrameSource = sourceLabel;
  setFrameButtonsState();
}

async function startCamera() {
  if (cameraStream) {
    return;
  }

  logActivity("Dang yeu cau truy cap camera.", "info");

  const stream = await navigator.mediaDevices.getUserMedia({
    video: {
      width: { ideal: VIDEO_WIDTH },
      height: { ideal: VIDEO_HEIGHT },
    },
    audio: false,
  });

  cameraStream = stream;
  elements.cameraPreview.srcObject = stream;
  await elements.cameraPreview.play();
  preparedFrameSource = "camera";

  showCameraPreview();
  setStatus(
    elements.streamStatus,
    "Camera san sang. Co the gui frame hoac bat auto stream 10 FPS.",
    "ok"
  );
  updateFrameMeta("Camera dang phat 320x240 preview.");
  setFrameButtonsState();
  logActivity("Camera da san sang.", "success");
}

function stopCamera() {
  if (!cameraStream) {
    return;
  }

  cameraStream.getTracks().forEach((track) => track.stop());
  cameraStream = null;
  elements.cameraPreview.srcObject = null;
  stopAutoStream();

  if (uploadedImagePreviewUrl) {
    showImagePreview(uploadedImagePreviewUrl);
  }

  setStatus(elements.streamStatus, "Camera da dung.", "idle");
  setFrameButtonsState();
  logActivity("Camera da dung.", "info");
}

function drawBitmapToCanvas(imageSource) {
  const canvas = elements.frameCanvas;
  const context = canvas.getContext("2d");

  canvas.width = VIDEO_WIDTH;
  canvas.height = VIDEO_HEIGHT;

  context.fillStyle = "#0f172a";
  context.fillRect(0, 0, VIDEO_WIDTH, VIDEO_HEIGHT);

  const sourceWidth = imageSource.videoWidth || imageSource.width;
  const sourceHeight = imageSource.videoHeight || imageSource.height;
  const scale = Math.min(VIDEO_WIDTH / sourceWidth, VIDEO_HEIGHT / sourceHeight);
  const targetWidth = sourceWidth * scale;
  const targetHeight = sourceHeight * scale;
  const offsetX = (VIDEO_WIDTH - targetWidth) / 2;
  const offsetY = (VIDEO_HEIGHT - targetHeight) / 2;

  context.drawImage(imageSource, offsetX, offsetY, targetWidth, targetHeight);
}

function canvasToJpegBlob() {
  return new Promise((resolve, reject) => {
    elements.frameCanvas.toBlob(
      (blob) => {
        if (!blob) {
          reject(new Error("Khong tao duoc JPEG tu canvas"));
          return;
        }

        resolve(blob);
      },
      "image/jpeg",
      0.9
    );
  });
}

async function prepareFrameFromCamera() {
  if (!cameraStream) {
    throw new Error("Camera chua duoc bat");
  }

  drawBitmapToCanvas(elements.cameraPreview);
  const frameBlob = await canvasToJpegBlob();

  lastPreparedFrameBlob = frameBlob;
  preparedFrameSource = "camera";
  updateFrameMeta(
    `Frame camera san sang: ${VIDEO_WIDTH}x${VIDEO_HEIGHT}, ${formatBytes(frameBlob.size)}`
  );
  setFrameButtonsState();
  return frameBlob;
}

async function prepareFrameFromUpload(file) {
  if (!file) {
    throw new Error("Chua chon file anh");
  }

  stopAutoStream();

  if (uploadedImagePreviewUrl) {
    URL.revokeObjectURL(uploadedImagePreviewUrl);
  }

  uploadedImagePreviewUrl = URL.createObjectURL(file);
  showImagePreview(uploadedImagePreviewUrl);

  if (uploadedImageBitmap) {
    uploadedImageBitmap.close();
  }

  uploadedImageBitmap = await createImageBitmap(file);
  drawBitmapToCanvas(uploadedImageBitmap);

  const frameBlob = await canvasToJpegBlob();
  lastPreparedFrameBlob = frameBlob;
  preparedFrameSource = "upload";

  updateFrameMeta(
    `Anh upload da duoc chuan hoa thanh JPEG 320x240: ${formatBytes(frameBlob.size)}`
  );
  setStatus(
    elements.streamStatus,
    "Anh da san sang. Bam Send frame de cap nhat last image tren server.",
    "ok"
  );
  setFrameButtonsState();
  logActivity(`Da nap anh "${file.name}" de test videoframe.`, "success");
}

async function sendFrameBlob(frameBlob, sourceLabel = "unknown") {
  const endpoint = buildEndpoint(
    elements.serverBaseUrl.value,
    elements.videoframePath.value
  );

  frameRequestInFlight = true;
  setStatus(elements.streamStatus, "Dang gui frame len server...", "busy");

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
    elements.frameCounter.textContent = String(streamedFrameCount);
    setStatus(
      elements.streamStatus,
      `Gui frame thanh cong. Last image tren server da duoc cap nhat tu ${sourceLabel}.`,
      "ok"
    );
    logActivity(
      `POST ${endpoint} thanh cong, frame ${streamedFrameCount}, payload ${formatBytes(frameBlob.size)}.`,
      "success"
    );
  } finally {
    frameRequestInFlight = false;
  }
}

async function captureAndSendFrame() {
  if (frameRequestInFlight) {
    return;
  }

  let frameBlob = lastPreparedFrameBlob;

  if (preparedFrameSource === "upload" && lastPreparedFrameBlob) {
    frameBlob = lastPreparedFrameBlob;
  } else if (cameraStream) {
    frameBlob = await prepareFrameFromCamera();
  }

  if (!frameBlob) {
    throw new Error("Chua co frame nao de gui");
  }

  await sendFrameBlob(frameBlob, preparedFrameSource || "frame");
}

function startAutoStream() {
  if (!cameraStream) {
    throw new Error("Can bat camera truoc khi auto stream");
  }

  if (autoStreamTimer) {
    return;
  }

  logActivity("Bat auto stream 10 FPS den /api/videoframe.", "info");
  setStatus(elements.streamStatus, "Dang auto stream 10 FPS...", "busy");

  autoStreamTimer = window.setInterval(async () => {
    if (!cameraStream || frameRequestInFlight) {
      return;
    }

    try {
      const frameBlob = await prepareFrameFromCamera();
      await sendFrameBlob(frameBlob, "camera");
    } catch (error) {
      stopAutoStream();
      setStatus(elements.streamStatus, `Auto stream loi: ${error.message}`, "error");
      logActivity(`Auto stream loi: ${error.message}`, "error");
    }
  }, AUTO_STREAM_INTERVAL_MS);
}

function stopAutoStream() {
  if (!autoStreamTimer) {
    return;
  }

  window.clearInterval(autoStreamTimer);
  autoStreamTimer = null;
  logActivity("Da dung auto stream.", "info");

  if (cameraStream) {
    setStatus(
      elements.streamStatus,
      "Auto stream da dung. Camera van san sang.",
      "idle"
    );
  }
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

  logActivity("Dang yeu cau microphone de ghi WAV.", "info");
  currentRequestAudioBlob = null;
  currentRequestAudioName = "";
  recordingStream = await navigator.mediaDevices.getUserMedia({
    audio: {
      channelCount: 1,
      echoCancellation: true,
      noiseSuppression: true,
    },
    video: false,
  });

  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass) {
    throw new Error("Trinh duyet khong ho tro Web Audio");
  }

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
  setRecordingIndicator("Dang ghi am...", "recording");
  setStatus(
    elements.recognizeStatus,
    "Dang ghi cau hoi. Bam Stop recording khi xong.",
    "busy"
  );
  setRecordingButtonsState();

  recordingTicker = window.setInterval(() => {
    const durationMs = Date.now() - recordingStartTime;
    updateAudioMeta(`Dang ghi: ${formatDurationMs(durationMs)}`);
  }, 200);

  logActivity("Da bat ghi am microphone.", "success");
}

async function stopRecording() {
  if (!isRecording) {
    return;
  }

  isRecording = false;

  if (recordingTicker) {
    window.clearInterval(recordingTicker);
    recordingTicker = null;
  }

  recordingProcessorNode?.disconnect();
  recordingSourceNode?.disconnect();
  recordingSilenceNode?.disconnect();

  recordingStream?.getTracks().forEach((track) => track.stop());
  recordingStream = null;

  await recordingContext?.close();

  const mergedSamples = mergeFloat32Buffers(recordingBuffers);
  if (!mergedSamples.length) {
    throw new Error("Khong thu duoc du lieu audio. Thu ghi am lai giup anh.");
  }

  const wavBlob = encodeWav(mergedSamples, recordingSampleRate);
  const durationMs = Date.now() - recordingStartTime;

  recordingContext = null;
  recordingSourceNode = null;
  recordingProcessorNode = null;
  recordingSilenceNode = null;
  recordingBuffers = [];

  currentRequestAudioBlob = wavBlob;
  currentRequestAudioName = `recorded-${Date.now()}.wav`;

  setRecordingIndicator("Da ghi xong.", "ready");
  updateAudioMeta(
    `WAV san sang: ${formatBytes(wavBlob.size)}, ${formatDurationMs(durationMs)}`
  );
  setStatus(
    elements.recognizeStatus,
    "Audio da san sang. Co the gui len /api/recognize.",
    "ok"
  );
  setRecordingButtonsState();
  logActivity("Da tao file WAV tu microphone.", "success");
}

async function useUploadedAudioFile(file) {
  if (!file) {
    return;
  }

  if (
    file.type !== "audio/wav" &&
    file.type !== "audio/x-wav" &&
    !file.name.toLowerCase().endsWith(".wav")
  ) {
    throw new Error("Chi chap nhan file WAV de test /api/recognize");
  }

  currentRequestAudioBlob = file;
  currentRequestAudioName = file.name;
  setRecordingIndicator("Da nap file WAV.", "ready");
  updateAudioMeta(`Da chon WAV: ${file.name} (${formatBytes(file.size)})`);
  setStatus(
    elements.recognizeStatus,
    "Audio upload da san sang. Co the gui len /api/recognize.",
    "ok"
  );
  setRecordingButtonsState();
  logActivity(`Da nap file WAV "${file.name}".`, "success");
}

async function sendRecognizeRequest() {
  if (!currentRequestAudioBlob) {
    throw new Error("Chua co audio WAV de gui");
  }

  const endpoint = buildEndpoint(
    elements.serverBaseUrl.value,
    elements.recognizePath.value
  );

  recognizeRequestInFlight = true;
  setRecordingButtonsState();
  setStatus(elements.recognizeStatus, "Dang gui audio len server...", "busy");

  try {
    const response = await fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "audio/wav",
      },
      body: currentRequestAudioBlob,
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
    elements.downloadResponseButton.disabled = false;

    updateResponseMeta(
      `Audio tra ve: ${formatBytes(currentResponseAudioBlob.size)} tu "${currentRequestAudioName}"`
    );
    setStatus(
      elements.recognizeStatus,
      "Nhan audio response thanh cong. Co the bam Play de nghe.",
      "ok"
    );
    logActivity(
      `POST ${endpoint} thanh cong, response ${formatBytes(currentResponseAudioBlob.size)}.`,
      "success"
    );
  } finally {
    recognizeRequestInFlight = false;
    setRecordingButtonsState();
  }
}

elements.startCameraButton.addEventListener("click", async () => {
  try {
    await startCamera();
  } catch (error) {
    setStatus(elements.streamStatus, `Khong mo duoc camera: ${error.message}`, "error");
    logActivity(`Khong mo duoc camera: ${error.message}`, "error");
  }
});

elements.stopCameraButton.addEventListener("click", () => {
  stopCamera();
});

elements.sendFrameButton.addEventListener("click", async () => {
  try {
    await captureAndSendFrame();
  } catch (error) {
    setStatus(elements.streamStatus, `Gui frame that bai: ${error.message}`, "error");
    logActivity(`Gui frame that bai: ${error.message}`, "error");
  }
});

elements.autoStreamCheckbox.addEventListener("change", () => {
  try {
    if (elements.autoStreamCheckbox.checked) {
      startAutoStream();
    } else {
      stopAutoStream();
    }
  } catch (error) {
    elements.autoStreamCheckbox.checked = false;
    setStatus(elements.streamStatus, `Khong bat duoc auto stream: ${error.message}`, "error");
    logActivity(`Khong bat duoc auto stream: ${error.message}`, "error");
  }
});

elements.imageFileInput.addEventListener("change", () => {
  setFrameButtonsState();
});

elements.uploadImageButton.addEventListener("click", async () => {
  try {
    const [file] = elements.imageFileInput.files;
    await prepareFrameFromUpload(file);
  } catch (error) {
    setStatus(elements.streamStatus, `Khong xu ly duoc anh: ${error.message}`, "error");
    logActivity(`Khong xu ly duoc anh: ${error.message}`, "error");
    resetPreparedFrame("upload");
  }
});

elements.recordButton.addEventListener("click", async () => {
  try {
    await startRecording();
  } catch (error) {
    setStatus(elements.recognizeStatus, `Khong ghi am duoc: ${error.message}`, "error");
    logActivity(`Khong ghi am duoc: ${error.message}`, "error");
  }
});

elements.stopRecordButton.addEventListener("click", async () => {
  try {
    await stopRecording();
  } catch (error) {
    setStatus(elements.recognizeStatus, `Khong dung ghi am duoc: ${error.message}`, "error");
    logActivity(`Khong dung ghi am duoc: ${error.message}`, "error");
  }
});

elements.audioFileInput.addEventListener("change", async () => {
  try {
    const [file] = elements.audioFileInput.files;
    await useUploadedAudioFile(file);
  } catch (error) {
    setStatus(elements.recognizeStatus, `Khong nap duoc WAV: ${error.message}`, "error");
    logActivity(`Khong nap duoc WAV: ${error.message}`, "error");
  }
});

elements.sendRecognizeButton.addEventListener("click", async () => {
  try {
    await sendRecognizeRequest();
  } catch (error) {
    setStatus(elements.recognizeStatus, `Recognize that bai: ${error.message}`, "error");
    logActivity(`Recognize that bai: ${error.message}`, "error");
  }
});

elements.downloadResponseButton.addEventListener("click", () => {
  if (!currentResponseAudioBlob) {
    return;
  }

  const downloadUrl = currentResponseAudioUrl || URL.createObjectURL(currentResponseAudioBlob);
  const anchor = document.createElement("a");
  anchor.href = downloadUrl;
  anchor.download = `recognize-response-${Date.now()}.wav`;
  anchor.click();
  logActivity("Da tai audio response xuong may.", "info");
});

window.addEventListener("beforeunload", () => {
  stopAutoStream();
  stopCamera();

  if (uploadedImageBitmap) {
    uploadedImageBitmap.close();
  }

  if (uploadedImagePreviewUrl) {
    URL.revokeObjectURL(uploadedImagePreviewUrl);
  }

  if (currentResponseAudioUrl) {
    URL.revokeObjectURL(currentResponseAudioUrl);
  }
});

setStatus(
  elements.streamStatus,
  "Chua ket noi camera. Co the upload anh hoac bat webcam de gui last image.",
  "idle"
);
setStatus(
  elements.recognizeStatus,
  "Chua co audio. Ghi am hoac chon file WAV roi gui len server.",
  "idle"
);
setRecordingIndicator("Chua ghi am.", "idle");
updateFrameMeta("Server se luu moi JPEG moi nhat thanh last image.");
updateAudioMeta("API recognize chi nhan audio/wav.");
updateResponseMeta("Audio response se xuat hien tai day sau khi recognize thanh cong.");
setFrameButtonsState();
setRecordingButtonsState();
logActivity("ESP simulator da san sang de test videoframe va recognize.", "success");
