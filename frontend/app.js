(function(){
  console.log('App.js starting. UI available:', typeof window.UI);
  const dz = document.getElementById('dropzone');
  const input = document.getElementById('fileInput');
  const preview = document.getElementById('preview');
  console.log('DOM elements:', {
    dropzone: !!dz,
    fileInput: !!input,
    preview: !!preview,
    themeButtons: document.querySelectorAll('[data-theme]').length
  });
  
  const quickButtons = Array.from(document.querySelectorAll('[data-theme]'));
  const dlBtn = document.getElementById('downloadBtn');
  const savedLink = document.getElementById('savedLink');
  const genderSeg = document.getElementById('genderSeg');

  // Camera controls
  const v = document.getElementById('camVideo');
  const c = document.getElementById('camCanvas');
  const openCam = document.getElementById('openCam');
  const shotCam = document.getElementById('shotCam');
  const closeCam = document.getElementById('closeCam');
  const mirrorToggle = document.getElementById('mirrorToggle');
  let camStream = null;

  let selectedTheme = 'resume';
  let uploaded = null; // { mime, base64Data (no prefix) }
  let lastResult = null; // { dataUrl, saved_url }
  let genderPresentation = 'auto';
  // composite feature removed
  let shotsCount = 1;
  let isBusy = false; // prevent concurrent requests

  // Remove segmented control usage; rely on quick buttons only

  UI.Dropzone(dz, input, preview, (file, dataUrl) => {
    const [prefix, b64] = dataUrl.split(',');
    const mime = (prefix.match(/data:(.*);base64/) || [])[1] || 'image/png';
    uploaded = { mime, base64: b64 };
    UI.setError(null);
  });

  // Camera events
  openCam.addEventListener('click', async () => {
    try {
      camStream = await Camera.openCamera(v);
      openCam.disabled = true; shotCam.disabled = false; closeCam.disabled = false;
    } catch (e) {
      UI.setError('카메라 접근을 허용해 주세요.');
    }
  });
  closeCam.addEventListener('click', () => {
    Camera.closeCamera(camStream, v);
    camStream = null;
    openCam.disabled = false; shotCam.disabled = true; closeCam.disabled = true;
  });
  shotCam.addEventListener('click', () => {
    if (!camStream) return;
    const cap = Camera.captureFrame(v, c, !!mirrorToggle?.checked);
    // Set preview & uploaded
    preview.src = cap.dataUrl;
    preview.style.display = 'block';
    uploaded = { mime: cap.mime, base64: cap.base64 };
    UI.setError(null);
  });

  // Mirror toggle affects video preview only; capture respects it via argument
  if (mirrorToggle) {
    mirrorToggle.addEventListener('change', () => {
      if (mirrorToggle.checked) v.classList.add('mirror');
      else v.classList.remove('mirror');
    });
    // default: non-mirror
    v.classList.remove('mirror');
  }

  let API_BASE = window.API_BASE || null;

  async function fetchWithTimeout(resource, options = {}, timeout = 30000) {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);
    try {
      const resp = await fetch(resource, { ...options, signal: controller.signal });
      return resp;
    } finally {
      clearTimeout(id);
    }
  }

  // Resolve API base: query override -> window -> 8001 -> 8000
  async function resolveApiBase() {
    const url = new URL(window.location.href);
    const qApi = url.searchParams.get('api');
    const candidates = [];
    if (qApi) candidates.push(qApi);
    if (window.API_BASE) candidates.push(window.API_BASE);
    candidates.push('http://localhost:8001');
    candidates.push('http://localhost:8000');

    for (const base of candidates) {
      try {
        const r = await fetchWithTimeout(`${base}/health`, {}, 3000);
        if (r.ok) {
          API_BASE = base;
          return base;
        }
      } catch {}
    }
    return null;
  }

  (async () => {
    const base = await resolveApiBase();
    if (!base) {
      UI.setError('백엔드 API에 연결할 수 없습니다. 서버가 8001 또는 8000 포트에서 실행 중인지 확인하세요. 또는 ?api=로 주소를 지정하세요.');
      // Disable theme buttons if API is unreachable
      quickButtons.forEach(b => b.disabled = true);
    }
  })();

  // Category filter
  const chips = document.getElementById('categoryChips');
  function applyCategory(cat){
    document.querySelectorAll('#categoryChips .chip').forEach(c=>c.classList.remove('active'));
    const active = document.querySelector(`#categoryChips .chip[data-cat="${cat}"]`);
    if (active) active.classList.add('active');
    const all = document.querySelectorAll('#themeButtons [data-theme]');
    all.forEach(btn => {
      const bcat = btn.getAttribute('data-cat') || 'essentials';
      const show = (cat === 'all') || (bcat === cat);
      btn.style.display = show ? '' : 'none';
    });
  }
  if (chips) {
    chips.addEventListener('click', (e) => {
      const t = e.target;
      if (t && t.classList.contains('chip')) {
        const cat = t.getAttribute('data-cat') || 'all';
        applyCategory(cat);
      }
    });
    applyCategory('essentials');
  }

  async function callGenerate(themeOverride) {
    if (isBusy) return;
    if (!uploaded) { UI.setError('먼저 사진을 준비해 주세요.'); return; }
    UI.Spinner(true);
    isBusy = true;
    UI.setError(null);
    try {
      // live mode only (demo disabled)
      const theme = themeOverride || selectedTheme;
      const options = {};
      if (genderPresentation && genderPresentation !== 'auto') {
        options.gender_presentation = genderPresentation;
      }
      if (shotsCount && shotsCount > 1) {
        options.shots = Math.min(3, Math.max(1, shotsCount));
      }
      // temporarily disable theme buttons to avoid burst clicks
      quickButtons.forEach(b => b.disabled = true);
      const resp = await fetchWithTimeout(`${API_BASE}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ theme, image: uploaded.base64, mime_type: uploaded.mime, options }),
      }, 60000);
      if (!resp.ok) {
        const text = await resp.text();
        throw new Error(text || 'Request failed');
      }
      const data = await resp.json();
      if (Array.isArray(data.images) && data.images.length > 0) {
        // Show first, add all to gallery
        const first = data.images[0];
        const firstUrl = `data:${first.mime_type || 'image/png'};base64,${first.image_base64}`;
        UI.setResultImage(firstUrl);
        lastResult = { dataUrl: firstUrl, saved_url: first.saved_url };
        data.images.forEach((im, i) => {
          const u = `data:${im.mime_type || 'image/png'};base64,${im.image_base64}`;
          UI.addToGallery(u);
        });
        if (dlBtn) dlBtn.disabled = false;
        if (savedLink) {
          savedLink.textContent = first.saved_url ? '파일 열기' : '';
          savedLink.href = first.saved_url && API_BASE ? `${API_BASE}${first.saved_url}` : '';
        }
      } else {
        const dataUrl = `data:${data.mime_type || 'image/png'};base64,${data.image_base64}`;
        UI.setResultImage(dataUrl);
        UI.addToGallery(dataUrl);
        lastResult = { dataUrl, saved_url: data.saved_url };
        if (dlBtn) dlBtn.disabled = false;
        if (savedLink) {
          savedLink.textContent = data.saved_url ? '파일 열기' : '';
          savedLink.href = data.saved_url && API_BASE ? `${API_BASE}${data.saved_url}` : '';
        }
      }
    } catch (e) {
      UI.setError(e.message || 'Unexpected error');
    } finally {
      UI.Spinner(false);
      isBusy = false;
      quickButtons.forEach(b => b.disabled = false);
    }
  }

  // Floating warning tooltip
  let warnTimer = null;
  function showHoverWarn(message, x, y) {
    let el = document.getElementById('hoverWarn');
    if (!el) {
      el = document.createElement('div');
      el.id = 'hoverWarn';
      el.className = 'warn-tooltip';
      document.body.appendChild(el);
    }
    el.textContent = message;
    el.style.left = `${x}px`;
    el.style.top = `${y}px`;
    el.style.display = 'block';
    if (warnTimer) clearTimeout(warnTimer);
    warnTimer = setTimeout(() => { el.style.display = 'none'; }, 1800);
  }

  quickButtons.forEach(btn => {
    btn.addEventListener('click', (e) => {
      selectedTheme = btn.dataset.theme;
      // visual active state
      quickButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      if (!uploaded) {
        showHoverWarn('먼저 사진을 업로드/촬영해 주세요', e.clientX, e.clientY);
        return;
      }
      callGenerate(selectedTheme);
    });
  });

  if (genderSeg) {
    genderSeg.querySelectorAll('[data-gender]').forEach(b => {
      b.addEventListener('click', () => {
        genderPresentation = b.dataset.gender;
        genderSeg.querySelectorAll('[data-gender]').forEach(x => x.classList.remove('active'));
        b.classList.add('active');
      });
    });
    // default active
    const autoBtn = genderSeg.querySelector('[data-gender="auto"]');
    if (autoBtn) autoBtn.classList.add('active');
  }

  // Shots segmented control (1/2/3)
  const shotsSeg = document.getElementById('shotsSeg');
  if (shotsSeg) {
    shotsSeg.querySelectorAll('[data-shots]').forEach(b => {
      b.addEventListener('click', () => {
        shotsCount = parseInt(b.dataset.shots || '1', 10);
        shotsSeg.querySelectorAll('[data-shots]').forEach(x => x.classList.remove('active'));
        b.classList.add('active');
      });
    });
    const one = shotsSeg.querySelector('[data-shots="1"]');
    if (one) one.classList.add('active');
  }

  // composite feature removed

  // Download
  if (dlBtn) {
    dlBtn.addEventListener('click', () => {
      if (!lastResult) return;
      const a = document.createElement('a');
      a.href = lastResult.dataUrl;
      a.download = `portrait_${Date.now()}.png`;
      a.click();
    });
  }

  // App initialization complete - hide spinner
  console.log('App initialized successfully');
  UI.Spinner(false);

  // Image Lightbox
  const lightbox = document.getElementById('lightbox');
  const lightboxImg = document.getElementById('lightboxImg');
  function openLightbox(src){ if (!lightbox || !lightboxImg) return; lightboxImg.src = src; lightbox.hidden = false; }
  function closeLightbox(){ if (!lightbox) return; lightbox.hidden = true; }
  const gallery = document.getElementById('gallery');
  const resultBox = document.getElementById('result');
  if (gallery) {
    gallery.addEventListener('click', (e) => {
      const t = e.target;
      if (t && t.tagName === 'IMG') openLightbox(t.src);
    });
  }
  if (resultBox) {
    resultBox.addEventListener('click', (e) => {
      const t = e.target;
      if (t && t.tagName === 'IMG') openLightbox(t.src);
    });
  }
  if (lightbox) {
    lightbox.addEventListener('click', (e) => {
      if (e.target.classList.contains('modal-backdrop') || e.target.id === 'lightboxImg') closeLightbox();
    });
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeLightbox(); });
  }
})();
