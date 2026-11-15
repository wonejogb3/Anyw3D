import { useEffect, useMemo, useRef, useState } from "react";
import Dropzone from "./components/Dropzone";
import ConfigPanel from "./components/ConfigPanel";
import ProgressBar from "./components/ProgressBar";
import Viewer3D from "./components/Viewer3D";
import { createJob, fileUrl, getEngines, streamJob } from "./api";
import type { EngineInfo, Job, JobConfig } from "./types";

export default function App() {
  const [engines, setEngines] = useState<EngineInfo[]>([]);
  const [config, setConfig] = useState<JobConfig>({
    engine: "mock",
    low_poly: false,
    target_faces: 20000,
    texture_size: 1024,
  });
  const [file, setFile] = useState<File | null>(null);
  const [localPreview, setLocalPreview] = useState<string | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const cancelRef = useRef<() => void>();

  // Carga la lista de motores disponibles al abrir.
  useEffect(() => {
    getEngines()
      .then((r) => {
        setEngines(r.engines);
        setConfig((c) => ({ ...c, engine: r.default }));
      })
      .catch(() => setEngines([]));
  }, []);

  // Vista previa local inmediata de la imagen elegida.
  useEffect(() => {
    if (!file) return;
    const url = URL.createObjectURL(file);
    setLocalPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  const busy = !!job && !["done", "error"].includes(job.status);

  const glbUrl = useMemo(
    () => (job?.status === "done" && job.glb_path ? fileUrl(job.glb_path) : null),
    [job]
  );

  async function handleGenerate() {
    if (!file) return;
    cancelRef.current?.();
    try {
      const created = await createJob(file, config);
      setJob(created);
      cancelRef.current = streamJob(created.id, setJob);
    } catch (e) {
      setJob({
        id: "-", engine: config.engine, status: "error", progress: 0,
        stage: "Error", error: (e as Error).message,
      });
    }
  }

  useEffect(() => () => cancelRef.current?.(), []);

  return (
    <div className="flex h-full flex-col">
      <header className="border-b border-line px-6 py-3">
        <h1 className="text-lg font-semibold">
          Anyw3D <span className="text-muted">· Workspace 3D local</span>
        </h1>
        <p className="text-xs text-muted">
          Convierte PNG/JPG en modelos 3D (.glb / .obj) 100% en tu máquina.
        </p>
      </header>

      <div className="grid flex-1 grid-cols-1 gap-4 overflow-auto p-4 lg:grid-cols-[360px_1fr]">
        {/* Columna izquierda: entrada + configuración */}
        <aside className="flex flex-col gap-4">
          <section className="rounded-xl border border-line bg-panel p-4">
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">
              1 · Imagen de entrada
            </h2>
            <Dropzone onFile={setFile} previewUrl={localPreview} />
          </section>

          <section className="rounded-xl border border-line bg-panel p-4">
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">
              2 · Configuración
            </h2>
            <ConfigPanel engines={engines} config={config} onChange={setConfig} disabled={busy} />
          </section>

          <button
            onClick={handleGenerate}
            disabled={!file || busy}
            className="rounded-xl bg-accent px-4 py-3 font-semibold text-[#06211d] transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {busy ? "Generando…" : "Generar 3D"}
          </button>
        </aside>

        {/* Columna derecha: progreso + visor */}
        <main className="flex min-h-[420px] flex-col gap-4">
          {job && (
            <section className="rounded-xl border border-line bg-panel p-4">
              <ProgressBar job={job} />
              {job.status === "done" && (
                <div className="mt-3 flex gap-2">
                  {job.glb_path && (
                    <a
                      href={fileUrl(job.glb_path)}
                      download
                      className="rounded-lg border border-line bg-panel2 px-3 py-2 text-sm font-medium hover:border-accent"
                    >
                      ⬇ Descargar .glb
                    </a>
                  )}
                  {job.obj_path && (
                    <a
                      href={fileUrl(job.obj_path)}
                      download
                      className="rounded-lg border border-line bg-panel2 px-3 py-2 text-sm font-medium hover:border-accent"
                    >
                      ⬇ Descargar .obj
                    </a>
                  )}
                </div>
              )}
            </section>
          )}

          <section className="min-h-[420px] flex-1">
            <Viewer3D glbUrl={glbUrl} />
          </section>
        </main>
      </div>
    </div>
  );
}
