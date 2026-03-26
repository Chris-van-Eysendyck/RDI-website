// ============================================================
// population-heatmap.js
// Population density "red mist" heatmap layer for globe.gl
// ============================================================

function redMistColorFn(t) {
  const v = Math.min(t, 1.2);
  const alpha = Math.pow(v, 0.45) * 0.55;
  const r = Math.round(140 + 115 * Math.min(v, 1));
  const g = Math.round(20 * Math.pow(v, 1.8));
  const b = Math.round(12 * Math.pow(v, 2.5));
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function initPopulationHeatmap(globe, opts = {}) {
  const {
    dataUrl = 'data/world_population_dense.csv',
    bandwidth = 1.2,
    saturation = 2.8,
    topAltitude = 0.01,
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
    .heatmapColorFn(() => redMistColorFn)
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
