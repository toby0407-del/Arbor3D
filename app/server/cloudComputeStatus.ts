export async function cloudComputeStatus(env: Record<string, string | undefined>, request: typeof fetch = fetch) {
  const endpoint = env.ARBOR3D_CLOUD_DBH_URL?.trim() || env.ARBOR3D_SECTION_CLOUD_URL?.trim();
  const hybrid = !env.ARBOR3D_CLOUD_DBH_URL?.trim() && Boolean(env.ARBOR3D_SECTION_CLOUD_URL?.trim());
  const configured = Boolean(endpoint);
  if (!configured) return { state: "unconfigured", configured: false };
  try {
    const url = new URL(endpoint!);
    const local = ["localhost", "127.0.0.1", "[::1]"].includes(url.hostname);
    if (url.username || url.password || url.search || url.hash || (!local && url.protocol !== "https:")) throw new Error("Invalid cloud endpoint");
    const key = env.ARBOR3D_CLOUD_DBH_API_KEY?.trim();
    if (!local && !key) return { configured, state: "authentication_required" };
    const response = await request(`${url.href.replace(/\/+$/, "")}/v1/capabilities`, {
      headers: key ? { "X-API-Key": key } : {}, signal: AbortSignal.timeout(10000),
    });
    if (!response.ok) return { configured, state: response.status === 401 ? "authentication_required" : "unavailable" };
    const capabilities = await response.json() as { full_pipeline_ready?: boolean; prepare_only?: boolean; result_download?: boolean; section_geometry_ready?: boolean };
    return { configured, state: hybrid && capabilities.section_geometry_ready === true ? "hybrid_ready" : capabilities.full_pipeline_ready === true && capabilities.prepare_only === false && capabilities.result_download === true ? "ready" : "prepare_only" };
  } catch { return { configured, state: "unavailable" }; }
}
