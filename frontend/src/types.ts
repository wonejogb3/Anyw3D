export type JobStatus =
  | "queued"
  | "preprocessing"
  | "inferring"
  | "postprocessing"
  | "done"
  | "error";

export interface Job {
  id: string;
  engine: string;
  status: JobStatus;
  progress: number;
  stage: string;
  error?: string | null;
  input_path?: string | null;
  preview_path?: string | null;
  glb_path?: string | null;
  obj_path?: string | null;
  meta?: Record<string, unknown>;
}

export interface EngineInfo {
  name: string;
  label: string;
  description: string;
  available: boolean;
  quality: "fast" | "balanced" | "high";
  needs_gpu: boolean;
}

export interface JobConfig {
  engine: string;
  low_poly: boolean;
  target_faces: number;
  texture_size: number;
}
