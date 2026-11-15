import { useCallback, useRef, useState } from "react";

interface Props {
  onFile: (file: File) => void;
  previewUrl: string | null;
}

/** Área de arrastrar y soltar para PNG/JPG (con soporte de transparencia). */
export default function Dropzone({ onFile, previewUrl }: Props) {
  const [over, setOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const accept = useCallback(
    (files: FileList | null) => {
      const f = files?.[0];
      if (!f) return;
      if (!/image\/(png|jpe?g)/.test(f.type)) {
        alert("Solo PNG o JPG.");
        return;
      }
      onFile(f);
    },
    [onFile]
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setOver(true);
      }}
      onDragLeave={() => setOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setOver(false);
        accept(e.dataTransfer.files);
      }}
      onClick={() => inputRef.current?.click()}
      className={`relative flex min-h-[220px] cursor-pointer items-center justify-center rounded-xl border-2 border-dashed p-4 transition
        ${over ? "border-accent bg-accent/5" : "border-line bg-panel2/40 hover:border-accent/60"}`}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/png,image/jpeg"
        className="hidden"
        onChange={(e) => accept(e.target.files)}
      />
      {previewUrl ? (
        <img
          src={previewUrl}
          alt="entrada"
          className="max-h-[260px] rounded-lg object-contain"
          style={{
            backgroundImage:
              "repeating-conic-gradient(#20262e 0% 25%, #171c23 0% 50%)",
            backgroundSize: "20px 20px",
          }}
        />
      ) : (
        <div className="text-center">
          <div className="text-4xl">🖼️ → 🧊</div>
          <p className="mt-2 font-medium">Arrastra una imagen PNG o JPG</p>
          <p className="text-sm text-muted">o haz clic para elegir · fondo transparente soportado</p>
        </div>
      )}
    </div>
  );
}
