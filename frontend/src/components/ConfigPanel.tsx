import type { EngineInfo, JobConfig } from "../types";

interface Props {
  engines: EngineInfo[];
  config: JobConfig;
  onChange: (c: JobConfig) => void;
  disabled?: boolean;
}

const qualityBadge: Record<string, string> = {
  fast: "bg-accent/15 text-accent",
  balanced: "bg-accent2/15 text-accent2",
  high: "bg-[#ff5d6c]/15 text-[#ff5d6c]",
};

/** Selectores de motor y de parámetros de reconstrucción. */
export default function ConfigPanel({ engines, config, onChange, disabled }: Props) {
  const set = (patch: Partial<JobConfig>) => onChange({ ...config, ...patch });

  return (
    <div className="space-y-5">
      <div>
        <label className="mb-2 block text-xs font-semibold uppercase tracking-wide text-muted">
          Motor 3D
        </label>
        <div className="space-y-2">
          {engines.map((e) => (
            <button
              key={e.name}
              disabled={disabled || !e.available}
              onClick={() => set({ engine: e.name })}
              className={`flex w-full items-start gap-3 rounded-lg border p-3 text-left transition
                ${config.engine === e.name ? "border-accent bg-accent/5" : "border-line bg-panel2/50 hover:border-accent/50"}
                ${!e.available ? "cursor-not-allowed opacity-45" : ""}`}
            >
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium">{e.label}</span>
                  <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${qualityBadge[e.quality]}`}>
                    {e.quality}
                  </span>
                  {!e.available && (
                    <span className="rounded-full bg-[#ff5d6c]/15 px-2 py-0.5 text-[10px] text-[#ff5d6c]">
                      no instalado
                    </span>
                  )}
                </div>
                <p className="mt-0.5 text-xs text-muted">{e.description}</p>
              </div>
            </button>
          ))}
        </div>
      </div>

      <div>
        <label className="flex items-center justify-between text-sm">
          <span>Modo low-poly</span>
          <input
            type="checkbox"
            checked={config.low_poly}
            disabled={disabled}
            onChange={(e) => set({ low_poly: e.target.checked })}
            className="h-4 w-4 accent-[#35d0ba]"
          />
        </label>
        {config.low_poly && (
          <div className="mt-2">
            <label className="mb-1 block text-xs text-muted">
              Caras objetivo: <b className="text-ink">{config.target_faces.toLocaleString()}</b>
            </label>
            <input
              type="range"
              min={2000}
              max={80000}
              step={1000}
              value={config.target_faces}
              disabled={disabled}
              onChange={(e) => set({ target_faces: Number(e.target.value) })}
              className="w-full accent-[#35d0ba]"
            />
          </div>
        )}
      </div>

      <div>
        <label className="mb-1 block text-xs text-muted">Resolución de textura PBR</label>
        <select
          value={config.texture_size}
          disabled={disabled}
          onChange={(e) => set({ texture_size: Number(e.target.value) })}
          className="w-full rounded-lg border border-line bg-panel2 p-2 text-sm"
        >
          <option value={512}>512 px</option>
          <option value={1024}>1024 px</option>
          <option value={2048}>2048 px</option>
        </select>
      </div>
    </div>
  );
}
