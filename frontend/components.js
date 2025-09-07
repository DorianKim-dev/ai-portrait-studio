function SegmentedControl(root, options, onChange) {
  const current = { value: options[0].value };
  root.innerHTML = "";
  options.forEach((opt) => {
    const b = document.createElement("div");
    b.className = "seg";
    b.textContent = opt.label;
    b.dataset.value = opt.value;
    if (opt.value === current.value) b.classList.add("active");
    b.addEventListener("click", () => {
      current.value = opt.value;
      root.querySelectorAll(".seg").forEach((el) => el.classList.remove("active"));
      b.classList.add("active");
      onChange(current.value);
    });
    root.appendChild(b);
  });
  return () => current.value;
}

function Dropzone(root, inputEl, previewEl, onFile) {
  function setActive(v) {
    root.style.background = v ? "#14161b" : "";
  }
  function handleFiles(files) {
    if (!files || !files[0]) return;
    const file = files[0];
    const reader = new FileReader();
    reader.onload = () => {
      previewEl.src = reader.result;
      previewEl.style.display = "block";
      onFile(file, reader.result);
    };
    reader.readAsDataURL(file);
  }
  root.addEventListener("click", () => inputEl.click());
  root.addEventListener("dragover", (e) => { e.preventDefault(); setActive(true); });
  root.addEventListener("dragleave", () => setActive(false));
  root.addEventListener("drop", (e) => { e.preventDefault(); setActive(false); handleFiles(e.dataTransfer.files); });
  inputEl.addEventListener("change", (e) => handleFiles(e.target.files));
}

function Spinner(visible) {
  const el = document.getElementById("spinner");
  if (!el) return;
  el.hidden = !visible;
}

function setError(msg) {
  const el = document.getElementById("error");
  if (!el) return;
  if (msg) { el.textContent = msg; el.hidden = false; }
  else { el.textContent = ""; el.hidden = true; }
}

function setResultImage(dataUrl) {
  const container = document.getElementById("result");
  container.innerHTML = "";
  const img = document.createElement("img");
  img.src = dataUrl;
  container.appendChild(img);
}

function addToGallery(dataUrl) {
  const g = document.getElementById("gallery");
  const card = document.createElement("div");
  card.className = "thumb";
  const img = document.createElement("img");
  img.src = dataUrl;
  card.appendChild(img);
  g.prepend(card);
}

window.UI = { SegmentedControl, Dropzone, Spinner, setError, setResultImage, addToGallery };

// Camera helper
async function openCamera(videoEl) {
  const stream = await navigator.mediaDevices.getUserMedia({
    video: {
      facingMode: 'user',
      width: { ideal: 1280 },
      height: { ideal: 720 }
    },
    audio: false
  });
  videoEl.srcObject = stream;
  await videoEl.play();
  return stream;
}

function closeCamera(stream, videoEl) {
  if (stream) stream.getTracks().forEach(t => t.stop());
  if (videoEl) videoEl.srcObject = null;
}

function captureFrame(videoEl, canvasEl, mirror=false) {
  let w = videoEl.videoWidth || 640;
  let h = videoEl.videoHeight || 480;
  // Downscale for speed if very large (keep aspect)
  const MAX_W = 1280;
  if (w > MAX_W) {
    const s = MAX_W / w;
    w = Math.round(w * s);
    h = Math.round(h * s);
  }
  canvasEl.width = w; canvasEl.height = h;
  const ctx = canvasEl.getContext('2d');
  if (mirror) {
    ctx.translate(w, 0);
    ctx.scale(-1, 1);
  }
  ctx.drawImage(videoEl, 0, 0, w, h);
  // Prefer JPEG to reduce payload size and latency
  const dataUrl = canvasEl.toDataURL('image/jpeg', 0.9);
  const [prefix, b64] = dataUrl.split(',');
  return { mime: 'image/jpeg', base64: b64, dataUrl };
}

window.Camera = { openCamera, closeCamera, captureFrame };
