// ============================================================
// population-heatmap.js
// Population density heatmap layer for globe.gl
// ============================================================

function populationColorFn(t) {
  // t = normalized density (0–1+), pre-multiplied by saturation
  // Hard noise floor — empty ocean/land stays invisible
  if (t < 0.05) return 'rgba(0,0,0,0)';

  const v = Math.min(t, 1);

  // Steep alpha: sparse areas stay dim, cities glow strongly
  const alpha = Math.pow(v, 0.85) * 0.80;

  // Color ramp: dark crimson → amber → bright gold at peak density
  const r = Math.round(140 + 115 * v);
  const g = Math.round(10  + 170 * Math.pow(v, 0.65));
  const b = Math.round(5   +  40 * Math.pow(v, 2.2));

  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function initPopulationHeatmap(globe, opts = {}) {
  const {
    dataUrl      = 'data/world_population_dense.csv',
    bandwidth    = 0.5,   // tight (~55 km) — matches 0.25° data resolution; prevents ocean bleed
    saturation   = 4.5,   // high — sharpens peak cities vs. sparse countryside
    topAltitude  = 0.015,
    baseAltitude = 0.001,
  } = opts;

  let popData = null;
  let visible = false;
  let loading = false;

  globe
    .heatmapPointLat('lat')
    .heatmapPointLng('lng')
    .heatmapPointWeight('pop')
    .heatmapBandwidth(bandwidth)
    .heatmapColorFn(() => populationColorFn)
    .heatmapColorSaturation(saturation)
    .heatmapTopAltitude(topAltitude)
    .heatmapBaseAltitude(baseAltitude)
    .heatmapsData([]);

  async function loadData() {
    if (popData) return popData;
    if (loading) return null;
    loading = true;
    try {
      const { csvParse } = await import('https://esm.sh/d3-dsv');
      const resp = await fetch(dataUrl);
      const csv = await resp.text();
      popData = csvParse(csv, ({ lat, lng, pop }) => ({
        lat: +lat, lng: +lng, pop: +pop,
      }));
      loading = false;
      return popData;
    } catch (err) {
      console.error('[population-heatmap] Failed to load data:', err);
      loading = false;
      return null;
    }
  }

  const controller = {
    async show() {
      const data = await loadData();
      if (!data) return;
      visible = true;
      globe.heatmapsData([data]);
    },
    hide() {
      visible = false;
      globe.heatmapsData([]);
    },
    toggle() {
      return visible ? controller.hide() : controller.show();
    },
    isVisible() {
      return visible;
    },
  };

  return controller;
}
