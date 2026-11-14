import type { EngineInfo, Job, JobConfig } from "./types";

// En desarrollo, Vite hace proxy de /api y /files al backend (ver vite.config.ts),
// por eso usamos rutas relativas. En producción, sirve el frontend detrás del
// mismo origen o ajusta API_BASE.
const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export function fileUrl(relPath: string): string {
  return `${API_BASE}/files/${relPath}`;
}

export async function getEngines(): Promise<{ default: string; engines: EngineInfo[] }> {
  const r = await fetch(`${API_BASE}/api/engines`);
  if (!r.ok) throw new Error("No se pudo obtener la lista de motores");
  return r.json();
}

export async function createJob(image: File, cfg: JobConfig): Promise<Job> {
  const fd = new FormData();
  fd.append("image", image);
  fd.append("engine", cfg.engine);
  fd.append("low_poly", String(cfg.low_poly));
  fd.append("target_faces", String(cfg.target_faces));
  fd.append("texture_size", String(cfg.texture_size));
  const r = await fetch(`${API_BASE}/api/jobs`, { method: "POST", body: fd });
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail ?? "Error al crear el job");
  return r.json();
}

/**
 * Sigue el progreso de un job vía SSE y llama onUpdate en cada cambio.
 * Devuelve una función para cancelar la suscripción.
 */
export function streamJob(jobId: string, onUpdate: (job: Job) => void): () => void {
  const es = new EventSource(`${API_BASE}/api/jobs/${jobId}/events`);
  es.onmessage = (ev) => {
    try {
      onUpdate(JSON.parse(ev.data) as Job);
    } catch {
      /* ignora frames mal formados */
    }
  };
  es.onerror = () => es.close();
  return () => es.close();
}
