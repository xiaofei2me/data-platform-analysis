import { esc } from "./dom.js";

/**
 * Affected Tables (spec §15). All columns come from existing artifacts
 * (model tables / layer assessments / problem scope) — no MaxCompute calls.
 *
 * @param {Object} ctx
 * @param {import("../domain/types.js").Problem} problem
 * @returns {string} HTML
 */
export function renderAffectedTables(ctx, problem) {
  const state = ctx.store.getState();
  const tableKeys = problem.table_keys || [];
  const evidenceRows = ctx.evidenceRepo.forProblem(problem).rows;

  if (!tableKeys.length) {
    return `
      <section class="panel" data-section="tables">
        <div class="panel-head"><h3>受影响的表</h3></div>
        <div class="panel-body">
          <div class="empty-note"><strong>没有可用的受影响表信息。</strong></div>
        </div>
      </section>`;
  }

  const rows = tableKeys.map((key) => buildRow(ctx, problem, key, evidenceRows));
  const filtered = applySearch(rows, state.tableSearch);
  const sorted = applySort(filtered, state.tableSort);
  const expanded = state.expandedTable;

  return `
    <section class="panel" data-section="tables">
      <div class="panel-head">
        <h3>受影响的表</h3>
        <span class="panel-note">${tableKeys.length} 张表 · 来自 M3.5/M3.6 已有产物，不重新读取 MaxCompute</span>
      </div>
      <div class="table-toolbar">
        <input type="search" data-role="table-search" data-focus-key="table-search"
               placeholder="搜索 表 / Workspace" value="${esc(state.tableSearch)}" />
        <select data-role="table-sort" aria-label="表排序">
          <option value="table" ${state.tableSort.field === "table" ? "selected" : ""}>表名</option>
          <option value="workspace" ${state.tableSort.field === "workspace" ? "selected" : ""}>Workspace</option>
          <option value="layer" ${state.tableSort.field === "layer" ? "selected" : ""}>分层</option>
          <option value="role" ${state.tableSort.field === "role" ? "selected" : ""}>角色</option>
          <option value="columns" ${state.tableSort.field === "columns" ? "selected" : ""}>列数</option>
        </select>
        <button type="button" class="seg-btn" data-action="table-sort-dir">${state.tableSort.direction === "asc" ? "升序" : "降序"}</button>
      </div>
      ${
        sorted.length
          ? `<div class="table-scroll">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>表</th><th>Workspace</th><th>分层</th><th>角色</th>
                    <th>粒度</th><th>过程</th><th>对象</th>
                  </tr>
                </thead>
                <tbody>
                  ${sorted
                    .map((row) => {
                      const isOpen = expanded === row.key;
                      return `
                    <tr class="row-click" data-action="toggle-table" data-table-key="${esc(row.key)}">
                      <td class="mono">${esc(row.key)}${isOpen ? " ▾" : " ▸"}</td>
                      <td>${esc(row.workspace)}</td>
                      <td>${esc(row.layer)}</td>
                      <td>${esc(row.role)}</td>
                      <td>${esc(row.grainDisplay)}</td>
                      <td class="mono">${esc(row.processDisplay)}</td>
                      <td>${esc(row.objectDisplay)}</td>
                    </tr>
                    ${isOpen ? expandRowHtml(row) : ""}`;
                    })
                    .join("")}
                </tbody>
              </table>
            </div>`
          : `<div class="panel-body"><div class="empty-note">没有符合搜索条件的表。</div></div>`
      }
    </section>`;
}

function buildRow(ctx, problem, key, evidenceRows) {
  const meta = ctx.tableRepo.describe(key);
  const grains = evidenceRows
    .filter((row) => row.evidence_type === "GRAIN" && row.table_key === key && row.grain_key)
    .map((row) => row.grain_key);
  const objects = evidenceRows
    .filter((row) => row.evidence_type === "OBJECT" && row.table_key === key && row.object_key)
    .map((row) => row.object_key);
  const processes = meta.processes.length
    ? meta.processes
    : (problem.process_keys || []).length === 1 && (problem.table_keys || []).length === 1
      ? problem.process_keys
      : [];

  return {
    key,
    workspace: meta.workspace,
    layer: meta.layer,
    layerStatus: meta.layerStatus,
    role: meta.role,
    modelShape: meta.modelShape,
    columnCount: meta.columnCount,
    measureCount: meta.measureCount,
    grainDisplay: grains.length ? displayList(grains) : "—",
    processDisplay: processes.length ? displayList(processes) : "—",
    objectDisplay: objects.length ? displayList(objects) : "—",
    meta,
  };
}

function displayList(values) {
  if (values.length <= 2) return values.join(", ");
  return `${values.slice(0, 2).join(", ")} (+${values.length - 2})`;
}

function applySearch(rows, term) {
  const q = (term || "").trim().toLowerCase();
  if (!q) return rows;
  return rows.filter((row) => row.key.toLowerCase().includes(q) || row.workspace.toLowerCase().includes(q));
}

function applySort(rows, sort) {
  const factor = sort.direction === "desc" ? -1 : 1;
  const pick = (row) => {
    switch (sort.field) {
      case "workspace":
        return row.workspace.toLowerCase();
      case "layer":
        return row.layer.toLowerCase();
      case "role":
        return row.role.toLowerCase();
      case "columns":
        return String(row.columnCount ?? -1).padStart(8, "0");
      case "table":
      default:
        return row.key.toLowerCase();
    }
  };
  return [...rows].sort((a, b) => {
    const ka = pick(a);
    const kb = pick(b);
    return (ka < kb ? -1 : ka > kb ? 1 : 0) * factor;
  });
}

function expandRowHtml(row) {
  const meta = row.meta;
  const cell = (label, value) =>
    `<div class="kv"><div class="k">${esc(label)}</div><div class="v">${esc(
      value === null || value === undefined || value === "" ? "—" : value,
    )}</div></div>`;
  return `
    <tr class="expand-row">
      <td colspan="7">
        <div class="expand-panel">
          ${
            meta.hasMeta
              ? `<div class="kv-grid">
                  ${cell("模型形态", meta.modelShape)}
                  ${cell("当前角色", meta.roles.join(", "))}
                  ${cell("列数", meta.columnCount)}
                  ${cell("度量数", meta.measureCount)}
                  ${cell("分层判定", `${row.layer} (${row.layerStatus || "unknown"})`)}
                  ${cell("事实键", meta.factKeys.join(", "))}
                  ${cell("维度键", meta.dimensionKey)}
                  ${cell("粒度模式", meta.grains.join(", "))}
                  ${cell("过程候选", meta.processes.join(", "))}
                  ${cell("发现 ID", meta.findingIds.join(", "))}
                  ${cell("血缘入 / 出", `${meta.lineageIn ?? "—"} / ${meta.lineageOut ?? "—"}`)}
                  ${cell("虚拟视图", meta.isVirtualView === null ? "—" : String(meta.isVirtualView))}
                  ${cell("机器状态", meta.status)}
                  ${cell("人工验证（产物内）", meta.humanValidated === null ? "—" : String(meta.humanValidated))}
                </div>`
              : `<div class="empty-note"><strong>没有可用的受影响表信息。</strong> 该表在 current-state-model-tables.json 中没有对应行。</div>`
          }
          <div class="evidence-note">
            只读 join：current-state-model-tables.json + layer/assessments.json。
            不查询 MaxCompute，不重新计算。
          </div>
        </div>
      </td>
    </tr>`;
}
