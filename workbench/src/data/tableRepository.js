/**
 * Table metadata join (read-only).
 *
 * Sources — all existing artifacts, nothing recomputed:
 *   - current-state-model-tables.json : role / shape / process / grain / facts
 *   - analysis/layer/assessments.json : layer decision
 *   - problem.table_keys              : fallback workspace derivation
 *
 * When an optional artifact is missing the repository degrades to values that
 * can be derived from the problem itself (workspace from the table key).
 */

/**
 * @param {{tableMeta?: any, layer?: any}} artifacts
 */
export function createTableRepository(artifacts) {
  /** @type {Map<string, any>} */
  const metaByKey = new Map();
  const metaArtifact = artifacts.tableMeta;
  if (metaArtifact && Array.isArray(metaArtifact.tables)) {
    for (const row of metaArtifact.tables) metaByKey.set(row.table_key, row);
  }

  /** @type {Map<string, any>} */
  const layerByKey = new Map();
  const layerArtifact = artifacts.layer;
  if (layerArtifact && Array.isArray(layerArtifact.assessments)) {
    for (const row of layerArtifact.assessments) layerByKey.set(row.table_identifier, row);
  }

  /**
   * @param {string} tableKey
   * @returns {string} workspace / MaxCompute project
   */
  function workspaceOf(tableKey) {
    const meta = metaByKey.get(tableKey);
    if (meta && meta.project) return meta.project;
    const layer = layerByKey.get(tableKey);
    if (layer && layer.workspace_name) return layer.workspace_name;
    const dot = tableKey.indexOf(".");
    return dot > 0 ? tableKey.slice(0, dot) : "—";
  }

  /**
   * @param {string} tableKey
   * @returns {{key: string, name: string, workspace: string, layer: string, layerStatus: string, role: string, roles: string[], modelShape: string, columnCount: number|null, measureCount: number|null, processes: string[], grains: string[], factKeys: string[], dimensionKey: string|null, findingIds: string[], lineageIn: number|null, lineageOut: number|null, isVirtualView: boolean|null, status: string|null, humanValidated: boolean|null, hasMeta: boolean}}
   */
  function describe(tableKey) {
    const meta = metaByKey.get(tableKey);
    const layer = layerByKey.get(tableKey);
    const dot = tableKey.indexOf(".");
    const shortName = dot > 0 ? tableKey.slice(dot + 1) : tableKey;
    const roles = meta && Array.isArray(meta.current_roles) ? meta.current_roles : [];
    return {
      key: tableKey,
      name: shortName,
      workspace: workspaceOf(tableKey),
      layer:
        (layer && (layer.candidate_layer || layer.workspace_layer)) ||
        (meta && meta.candidate_layer) ||
        "—",
      layerStatus: (layer && layer.status) || (meta && meta.status) || null,
      role: (meta && meta.current_role) || (roles.length ? roles.join("/") : "—"),
      roles: roles.length ? roles : meta && meta.current_role ? [meta.current_role] : [],
      modelShape: (meta && meta.model_shape) || "—",
      columnCount: meta ? meta.column_count : null,
      measureCount: meta ? meta.measure_count : null,
      processes: (meta && meta.process_candidate_ids) || [],
      grains: (meta && meta.grain_patterns) || [],
      factKeys: (meta && meta.fact_keys) || [],
      dimensionKey: meta ? meta.dimension_key : null,
      findingIds: (meta && meta.finding_ids) || [],
      lineageIn: meta ? meta.lineage_in_degree : null,
      lineageOut: meta ? meta.lineage_out_degree : null,
      isVirtualView: meta ? Boolean(meta.is_virtual_view) : null,
      status: meta ? meta.status : null,
      humanValidated: meta ? Boolean(meta.human_validated) : null,
      hasMeta: Boolean(meta),
    };
  }

  /**
   * Model shape for the scope of a problem (single table or a small set).
   * @param {import("../domain/types.js").Problem} problem
   * @returns {string}
   */
  function modelShapeFor(problem) {
    const keys = problem.table_keys || [];
    if (!keys.length) return "—";
    const shapes = [...new Set(keys.map((key) => describe(key).modelShape).filter((s) => s && s !== "—"))];
    if (!shapes.length) return "—";
    if (shapes.length <= 3) return shapes.join(", ");
    return `${shapes.slice(0, 3).join(", ")} +${shapes.length - 3}`;
  }

  return {
    workspaceOf,
    describe,
    modelShapeFor,
    get metaCount() {
      return metaByKey.size;
    },
    get layerCount() {
      return layerByKey.size;
    },
  };
}
