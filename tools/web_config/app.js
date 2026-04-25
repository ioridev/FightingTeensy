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

const elements = {
  portSelect: document.querySelector("#portSelect"),
  status: document.querySelector("#status"),
  log: document.querySelector("#log"),
  sampleGrid: document.querySelector("#sampleGrid"),
  directionGrid: document.querySelector("#directionGrid"),
  buttonPinGrid: document.querySelector("#buttonPinGrid"),
  pinScan: document.querySelector("#pinScan"),
};

let monitorTimer = null;
let pinMonitorTimer = null;

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
        <div class="metric"><span>raw</span><span>${raw}</span></div>
        <div class="metric"><span>travel</span><span>${travel}</span></div>
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
      <button type="button" data-action="applyButtonPin" data-button="${button.key}">Apply</button>
    </article>
  `).join("");
}

function renderDirectionCards() {
  elements.directionGrid.innerHTML = directions.map((direction) => `
    <article class="direction-card" data-key="${direction.key}">
      <div class="direction-header">
        <h3>${direction.label}</h3>
        <button type="button" data-action="calBottom" data-key="${direction.key}">Cal Bottom</button>
      </div>
      <div class="direction-body">
        <label class="field">
          Press offset
          <input type="number" min="0" max="1023" step="1" data-field="press">
        </label>
        <label class="field">
          Release offset
          <input type="number" min="0" max="1023" step="1" data-field="release">
        </label>
        <label class="field">
          Rapid trigger offset
          <input type="number" min="0" max="1023" step="1" data-field="rapid">
        </label>
        <label class="field">
          Rest
          <input type="number" min="0" max="1023" step="1" data-field="rest">
        </label>
        <label class="field">
          Bottom
          <input type="number" min="0" max="1023" step="1" data-field="bottom">
        </label>
        <label class="check-row">
          <input type="checkbox" data-field="active_low">
          Active low
        </label>
        <div class="card-actions">
          <button type="button" data-action="apply" data-key="${direction.key}">Apply</button>
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
      setStatus(`Ready: ${selectedPort()}`);
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
  const data = await api("/api/sample", {});
  renderSamples(fieldsOf(data));
  return data;
}

async function scanPins() {
  const data = await api("/api/pins", {});
  renderPinScan(fieldsOf(data));
  return data;
}

async function save() {
  const data = await api("/api/save", {});
  log(data.response.text);
}

async function flashFirmware(target) {
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
    return;
  }
  pinMonitorTimer = setInterval(() => scanPins().catch(handleError), 120);
  button.textContent = "Stop Pins";
}

function toggleMonitor() {
  const button = document.querySelector("#monitor");
  if (monitorTimer) {
    clearInterval(monitorTimer);
    monitorTimer = null;
    button.textContent = "Monitor";
    return;
  }
  monitorTimer = setInterval(() => sample().catch(handleError), 150);
  button.textContent = "Stop";
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
  document.querySelector("#scanPins").addEventListener("click", () => scanPins().catch(handleError));
  document.querySelector("#monitorPins").addEventListener("click", () => togglePinMonitor());
  document.querySelector("#calRest").addEventListener("click", () => calRest().catch(handleError));
  document.querySelector("#clearLog").addEventListener("click", () => { elements.log.textContent = ""; });
  elements.buttonPinGrid.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    if (button.dataset.action === "applyButtonPin") {
      applyButtonPin(button.dataset.button).catch(handleError);
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
renderDirectionCards();
bindEvents();
refreshPorts();
