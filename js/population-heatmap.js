// ============================================================
// population-heatmap.js
// Population density "red mist" heatmap layer for globe.gl
// Drop into /js/ and wire up from map page
// ============================================================

/**
 * Red mist color interpolator.
 * Takes a density value t ∈ [0, 1+] and returns an rgba() string
 * that goes from fully transparent → dark red → bright red/white-hot.
 *
 * The "mist" effect comes from:
 *   1. Low base opacity that fades in smoothly
 *   2. Color ramp from deep crimson to hot scarlet
 *   3. A soft bandwidth setting on the heatmap itself
 */
function redMistColorFn(t) {
  // Clamp to reasonable range
  const v = Math.min(t, 1.2);

  // Opacity: transparent at 0, peaks around 0.72 at full density
  const alpha = Math.pow(v, 0.6) * 0.72;

  // Red channel: always high — from deep crimson (160) to full red (255)
  const r = Math.round(160 + 95 * Math.min(v, 1));

  // Green channel: stays very low, slight warm glow at peaks
  const g = Math.round(20 * Math.pow(v, 2));

  // Blue channel: near-zero, tiny hint at extreme density for "heat"
  const b = Math.round(12 * Math.pow(v, 3));

  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}


/**
 * Initialize the population heatmap layer on an existing Globe instance.
 *
 * @param {Globe} globe - Your existing globe.gl instance
 * @param {Object} opts - Optional overrides
 * @param {string} opts.dataUrl - URL to world_population.csv
 * @param {number} opts.bandwidth - Heatmap kernel bandwidth (default 0.9)
 * @param {number} opts.saturation - Color saturation multiplier (default 2.2)
 * @param {number} opts.topAltitude - Max heatmap altitude (default 0.12)
 * @param {number} opts.baseAltitude - Floor altitude (default 0.006)
 *
 * @returns {Object} Controller with .show(), .hide(), .toggle(), .isVisible()
 */
export function initPopulationHeatmap(globe, opts = {}) {
  const {
    dataUrl = 'https://raw.githubusercontent.com/vasturiano/globe.gl/master/example/datasets/world_population.csv',
    bandwidth = 0.9,
    saturation = 2.2,
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
