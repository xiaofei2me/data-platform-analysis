/**
 * Artifact loader — the only module that talks to the network.
 *
 * Read-only: every path points at an existing M3.6 / M3.x analysis artifact.
 * Nothing here may POST, PUT or mutate the files on disk.
 */

export const ARTIFACT_PATHS = Object.freeze({
  problems: "../analysis/review/current-state-problems.json",
  evidence: "../analysis/review/current-state-problem-evidence.json",
  tableMeta: "../analysis/review/current-state-model-tables.json",
  layer: "../analysis/evidence/layer/assessments.json",
});

export const REQUIRED_ARTIFACTS = Object.freeze(["problems", "evidence"]);
export const OPTIONAL_ARTIFACTS = Object.freeze(["tableMeta", "layer"]);

export class ArtifactsLoadError extends Error {
  /**
   * @param {string} message
   * @param {{missing?: string[], protocol?: string}} [details]
   */
  constructor(message, details = {}) {
    super(message);
    this.name = "ArtifactsLoadError";
    this.missing = details.missing || [];
    this.protocol = details.protocol || "";
  }
}

/**
 * @param {string} name
 * @param {string} url
 * @param {typeof fetch} fetchImpl
 * @returns {Promise<any>}
 */
async function fetchJson(name, url, fetchImpl) {
  let response;
  try {
    response = await fetchImpl(url, { cache: "no-store" });
  } catch (cause) {
    throw new ArtifactsLoadError(`无法加载 M3.6 产物（${name}）：${cause.message}`, {
      missing: [name],
    });
  }
  if (!response.ok) {
    throw new ArtifactsLoadError(
      `无法加载 M3.6 产物（${name}）：HTTP ${response.status}，${url}`,
      { missing: [name] },
    );
  }
  try {
    return await response.json();
  } catch (cause) {
    throw new ArtifactsLoadError(`无法解析 M3.6 产物（${name}）：${cause.message}`, {
      missing: [name],
    });
  }
}

/**
 * Load all workbench artifacts.
 *
 * `problems` and `evidence` are required; `tableMeta` and `layer` degrade
 * gracefully (affected-table columns fall back to values derived from the
 * problem itself).
 *
 * @param {{fetchImpl?: typeof fetch, protocol?: string}} [options]
 * @returns {Promise<{
 *   problems: any,
 *   evidence: any,
 *   tableMeta: any|null,
 *   layer: any|null,
 *   loadedAt: string,
 *   warnings: string[],
 * }>}
 */
export async function loadArtifacts(options = {}) {
  const fetchImpl = options.fetchImpl || (typeof fetch !== "undefined" ? fetch : null);
  const protocol = options.protocol || (typeof location !== "undefined" ? location.protocol : "http:");
  if (!fetchImpl) {
    throw new ArtifactsLoadError("当前环境没有可用的 fetch 实现。");
  }
  if (protocol === "file:") {
    throw new ArtifactsLoadError(
      "无法加载 M3.6 产物：页面以 file:// 方式打开，浏览器禁止读取 JSON。请通过 HTTP 访问本工作台。",
      { missing: [...REQUIRED_ARTIFACTS], protocol: "file:" },
    );
  }

  const required = await Promise.all(
    REQUIRED_ARTIFACTS.map((name) => fetchJson(name, ARTIFACT_PATHS[name], fetchImpl)),
  );
  const optional = await Promise.all(
    OPTIONAL_ARTIFACTS.map((name) =>
      fetchJson(name, ARTIFACT_PATHS[name], fetchImpl).catch(() => null),
    ),
  );

  const tableMeta = optional[0];
  const layer = optional[1];
  const warnings = [];
  if (!tableMeta) warnings.push(`可选产物缺失：${ARTIFACT_PATHS.tableMeta}`);
  if (!layer) warnings.push(`可选产物缺失：${ARTIFACT_PATHS.layer}`);
  if (!Array.isArray(problemsOf(required[0]))) {
    throw new ArtifactsLoadError("current-state-problems.json 中没有 problems 数组。", {
      missing: ["problems"],
    });
  }

  return {
    problems: required[0],
    evidence: required[1],
    tableMeta,
    layer,
    loadedAt: new Date().toISOString(),
    warnings,
  };
}

/**
 * @param {any} artifact
 * @returns {any[]|null}
 */
export function problemsOf(artifact) {
  return artifact && Array.isArray(artifact.problems) ? artifact.problems : null;
}

/**
 * Human-readable error block for the error screen (spec §34).
 * @param {ArtifactsLoadError} error
 * @returns {{title: string, details: string[], files: string[]}}
 */
export function describeLoadError(error) {
  const files = ["current-state-problems.json", "current-state-problem-evidence.json"];
  if (error && error.protocol === "file:") {
    return {
      title: "无法加载 M3.6 产物。",
      details: [
        "页面以 file:// 方式打开，浏览器会禁止 JSON fetch。",
        "请在仓库根目录启动静态服务，然后访问 /workbench/。",
        "示例：python3 -m http.server 8787  →  http://localhost:8787/workbench/",
      ],
      files,
    };
  }
  return {
    title: (error && error.message) || "无法加载 M3.6 产物。",
    details: ["请检查以下文件是否存在："],
    files,
  };
}
