const directions = [
  { key: "up", index: 0, label: "Up" },
  { key: "down", index: 1, label: "Down" },
  { key: "left", index: 2, label: "Left" },
  { key: "right", index: 3, label: "Right" },
];

const buttons = [
  { key: "a", label: "A" },
  { key: "b", label: "B" },
  { key: "x", label: "X" },
  { key: "y", label: "Y" },
  { key: "lb", label: "LB" },
  { key: "rb", label: "RB" },
  { key: "back", label: "Back" },
  { key: "start", label: "Start" },
  { key: "l3", label: "L3" },
  { key: "r3", label: "R3" },
  { key: "logo", label: "Home" },
  { key: "lt", label: "LT" },
  { key: "rt", label: "RT" },
];

const testerButtons = [
  { key: "x", label: "X", row: 1, col: 1 },
  { key: "y", label: "Y", row: 1, col: 2 },
  { key: "rb", label: "RB", row: 1, col: 3 },
  { key: "rt", label: "RT", row: 1, col: 4 },
  { key: "a", label: "A", row: 2, col: 1 },
  { key: "b", label: "B", row: 2, col: 2 },
  { key: "lb", label: "LB", row: 2, col: 3 },
  { key: "lt", label: "LT", row: 2, col: 4 },
  { key: "back", label: "Back", row: 3, col: 1 },
  { key: "start", label: "Start", row: 3, col: 2 },
  { key: "logo", label: "Home", row: 3, col: 3 },
  { key: "l3", label: "L3", row: 3, col: 4 },
  { key: "r3", label: "R3", row: 3, col: 5 },
];

const elements = {
  portSelect: document.querySelector("#portSelect"),
  status: document.querySelector("#status"),
  log: document.querySelector("#log"),
  sampleGrid: document.querySelector("#sampleGrid"),
  directionGrid: document.querySelector("#directionGrid"),
  buttonPinGrid: document.querySelector("#buttonPinGrid"),
  pinScan: document.querySelector("#pinScan"),
  arcadeTester: document.querySelector("#arcadeTester"),
  monitorState: document.querySelector("#monitorState"),
};

let monitorTimer = null;
let pinMonitorTimer = null;
let buttonMonitorTimer = null;
let latestPressedPins = [];
let sampleBusy = false;
let pinScanBusy = false;
let buttonSampleBusy = false;

function selectedPort() {
  return elements.portSelect.value;
}

function setStatus(text, ok = true) {
  elements.status.textContent = text;
  elements.status.className = ok ? "ok" : "error";
}

function log(text) {
  const stamp = new Date().toLocaleTimeString();
  elements.log.textContent = `[${stamp}] ${text}\n${elements.log.textContent}`;
}

function isAnyMonitorRunning() {
  return Boolean(monitorTimer || pinMonitorTimer || buttonMonitorTimer);
}

function updateMonitorState() {
  if (!elements.monitorState) return;
  if (isAnyMonitorRunning()) {
    elements.monitorState.textContent = "Monitor running: serial is busy";
    elements.monitorState.classList.add("busy");
  } else {
    elements.monitorState.textContent = "Monitor stopped";
    elements.monitorState.classList.remove("busy");
  }
}

function stopAllMonitors() {
  const hallButton = document.querySelector("#monitor");
  const pinButton = document.querySelector("#monitorPins");
  const buttonTester = document.querySelector("#monitorButtons");

  if (monitorTimer) {
    clearInterval(monitorTimer);
    monitorTimer = null;
  }
  if (pinMonitorTimer) {
    clearInterval(pinMonitorTimer);
    pinMonitorTimer = null;
  }
  if (buttonMonitorTimer) {
    clearInterval(buttonMonitorTimer);
    buttonMonitorTimer = null;
  }

  if (hallButton) hallButton.textContent = "Monitor";
  if (pinButton) pinButton.textContent = "Monitor Pins";
  if (buttonTester) buttonTester.textContent = "Monitor Buttons";
  updateMonitorState();
}

async function api(path, payload = null) {
  const options = payload === null
    ? {}
    : {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ port: selectedPort(), ...payload }),
      };
  const response = await fetch(path, options);
  const data = await response.json();
  if (!data.ok) {
    throw new Error(data.error || "request failed");
  }
  return data;
}

function fieldsOf(data) {
  return data.response ? data.response.fields : {};
}

