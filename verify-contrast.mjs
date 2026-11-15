// verify-contrast.mjs — Verificación de contraste WCAG (sin dependencias)
// Uso: node verify-contrast.mjs tokens.json

const fs = require('fs');

function hexToRgb(hex) {
  hex = hex.replace('#', '');
  if (hex.startsWith('rgba')) {
    const m = hex.match(/rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)/);
    return { r: +m[1], g: +m[2], b: +m[3] };
  }
  if (hex.length === 3) hex = hex.split('').map(c => c + c).join('');
  return {
    r: parseInt(hex.slice(0, 2), 16),
    g: parseInt(hex.slice(2, 4), 16),
    b: parseInt(hex.slice(4, 6), 16),
  };
}

function luminance({ r, g, b }) {
  const [rs, gs, bs] = [r, g, b].map(c => {
    c /= 255;
    return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

function contrast(fg, bg) {
  const L1 = luminance(hexToRgb(fg));
  const L2 = luminance(hexToRgb(bg));
  const hi = Math.max(L1, L2), lo = Math.min(L1, L2);
  return (hi + 0.05) / (lo + 0.05);
}

const data = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const themes = ['light', 'dark'];
const pairs = [
  ['text-primary', 'bg-base', 4.5],
  ['text-primary', 'bg-surface', 4.5],
  ['text-secondary', 'bg-base', 4.5],
  ['text-secondary', 'bg-surface', 4.5],
  ['text-disabled', 'bg-base', 3.0],
  ['text-disabled', 'bg-surface', 3.0],
  ['text-inverse', 'brand-primary', 4.5],
  ['brand-on-primary', 'brand-primary', 4.5],
  ['color-positive-text', 'color-positive-subtle', 4.5],
  ['color-positive-text', 'bg-surface', 4.5],
  ['color-negative-text', 'color-negative-subtle', 4.5],
  ['color-negative-text', 'bg-surface', 4.5],
  ['color-warning-text', 'color-warning-subtle', 4.5],
  ['color-info-text', 'color-info-subtle', 4.5],
  ['color-positive', 'bg-surface', 3.0],
  ['color-negative', 'bg-surface', 3.0],
  ['on-positive', 'color-positive', 4.5],
  ['on-negative', 'color-negative', 4.5],
  ['border-focus', 'bg-surface', 3.0],
];

let failed = 0;
for (const theme of themes) {
  console.log(`\n=== ${theme.toUpperCase()} ===`);
  console.log('Pair'.padEnd(42) + 'Ratio'.padStart(8) + '  Threshold'.padStart(12) + '  Result');
  console.log('-'.repeat(72));
  for (const [fg, bg, thr] of pairs) {
    try {
      const r = contrast(data[theme][fg], data[theme][bg]);
      const pass = r >= thr;
      if (!pass) failed++;
      console.log(`${fg}/${bg}`.padEnd(42) + r.toFixed(2).padStart(8) + thr.toFixed(1).padStart(12) + (pass ? '  PASS' : '  FAIL'));
    } catch (e) {
      console.log(`${fg}/${bg}`.padEnd(42) + 'ERROR'.padStart(8) + thr.toFixed(1).padStart(12) + '  FAIL');
      failed++;
    }
  }
}

// Chart colors: verify luminance differences
console.log('\n=== CHART COLORS (luminance check) ===');
for (const theme of themes) {
  const charts = ['chart-1','chart-2','chart-3','chart-4','chart-5','chart-6'].map(k => data[theme][k]);
  const lums = charts.map(c => luminance(hexToRgb(c)));
  let minDiff = Infinity;
  for (let i = 0; i < lums.length; i++)
    for (let j = i + 1; j < lums.length; j++)
      minDiff = Math.min(minDiff, Math.abs(lums[i] - lums[j]));
  const pass = minDiff > 0.05;
  if (!pass) failed++;
  console.log(`${theme}: min luminance diff = ${minDiff.toFixed(4)} ${pass ? 'PASS' : 'FAIL'}`);
}

console.log(`\n${failed === 0 ? 'ALL PASS' : failed + ' FAILURES'}`);
process.exit(failed > 0 ? 1 : 0);