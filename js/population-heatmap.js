// ============================================================
// population-heatmap.js
// Population density — 3D hex-bin spike layer for globe.gl
// Replaces flat heatmap with extruded hexagonal prisms,
// height proportional to population density.
// ============================================================

export function initPopulationHeatmap(globe, opts = {}) {
  const {
    dataUrl    = 'data/world_population_dense.csv',
    resolution = 4,     // H3 hex resolution: 4 ≈ 86 km across — regional detail
    maxAlt     = 0.22,  // tallest hex height (fraction of globe radius)
    margin     = 0.12,  // gap between hexes (0 = touching, 1 = invisible)
  } = opts;

  let popData = null;
  let visible = false;
  let loading = false;

  // Color ramp: dark crimson → amber → bright gold
  // Matches RDI brand palette
  function topColor(t) {
    t = Math.min(Math.max(t, 0), 1);
    const r = Math.round(110 + 145 * t);
    const g = Math.round(55  + 130 * Math.pow(t, 0.65));
    const b = Math.round(8   +  40 * Math.pow(t, 1.8));
    return `rgba(${r},${g},${b},0.95)`;
  }

  function sideColor(t) {
    t = Math.min(Math.max(t, 0), 1);
    const r = Math.round(70 + 100 * t);
    const g = Math.round(35 +  80 * Math.pow(t, 0.65));
    const b = Math.round(5  +  25 * Math.pow(t, 1.8));
    return `rgba(${r},${g},${b},0.55)`;
  }

  // Initialize hex-bin layer (empty until data loads)
  globe
    .hexBinPointsData([])
    .hexBinPointLat('lat')
    .hexBinPointLng('lng')
    .hexBinPointWeight('pop')
    .hexBinResolution(resolution)
    .hexMargin(margin)
    .hexAltitude(0)
    .hexTopColor(() => '#000')
    .hexSideColor(() => '#000');

  async function loadData() {
    if (popData) return popData;
    if (loading) return null;
    loading = true;
    try {
      const { csvParse } = await import('https://esm.sh/d3-dsv');
      const resp = await fetch(dataUrl);
      const csv  = await resp.text();
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

  function applyData(data) {
    // Estimate a reasonable max sumWeight for this resolution.
    // At H3 resolution 4 (~86 km hex), each hex covers ~30 of our 0.25° cells.
    // Use log scaling so the tallest bars (megacities) pop without
    // overwhelming everything else.
    const maxPop = Math.max(...data.map(d => d.pop));
    const MAX_W  = maxPop * 35; // headroom for hexbin aggregation

    function t(d) {
      // log scale: compresses extreme peaks, reveals smaller cities
      return Math.min(Math.log(d.sumWeight + 1) / Math.log(MAX_W + 1), 1);
    }

    globe
      .hexAltitude(d => Math.pow(t(d), 0.7) * maxAlt)
      .hexTopColor(d => topColor(t(d)))
      .hexSideColor(d => sideColor(t(d)))
      .hexBinPointsData(data);
  }

  const controller = {
    async show() {
      const data = await loadData();
      if (!data) return;
      visible = true;
      applyData(data);
    },
    hide() {
      visible = false;
      globe.hexBinPointsData([]);
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
