document.addEventListener('DOMContentLoaded', () => {
  const canvasContainer = document.getElementById('canvas-container');
  const btnSideBySide = document.getElementById('btn-side-by-side');
  const btnStacked = document.getElementById('btn-stacked');
  const btnPip = document.getElementById('btn-pip');

  function selectPreset(preset) {
    canvasContainer.className = `preset-${preset}`;
    [btnSideBySide, btnStacked, btnPip].forEach(btn => btn.classList.remove('active'));
    if (preset === 'side-by-side') btnSideBySide.classList.add('active');
    if (preset === 'stacked') btnStacked.classList.add('active');
    if (preset === 'pip') btnPip.classList.add('active');
  }

  btnSideBySide.addEventListener('click', () => selectPreset('side-by-side'));
  btnStacked.addEventListener('click', () => selectPreset('stacked'));
  btnPip.addEventListener('click', () => selectPreset('pip'));

  // Camera enumeration
  const selectA = document.getElementById('camera-select-a');
  const selectB = document.getElementById('camera-select-b');

  async function initDevices() {
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.enumerateDevices) {
        console.warn('mediaDevices API not supported in this environment');
        return;
      }
      const devices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = devices.filter(d => d.kind === 'videoinput');
      
      [selectA, selectB].forEach(select => {
        // Clear except first option
        while (select.options.length > 1) {
          select.remove(1);
        }
        
        videoDevices.forEach((device, index) => {
          const opt = document.createElement('option');
          opt.value = device.deviceId;
          opt.text = device.label || `Camera ${index + 1}`;
          select.appendChild(opt);
        });
      });
    } catch (err) {
      console.error('Error enumerating devices:', err);
    }
  }

  initDevices();
});