function renderSamples(fields = {}) {
  elements.sampleGrid.innerHTML = directions.map((direction) => {
    const raw = fields[`key${direction.index}_raw`] ?? "-";
    const travel = fields[`key${direction.index}_travel`] ?? "-";
    return `
      <div class="sample-card">
        <strong>${direction.label}</strong>
        <div class="metric"><span>Raw</span><span>${raw}</span></div>
        <div class="metric"><span>Travel</span><span>${travel}</span></div>
      </div>
    `;
  }).join("");
}

function renderButtonPins() {
  elements.buttonPinGrid.innerHTML = buttons.map((button) => `
    <article class="button-pin-card" data-button="${button.key}">
      <label class="field">
        ${button.label}
        <input type="number" min="0" max="33" step="1" data-field="pin">
      </label>
      <div class="button-pin-actions">
        <button type="button" data-action="usePressedPin" data-button="${button.key}">Use Pressed</button>
        <button type="button" data-action="applyButtonPin" data-button="${button.key}">Apply</button>
      </div>
    </article>
  `).join("");
}

function renderArcadeTester(fields = {}) {
  const active = (key) => fields[key] === "1";
  elements.arcadeTester.innerHTML = `
    <div class="stick-area" aria-label="D-pad tester">
      <div></div>
      <div class="tester-direction ${active("up") ? "active" : ""}" data-button="up">Up</div>
      <div></div>
      <div class="tester-direction ${active("left") ? "active" : ""}" data-button="left">Left</div>
      <div class="stick-center"></div>
      <div class="tester-direction ${active("right") ? "active" : ""}" data-button="right">Right</div>
      <div></div>
      <div class="tester-direction ${active("down") ? "active" : ""}" data-button="down">Down</div>
      <div></div>
    </div>
    <div class="face-area" aria-label="XInput button tester">
      ${testerButtons.map((button) => `
        <div
          class="tester-button ${active(button.key) ? "active" : ""}"
          data-button="${button.key}"
          style="grid-row:${button.row};grid-column:${button.col};"
        >${button.label}</div>
      `).join("")}
    </div>
  `;
}

function renderDirectionCards() {
  elements.directionGrid.innerHTML = directions.map((direction) => `
    <article class="direction-card" data-key="${direction.key}">
      <div class="direction-header">
        <h3>${direction.label}</h3>
        <button type="button" data-action="calBottom" data-key="${direction.key}">Calibrate Pressed</button>
      </div>
      <div class="direction-body">
        <label class="field">
          Idle ADC
          <input type="number" min="0" max="1023" step="1" data-field="rest">
        </label>
        <label class="field">
          Pressed ADC
          <input type="number" min="0" max="1023" step="1" data-field="bottom">
        </label>
        <label class="field">
          Activation Offset
          <input type="number" min="0" max="1023" step="1" data-field="press">
        </label>
        <label class="field">
          Rapid Release Offset
          <input type="number" min="0" max="1023" step="1" data-field="release">
        </label>
        <label class="field">
          Rapid Noise Filter
          <input type="number" min="0" max="1023" step="1" data-field="rapid">
        </label>
        <label class="check-row">
          <input type="checkbox" data-field="active_low">
          Flip Polarity
        </label>
        <div class="card-actions">
          <button type="button" data-action="apply" data-key="${direction.key}">Apply Trigger Values</button>
          <button type="button" data-action="sampleOne" data-key="${direction.key}">Sample</button>
        </div>
      </div>
    </article>
  `).join("");
}

function cardFor(key) {
  return document.querySelector(`.direction-card[data-key="${key}"]`);
}

function buttonCardFor(key) {
  return document.querySelector(`.button-pin-card[data-button="${key}"]`);
}

function applySettings(fields) {
  for (const direction of directions) {
    const card = cardFor(direction.key);
    if (!card) continue;
    for (const field of ["press", "release", "rapid", "rest", "bottom"]) {
      const input = card.querySelector(`[data-field="${field}"]`);
      input.value = fields[`key${direction.index}_${field}`] ?? "";
    }
    const activeLow = card.querySelector('[data-field="active_low"]');
    activeLow.checked = fields[`key${direction.index}_active_low`] === "1";
  }
  for (const button of buttons) {
    const card = buttonCardFor(button.key);
    if (!card) continue;
    const input = card.querySelector('[data-field="pin"]');
    input.value = fields[`btn_${button.key}_pin`] ?? "";
  }
}

