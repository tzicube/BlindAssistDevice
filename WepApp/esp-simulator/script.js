const MODE_LABELS = {
  object_search: "Object Search",
  conversation_mode: "Conversation",
  mobility_mode: "Mobility",
};

const MODE_MESSAGES = {
  object_search: "Dang yeu cau server tra audio cho che do tim do vat.",
  conversation_mode: "Dang yeu cau server tra audio cho che do hoi thoai.",
  mobility_mode: "Dang yeu cau server tra audio cho che do di chuyen.",
};

const MODE_ENDPOINT = "http://localhost:8765/mode";

const statusText = document.getElementById("statusText");
const serverText = document.getElementById("serverText");
const lastModeText = document.getElementById("lastModeText");
const displayTitle = document.getElementById("displayTitle");
const displayText = document.getElementById("displayText");
const statusLamp = document.getElementById("statusLamp");
const boardLed = document.getElementById("boardLed");
const audioPlayer = document.getElementById("audioPlayer");
const replayButton = document.getElementById("replayButton");
const allButtons = document.querySelectorAll("[data-mode]");

let currentAudioUrl = null;
let audioContext = null;
let audioGainNode = null;
let currentSource = null;
let playbackToken = 0;
let lastAudioBlob = null;
let lastModeLabel = "";

serverText.textContent = MODE_ENDPOINT;
audioPlayer.volume = 1;

function setActiveMode(mode) {
  allButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.mode === mode);
  });
}

function setStatus(message, state = "idle") {
  statusText.textContent = message;
  statusLamp.classList.remove("is-busy", "is-error");
  boardLed.classList.remove("bg-amber-300", "bg-rose-400");
  boardLed.classList.add("bg-emerald-300");

  if (state === "busy") {
    statusLamp.classList.add("is-busy");
    boardLed.classList.remove("bg-emerald-300");
    boardLed.classList.add("bg-amber-300");
  }

  if (state === "error") {
    statusLamp.classList.add("is-error");
    boardLed.classList.remove("bg-emerald-300");
    boardLed.classList.add("bg-rose-400");
  }
}

async function ensureAudioReady() {
  if (!audioContext) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext;

    if (!AudioContextClass) {
      throw new Error("Trinh duyet khong ho tro Web Audio");
    }

    audioContext = new AudioContextClass();
    audioGainNode = audioContext.createGain();
    audioGainNode.gain.value = 1.6;
    audioGainNode.connect(audioContext.destination);
  }

  if (audioContext.state === "suspended") {
    await audioContext.resume();
  }
}

function unlockAudio() {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;

  if (!AudioContextClass) {
    return;
  }

  if (!audioContext) {
    audioContext = new AudioContextClass();
    audioGainNode = audioContext.createGain();
    audioGainNode.gain.value = 1.6;
    audioGainNode.connect(audioContext.destination);
  }

  if (audioContext.state === "suspended") {
    audioContext.resume();
  }

  const buffer = audioContext.createBuffer(1, 1, 22050);
  const source = audioContext.createBufferSource();
  source.buffer = buffer;
  source.connect(audioGainNode);
  source.start(0);
}

function stopCurrentAudio() {
  if (currentSource) {
    currentSource.onended = null;
    try {
      currentSource.stop();
    } catch (error) {
    }
    currentSource.disconnect();
    currentSource = null;
  }

  audioPlayer.pause();
  audioPlayer.currentTime = 0;
}

async function playAudioBlob(audioBlob, label, token) {
  await ensureAudioReady();

  const arrayBuffer = await audioBlob.arrayBuffer();
  const audioBuffer = await audioContext.decodeAudioData(arrayBuffer.slice(0));

  stopCurrentAudio();

  const source = audioContext.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(audioGainNode);
  source.onended = () => {
    if (currentSource === source) {
      currentSource = null;
    }

    if (token !== playbackToken) {
      return;
    }

    setStatus(`Phat xong audio cho mode ${label}.`);
    displayText.textContent = "ESP32 simulator dang cho ban chon mode khac.";
  };

  currentSource = source;
  currentSource.start(0);
  lastAudioBlob = audioBlob;
  lastModeLabel = label;
  replayButton.disabled = false;

  if (currentAudioUrl) {
    URL.revokeObjectURL(currentAudioUrl);
  }

  currentAudioUrl = URL.createObjectURL(audioBlob);
  audioPlayer.src = currentAudioUrl;
  audioPlayer.load();
}

async function playMode(mode) {
  const label = MODE_LABELS[mode] || mode;
  const token = Date.now();

  playbackToken = token;

  setActiveMode(mode);
  setStatus(`Dang ket noi toi server cho mode ${label}...`, "busy");
  lastModeText.textContent = label;
  displayTitle.textContent = label;
  displayText.textContent = MODE_MESSAGES[mode] || "Dang cho audio tra ve tu server.";

  try {
    await ensureAudioReady();

    const response = await fetch(MODE_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        type: "mode_request",
        mode,
      }),
    });

    const contentType = response.headers.get("content-type") || "";

    if (!response.ok || !contentType.includes("audio/wav")) {
      let message = `Server error: ${response.status}`;

      if (contentType.includes("application/json")) {
        const errorData = await response.json();
        message = errorData.message || message;
      }

      throw new Error(message);
    }

    const audioBlob = await response.blob();
    await playAudioBlob(audioBlob, label, token);

    setStatus(`Dang phat audio cho mode ${label}.`);
    displayText.textContent = "Audio da nhan thanh cong va dang phat truc tiep tu server.";
  } catch (error) {
    setStatus(`Loi: ${error.message}`, "error");
    displayText.textContent = "Khong phat duoc audio. Hay kiem tra server co dang chay o cong 8765 khong.";
  }
}

allButtons.forEach((button) => {
  button.addEventListener("click", () => {
    unlockAudio();
    playMode(button.dataset.mode);
  });
});

replayButton.addEventListener("click", async () => {
  if (!lastAudioBlob) {
    return;
  }

  const token = Date.now();
  playbackToken = token;
  unlockAudio();

  try {
    await playAudioBlob(lastAudioBlob, lastModeLabel, token);
    setStatus(`Dang phat lai audio cho mode ${lastModeLabel}.`);
    displayText.textContent = "Dang phat lai audio vua nhan duoc tu server.";
  } catch (error) {
    setStatus(`Loi: ${error.message}`, "error");
  }
});
