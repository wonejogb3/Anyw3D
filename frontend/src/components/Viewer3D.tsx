import { Suspense, useEffect } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { Center, Environment, Grid, OrbitControls, useGLTF } from "@react-three/drei";
import * as THREE from "three";

// El backend normaliza todo modelo a una caja de lado 1 centrada en el origen,
// así que una cámara fija a ~2.7 unidades (fov 40) lo encuadra siempre entero.
const CAMERA_HOME: [number, number, number] = [1.45, 0.85, 2.1];

function Model({ url }: { url: string }) {
  // useGLTF cachea y suspende mientras carga el .glb del backend.
  const { scene } = useGLTF(url);

  useEffect(() => {
    // Dibuja ambas caras: muchas mallas generadas desde imagen no son cerradas
    // y, vistas por detrás, desaparecerían (backface culling).
    scene.traverse((obj) => {
      const mesh = obj as THREE.Mesh;
      if (!mesh.isMesh) return;
      const mats = Array.isArray(mesh.material) ? mesh.material : [mesh.material];
      for (const m of mats) {
        m.side = THREE.DoubleSide;
        m.needsUpdate = true;
      }
    });
  }, [scene]);

  return (
    <Center>
      <primitive object={scene} />
    </Center>
  );
}

/** Vuelve a la vista inicial cada vez que se carga un modelo nuevo. */
function CameraReset({ url }: { url: string | null }) {
  const { camera, controls } = useThree();
  useEffect(() => {
    camera.position.set(...CAMERA_HOME);
    const orbit = controls as unknown as { target: THREE.Vector3; update: () => void } | null;
    if (orbit) {
      orbit.target.set(0, 0, 0);
      orbit.update();
    } else {
      camera.lookAt(0, 0, 0);
    }
  }, [url, camera, controls]);
  return null;
}

/** Visor interactivo: rotación (arrastrar), zoom (rueda), paneo (clic derecho). */
export default function Viewer3D({ glbUrl }: { glbUrl: string | null }) {
  return (
    <div className="relative h-full w-full overflow-hidden rounded-xl border border-line bg-[#0b0e12]">
      <Canvas camera={{ position: CAMERA_HOME, fov: 40 }} dpr={[1, 2]}>
        <ambientLight intensity={0.6} />
        <directionalLight position={[3, 5, 2]} intensity={1.1} />
        <Suspense fallback={null}>
          {glbUrl && <Model url={glbUrl} />}
          <Environment preset="city" />
        </Suspense>
        <Grid
          args={[10, 10]}
          cellColor="#2a333f"
          sectionColor="#35d0ba"
          fadeDistance={14}
          infiniteGrid
          position={[0, -0.52, 0]}
        />
        <OrbitControls makeDefault enableDamping dampingFactor={0.1} target={[0, 0, 0]} />
        <CameraReset url={glbUrl} />
      </Canvas>

      {!glbUrl && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center text-center text-muted">
          <div>
            <div className="text-5xl">🧊</div>
            <p className="mt-2 text-sm">El modelo 3D aparecerá aquí</p>
          </div>
        </div>
      )}
      {glbUrl && (
        <div className="pointer-events-none absolute bottom-2 left-3 font-mono text-[11px] text-muted">
          arrastrar: rotar · rueda: zoom · clic derecho: paneo
        </div>
      )}
    </div>
  );
}