function payloadForCard(key) {
  const card = cardFor(key);
  const payload = { key };
  for (const field of ["press", "release", "rapid", "rest", "bottom"]) {
    const value = card.querySelector(`[data-field="${field}"]`).value;
    if (value !== "") {
      payload[field] = Number(value);
    }
  }
  payload.active_low = card.querySelector('[data-field="active_low"]').checked ? 1 : 0;
  return payload;
}

function payloadForButtonPin(key) {
  const card = buttonCardFor(key);
  const value = card.querySelector('[data-field="pin"]').value;
  return { button: key, pin: Number(value) };
}

function payloadForButtonPins() {
  const buttonPins = {};
  for (const button of buttons) {
    const card = buttonCardFor(button.key);
    const value = card.querySelector('[data-field="pin"]').value;
    buttonPins[button.key] = Number(value);
  }
  return { button_pins: buttonPins };
}

function usePressedPinForButton(key) {
  if (latestPressedPins.length !== 1) {
    throw new Error("press exactly one button, then scan pins");
  }
  const card = buttonCardFor(key);
  card.querySelector('[data-field="pin"]').value = latestPressedPins[0];
  log(`${key} pin set to ${latestPressedPins[0]} from scan`);
}

async function scanAndUsePressedPinForButton(key) {
  const data = await scanPins();
  if (data === null) {
    throw new Error("pin scan is already running");
  }
  usePressedPinForButton(key);
}

function labelForPin(pin) {
  const matched = buttons.find((button) => {
    const card = buttonCardFor(button.key);
    return card && card.querySelector('[data-field="pin"]').value === String(pin);
  });
  return matched ? matched.label : "";
}

function renderPinScan(fields = {}) {
  const pressed = Object.entries(fields)
    .filter(([key, value]) => key.startsWith("pin") && value === "1")
    .map(([key]) => Number(key.substring(3)))
    .sort((a, b) => a - b);
  latestPressedPins = pressed;

  if (pressed.length === 0) {
    elements.pinScan.innerHTML = '<span class="muted">No pressed pins</span>';
    return;
  }

  elements.pinScan.innerHTML = pressed.map((pin) => {
    const label = labelForPin(pin);
    return `<span class="pin-chip">Pin ${pin}${label ? ` · ${label}` : ""}</span>`;
  }).join("");
}

async function refreshPorts() {
  try {
    const data = await api("/api/ports");
    elements.portSelect.innerHTML = data.ports.map((port) => {
      const label = `${port.device} - ${port.description || ""}`.trim();
      return `<option value="${port.device}">${label}</option>`;
    }).join("");
    if (data.ports.length === 0) {
      elements.portSelect.innerHTML = '<option value="">No serial ports</option>';
      setStatus("No serial ports", false);
    } else {
      const teensyPort = data.ports.find((port) => String(port.hwid || "").toUpperCase().includes("VID:PID=16C0:0483"));
      if (teensyPort) {
        elements.portSelect.value = teensyPort.device;
        setStatus(`Ready: ${selectedPort()}`);
        loadSettings().catch(handleError);
      } else {
        setStatus("Teensy serial not found", false);
        log("Teensy serial port not found. Use config firmware mode, then Refresh Ports.");
      }
    }
  } catch (error) {
    setStatus(error.message, false);
    log(error.message);
  }
}

async function ping() {
  const data = await api("/api/ping", {});
  setStatus(data.response.text);
  log(data.response.text);
}

async function loadSettings() {
  const data = await api("/api/settings", {});
  applySettings(fieldsOf(data));
  log(data.response.text);
}

async function sample() {
  if (sampleBusy) return null;
  sampleBusy = true;
  try {
  const data = await api("/api/sample", {});
  renderSamples(fieldsOf(data));
  return data;
  } finally {
    sampleBusy = false;
  }
}

async function scanPins() {
  if (pinScanBusy) return null;
  pinScanBusy = true;
  try {
  const data = await api("/api/pins", {});
  renderPinScan(fieldsOf(data));
  return data;
  } finally {
    pinScanBusy = false;
  }
}

async function sampleButtons() {
  if (buttonSampleBusy) return null;
  buttonSampleBusy = true;
  try {
  const data = await api("/api/buttons", {});
  renderArcadeTester(fieldsOf(data));
  return data;
  } finally {
    buttonSampleBusy = false;
  }
}

async function save() {
  stopAllMonitors();
  const data = await api("/api/save", {});
  log(data.response.text);
}

async function flashFirmware(target) {
  stopAllMonitors();
  setStatus(`Flashing ${target}...`);
  log(`flash ${target} started`);
  const data = await api("/api/flash", { target });
  log(data.flash.log || `flash ${target} done`);
  setStatus(`Flashed ${target}`);
  await refreshPorts();
}

