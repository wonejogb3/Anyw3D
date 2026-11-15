import type { Job } from "../types";

const labels: Record<string, string> = {
  queued: "En cola",
  preprocessing: "Preprocesando",
  inferring: "Reconstruyendo",
  postprocessing: "Exportando",
  done: "Listo",
  error: "Error",
};

/** Barra de progreso en tiempo real con la etapa actual. */
export default function ProgressBar({ job }: { job: Job }) {
  const isError = job.status === "error";
  const pct = Math.max(2, job.progress);
  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-sm">
        <span className="font-medium">
          {labels[job.status] ?? job.status}
          {job.stage !== (labels[job.status] ?? job.status) && (
            <span className="ml-2 text-muted">{job.stage}</span>
          )}
        </span>
        <span className="font-mono text-muted">{job.progress}%</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-panel2">
        <div
          className="h-full rounded-full transition-[width] duration-200"
          style={{
            width: `${pct}%`,
            background: isError ? "#ff5d6c" : job.status === "done" ? "#35d0ba" : "#f5a623",
          }}
        />
      </div>
      {isError && <p className="mt-2 text-sm text-[#ff5d6c]">{job.error}</p>}
    </div>
  );
}
