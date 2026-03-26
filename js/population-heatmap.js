// ============================================================
// population-heatmap.js
// Population density "red mist" heatmap layer for globe.gl
// ============================================================

/**
 * Red mist color interpolator.
 * Tuned for the dense dataset — visible at low density,
 * semi-transparent at peaks so markers/borders show through.
 */
function redMistColorFn(t) {
  const v = Math.min(t, 1.2);

  // Moderate curve — shows low density without flooding high density
  const alpha = Math.pow(v, 0.45) * 0.55;

  // Dark maroon at low density, bright scarlet at high
  const r = Math.round(140 + 115 * Math.min(v, 1));
  const g = Math.round(20 * Math.pow(v, 1.8));
  const b = Math.round(12 * Math.pow(v, 2.5));

  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}


/**
 * Initialize the population heatmap layer on an existing Globe instance.
 *
 * @param {Globe} globe - Your existing globe.gl instance
 * @param {Object} opts - Optional overrides
 * @param {string} opts.dataUrl - URL to population CSV
 * @param {number} opts.bandwidth - Heatmap kernel bandwidth
 * @param {number} opts.saturation - Color saturation multiplier
 * @param {number} opts.topAltitude - Max heatmap altitude
 * @param {number} opts.baseAltitude - Floor altitude
 *
 * @returns {Object} Controller with .show(), .hide(), .toggle(), .isVisible()
 */
export function initPopulationHeatmap(globe, opts = {}) {
  const {
    dataUrl = 'data/world_population_dense.csv',
    bandwidth = 1.4,
    saturation = 2.8,
    topAltitude = 0.01,
    baseAltitude = 0.001,
  } = opts;

  let popData = null;
  let visible = false;
  let loading = false;

  // Pre-configure heatmap settings on the globe
  globe
    .heatmapPointLat('lat')
    .heatmapPointLng('lng')
    .heatmapPointWeight('pop')
    .heatmapBandwidth(bandwidth)
    .heatmapColorFn(() => redMistColorFn)
    .heatmapColorSaturation(saturation)
    .heatmapTopAltitude(topAltitude)
    .heatmapBaseAltitude(baseAltitude)
    .heatmapsData([]);   // start empty

  /**
   * Load the population CSV (lazy, once)
   */
  async function loadData() {
    if (popData) return popData;
    if (loading) return null;

    loading = true;

    try {
      // Dynamic import d3-dsv for CSV parsing
      const { csvParse } = await import('https://esm.sh/d3-dsv');
      const resp = await fetch(dataUrl);
      const csv = await resp.text();

      popData = csvParse(csv, ({ lat, lng, pop }) => ({
        lat: +lat,
        lng: +lng,
        pop: +pop,
      }));

      loading = false;
      return popData;
    } catch (err) {
      console.error('[population-heatmap] Failed to load data:', err);
      loading = false;
      return null;
    }
  }

  // Controller
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