async function calRest() {
  const data = await api("/api/calibrate", { point: "rest" });
  log(data.response.text);
  await sample();
  await loadSettings();
}

async function calBottom(key) {
  const data = await api("/api/calibrate", { key, point: "bottom" });
  log(data.response.text);
  await loadSettings();
}

async function applyCard(key) {
  const data = await api("/api/set", payloadForCard(key));
  log(`${key}: ${data.response.text}`);
}

async function applyButtonPin(key) {
  const data = await api("/api/set", payloadForButtonPin(key));
  log(`${key} pin: ${data.response.text}`);
}

async function applyButtonPins() {
  const data = await api("/api/set", payloadForButtonPins());
  log(`button pins: ${data.response.text}`);
}

function handleError(error) {
  setStatus(error.message, false);
  log(`ERROR ${error.message}`);
}

function togglePinMonitor() {
  const button = document.querySelector("#monitorPins");
  if (pinMonitorTimer) {
    clearInterval(pinMonitorTimer);
    pinMonitorTimer = null;
    button.textContent = "Monitor Pins";
    updateMonitorState();
    return;
  }
  pinMonitorTimer = setInterval(() => scanPins().catch(handleError), 120);
  button.textContent = "Stop Pins";
  updateMonitorState();
}

function toggleButtonMonitor() {
  const button = document.querySelector("#monitorButtons");
  if (buttonMonitorTimer) {
    clearInterval(buttonMonitorTimer);
    buttonMonitorTimer = null;
    button.textContent = "Monitor Buttons";
    updateMonitorState();
    return;
  }
  buttonMonitorTimer = setInterval(() => sampleButtons().catch(handleError), 50);
  button.textContent = "Stop Buttons";
  updateMonitorState();
}

function toggleMonitor() {
  const button = document.querySelector("#monitor");
  if (monitorTimer) {
    clearInterval(monitorTimer);
    monitorTimer = null;
    button.textContent = "Monitor";
    updateMonitorState();
    return;
  }
  monitorTimer = setInterval(() => sample().catch(handleError), 150);
  button.textContent = "Stop";
  updateMonitorState();
}

function bindEvents() {
  document.querySelector("#refreshPorts").addEventListener("click", () => refreshPorts());
  document.querySelector("#ping").addEventListener("click", () => ping().catch(handleError));
  document.querySelector("#load").addEventListener("click", () => loadSettings().catch(handleError));
  document.querySelector("#save").addEventListener("click", () => save().catch(handleError));
  document.querySelector("#flashConfig").addEventListener("click", () => flashFirmware("config").catch(handleError));
  document.querySelector("#returnXinput").addEventListener("click", () => flashFirmware("xinput").catch(handleError));
  document.querySelector("#sample").addEventListener("click", () => sample().catch(handleError));
  document.querySelector("#monitor").addEventListener("click", () => toggleMonitor());
  document.querySelector("#sampleButtons").addEventListener("click", () => sampleButtons().catch(handleError));
  document.querySelector("#monitorButtons").addEventListener("click", () => toggleButtonMonitor());
  document.querySelector("#stopAllMonitors").addEventListener("click", () => stopAllMonitors());
  document.querySelector("#scanPins").addEventListener("click", () => scanPins().catch(handleError));
  document.querySelector("#monitorPins").addEventListener("click", () => togglePinMonitor());
  document.querySelector("#applyButtonPins").addEventListener("click", () => applyButtonPins().catch(handleError));
  document.querySelector("#calRest").addEventListener("click", () => calRest().catch(handleError));
  document.querySelector("#clearLog").addEventListener("click", () => { elements.log.textContent = ""; });
  elements.buttonPinGrid.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    if (button.dataset.action === "applyButtonPin") {
      applyButtonPin(button.dataset.button).catch(handleError);
    }
    if (button.dataset.action === "usePressedPin") {
      scanAndUsePressedPinForButton(button.dataset.button).catch(handleError);
    }
  });
  elements.directionGrid.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    const action = button.dataset.action;
    const key = button.dataset.key;
    if (action === "calBottom") calBottom(key).catch(handleError);
    if (action === "apply") applyCard(key).catch(handleError);
    if (action === "sampleOne") sample().catch(handleError);
  });
}

renderSamples();
renderPinScan();
renderButtonPins();
renderArcadeTester();
renderDirectionCards();
bindEvents();
refreshPorts();
