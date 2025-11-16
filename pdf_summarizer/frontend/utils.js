// utils.js

export function animateProgressBar(progressBar, current, target, duration = 800) {
  const start = performance.now();

  function step(timestamp) {
    const elapsed = timestamp - start;
    const progress = Math.min(elapsed / duration, 1);
    const interpolated = current + (target - current) * progress;
    progressBar.style.width = interpolated + "%";

    if (progress < 1) {
      requestAnimationFrame(step);
    }
  }

  requestAnimationFrame(step);
}

export function updateProgressSmooth(progressBar, currentPercent, targetPercent, duration = 300) {
  const start = parseFloat(progressBar.style.width) || 0;
  const change = targetPercent - start;
  const stepTime = 20; // ms
  const steps = Math.ceil(duration / stepTime);
  let stepCount = 0;

  const interval = setInterval(() => {
    stepCount++;
    const newPercent = start + (change * stepCount / steps);
    progressBar.style.width = newPercent + "%";
    if (stepCount >= steps) clearInterval(interval);
  }, stepTime);
}