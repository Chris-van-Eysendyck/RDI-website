// ============================================================
// population-heatmap.js
// Population density — 3D hex-bin spike layer for globe.gl
// ============================================================

export function initPopulationHeatmap(globe, opts = {}) {
  const {
    dataUrl    = 'data/world_population_dense.csv',
    resolution = 5,     // H3 resolution 5 ≈ 33 km hex — fine city-scale detail
    maxAlt     = 0.04,  // tallest spike = 4% of globe radius (subtle but visible)
    margin     = 0.20,  // visible gap between hexes so individual structures show
  } = opts;

  let popData = null;
  let visible = false;
  let loading = false;

  // Color ramp: dark crimson → warm amber → bright gold at peak
  function topColor(t) {
    t = Math.min(Math.max(t, 0), 1);
    const r = Math.round(110 + 145 * t);
    const g = Math.round(50  + 130 * Math.pow(t, 0.7));
    const b = Math.round(8   +  40 * Math.pow(t, 2));
    return `rgba(${r},${g},${b},0.92)`;
  }

  function sideColor(t) {
    t = Math.min(Math.max(t, 0), 1);
    const r = Math.round(70 + 90 * t);
    const g = Math.round(30 + 75 * Math.pow(t, 0.7));
    const b = Math.round(5  + 22 * Math.pow(t, 2));
    return `rgba(${r},${g},${b},0.5)`;
  }

  // Initialize empty hex-bin layer
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
    // At H3 resolution 5 (~33 km hex), our 0.25° data cells (~27 km) map
    // roughly 1:1 to hexes. Typical max sumWeight ≈ 3–5 cells × max pop (62).
    // Use sqrt scaling: gives good spread so sparse areas stay dim but
    // medium-density regions (not just megacities) are also visible.
    const MAX_W = 180; // generous cap; values above this all reach peak color

    function t(d) {
      return Math.min(Math.sqrt(d.sumWeight / MAX_W), 1);
    }

    globe
      .hexAltitude(d => t(d) * maxAlt)
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
