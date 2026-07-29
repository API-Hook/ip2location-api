const form = document.querySelector("#lookup-form");
const ipInput = document.querySelector("#ip-input");
const statusEl = document.querySelector("#status");
const resultCard = document.querySelector("#result-card");
const copyButton = document.querySelector("#copy-button");
const meButton = document.querySelector("#me-button");
const lookupButton = document.querySelector("#lookup-button");
const rawJson = document.querySelector("#raw-json");

let lastResult = null;

function setStatus(message, isError = false) {
  statusEl.textContent = message;
  statusEl.classList.toggle("error", isError);
}

function setLoading(isLoading) {
  lookupButton.disabled = isLoading;
  meButton.disabled = isLoading;
  setStatus(isLoading ? "Loading..." : "");
}

function valueOrDash(value) {
  return value === null || value === undefined || value === "" ? "-" : String(value);
}

function renderResult(result) {
  lastResult = result;
  resultCard.classList.remove("hidden");
  document.querySelector("#result-ip").textContent = result.ip;
  document.querySelector("#country-code").textContent = valueOrDash(result.countryCode);
  document.querySelector("#country-name").textContent = valueOrDash(result.countryName);
  document.querySelector("#region-name").textContent = valueOrDash(result.regionName);
  document.querySelector("#city-name").textContent = valueOrDash(result.cityName);
  document.querySelector("#latitude").textContent = valueOrDash(result.latitude);
  document.querySelector("#longitude").textContent = valueOrDash(result.longitude);
  document.querySelector("#ip-number").textContent = valueOrDash(result.ipNumber);
  document.querySelector("#ip-range").textContent = `${result.range.from} - ${result.range.to}`;
  rawJson.textContent = JSON.stringify(result, null, 2);
}

async function requestJson(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  const body = await response.json();
  if (!response.ok) {
    throw new Error(body.message || "Lookup failed.");
  }
  return body;
}

async function lookupIp(ip) {
  const normalized = ip.trim();
  if (!normalized) {
    setStatus("Enter an IPv4 address.", true);
    return;
  }
  if (normalized.length > 64) {
    setStatus("IP address is too long.", true);
    return;
  }

  setLoading(true);
  resultCard.classList.add("hidden");
  try {
    const result = await requestJson(`/api/v1/lookup?ip=${encodeURIComponent(normalized)}`);
    renderResult(result);
    setStatus("Lookup complete.");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    lookupButton.disabled = false;
    meButton.disabled = false;
  }
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  lookupIp(ipInput.value);
});

meButton.addEventListener("click", async () => {
  setLoading(true);
  resultCard.classList.add("hidden");
  try {
    const result = await requestJson("/api/v1/me");
    ipInput.value = result.ip;
    renderResult(result);
    setStatus("Lookup complete.");
  } catch (error) {
    setStatus(error.message, true);
  } finally {
    lookupButton.disabled = false;
    meButton.disabled = false;
  }
});

copyButton.addEventListener("click", async () => {
  if (!lastResult) {
    return;
  }
  await navigator.clipboard.writeText(JSON.stringify(lastResult, null, 2));
  setStatus("JSON copied.");
});

