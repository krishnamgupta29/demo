import React, { useEffect, useRef, useState, useCallback, memo } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { buildAnatomicalToothGeometry } from './anatomicalToothBuilder';
import { TEETH_DATA, ToothMeta } from './toothData';
import { RotateCcw, Sparkles, Layers, Eye } from 'lucide-react';

export interface HeroTooth3DProps {
  height?: number | string;
  onStructureHover?: (structure: string | null) => void;
}

interface StructureCallout {
  id: string;
  name: string;
  category: 'enamel' | 'dentin' | 'pulp' | 'canal' | 'pdl' | 'apex';
  colorHex: string;
  badge: string;
  desc: string;
}

const STRUCTURE_CALLOUTS: Record<string, StructureCallout> = {
  'enamel-16': {
    id: 'enamel-16',
    name: 'Crown Enamel',
    category: 'enamel',
    colorHex: '#F5F2E8',
    badge: '96% Hydroxyapatite',
    desc: 'Outer protective translucent crystalline layer of the crown.',
  },
  'dentin-coronal-16': {
    id: 'dentin-coronal-16',
    name: 'Coronal Dentin',
    category: 'dentin',
    colorHex: '#E5D3A3',
    badge: 'Microscopic Tubules',
    desc: 'Shock-absorbing mineralized tissue beneath the enamel mantle.',
  },
  'dentin-radicular-16': {
    id: 'dentin-radicular-16',
    name: 'Radicular Dentin',
    category: 'dentin',
    colorHex: '#D1BD84',
    badge: 'Root Bulk',
    desc: 'Encases the root canal conduits down to the apical constriction.',
  },
  'pulp-chamber-16': {
    id: 'pulp-chamber-16',
    name: 'Pulp Chamber',
    category: 'pulp',
    colorHex: '#DC2626',
    badge: 'Neurovascular Core',
    desc: 'Contains vital odontoblasts, sensory nerves, and microcapillaries.',
  },
  'canal-distobuccal-16': {
    id: 'canal-distobuccal-16',
    name: 'Endodontic Canal',
    category: 'canal',
    colorHex: '#B91C1C',
    badge: 'Apical Pathway',
    desc: 'Conduit supplying innervation and blood supply from alveolar bone.',
  },
  'pdl-16': {
    id: 'pdl-16',
    name: 'Periodontal Ligament',
    category: 'pdl',
    colorHex: '#E5989B',
    badge: 'Sharpey Fibers',
    desc: 'Suspends the tooth root within the alveolar socket.',
  },
};

export const HeroTooth3D = memo<HeroTooth3DProps>(({
  height = '100%',
  onStructureHover,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [activeCallout, setActiveCallout] = useState<StructureCallout | null>(null);
  const [isInteracting, setIsInteracting] = useState<boolean>(false);
  const [modelType, setModelType] = useState<'glb' | 'procedural'>('glb');

  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const modelRootRef = useRef<THREE.Group | null>(null);
  const meshMapRef = useRef<Map<string, THREE.Mesh>>(new Map());
  const animFrameIdRef = useRef<number | null>(null);
  const lastUserInteractionRef = useRef<number>(Date.now());

  const resetCamera = useCallback(() => {
    if (!cameraRef.current || !controlsRef.current) return;
    cameraRef.current.position.set(2.8, 1.2, 3.0);
    controlsRef.current.target.set(0, 0, 0);
    controlsRef.current.update();
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    // ─── Scene & Background ──────────────────────────────────────────────────
    const scene = new THREE.Scene();
    sceneRef.current = scene;

    const width = container.clientWidth || 600;
    const heightPx = typeof height === 'number' ? height : container.clientHeight || 560;

    const camera = new THREE.PerspectiveCamera(34, width / heightPx, 0.1, 100);
    camera.position.set(2.8, 1.2, 3.0);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
      preserveDrawingBuffer: true,
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2.0));
    renderer.setSize(width, heightPx);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.35;
    rendererRef.current = renderer;

    // ─── Camera Orbit Controls ───────────────────────────────────────────────
    const controls = new OrbitControls(camera, canvas);
    controls.enableDamping = true;
    controls.dampingFactor = 0.06;
    controls.rotateSpeed = 0.85;
    controls.zoomSpeed = 1.0;
    controls.enablePan = false;
    controls.minDistance = 1.5;
    controls.maxDistance = 6.0;
    controls.target.set(0.0, 0.0, 0.0);
    controlsRef.current = controls;

    controls.addEventListener('start', () => {
      setIsInteracting(true);
      lastUserInteractionRef.current = Date.now();
    });
    controls.addEventListener('end', () => {
      setIsInteracting(false);
      lastUserInteractionRef.current = Date.now();
    });

    // ─── Studio Lighting Setup ───────────────────────────────────────────────
    // Ambient Light
    const ambientLight = new THREE.AmbientLight(0xFFFBF0, 1.4);
    scene.add(ambientLight);

    // Key Light (Warm ivory highlight)
    const keyLight = new THREE.DirectionalLight(0xFFFEF5, 3.2);
    keyLight.position.set(-3.5, 4.5, 3.8);
    keyLight.castShadow = true;
    scene.add(keyLight);

    // Fill Light (Soft cool navy bounce)
    const fillLight = new THREE.DirectionalLight(0xE0E7FF, 1.8);
    fillLight.position.set(4.0, 2.5, 2.5);
    scene.add(fillLight);

    // Back / Rim Light (Separates enamel silhouette)
    const rimLight = new THREE.DirectionalLight(0xFFFFFF, 3.0);
    rimLight.position.set(0.0, 4.5, -4.0);
    scene.add(rimLight);

    // Subtle Under-Light (Gives root warmth)
    const underLight = new THREE.DirectionalLight(0xFDE68A, 1.2);
    underLight.position.set(0.0, -4.0, 1.5);
    scene.add(underLight);

    // ─── Model Loading (GLB Cutaway or Procedural Watertight Fallback) ────────
    const loader = new GLTFLoader();
    setIsLoading(true);

    const meshes = new Map<string, THREE.Mesh>();

    const setupProceduralFallback = () => {
      const group = new THREE.Group();
      const meta = TEETH_DATA.find((t) => t.fdi === 16) || TEETH_DATA[0];
      const geom = buildAnatomicalToothGeometry(meta);

      const mat = new THREE.MeshPhysicalMaterial({
        vertexColors: true,
        roughness: 0.18,
        metalness: 0.0,
        clearcoat: 0.9,
        clearcoatRoughness: 0.08,
        transmission: 0.15,
        ior: 1.54,
        side: THREE.DoubleSide,
      });

      const mesh = new THREE.Mesh(geom, mat);
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      group.add(mesh);

      // Center geometry
      geom.computeBoundingBox();
      const center = geom.boundingBox?.getCenter(new THREE.Vector3()) || new THREE.Vector3();
      mesh.position.sub(center);

      scene.add(group);
      modelRootRef.current = group;
      setModelType('procedural');
      setIsLoading(false);
    };

    loader.load(
      '/models/tooth-cutaway.glb',
      (gltf) => {
        const root = gltf.scene;
        const box = new THREE.Box3().setFromObject(root);
        const center = box.getCenter(new THREE.Vector3());
        root.position.set(-center.x, -center.y, -center.z);

        root.traverse((obj) => {
          if ((obj as THREE.Mesh).isMesh) {
            const mesh = obj as THREE.Mesh;
            mesh.castShadow = true;
            mesh.receiveShadow = true;
            const name = mesh.name;
            meshes.set(name, mesh);

            const meta = STRUCTURE_CALLOUTS[name];
            if (meta) {
              if (meta.category === 'enamel') {
                mesh.material = new THREE.MeshPhysicalMaterial({
                  color: new THREE.Color(meta.colorHex),
                  roughness: 0.14,
                  metalness: 0.0,
                  clearcoat: 1.0,
                  clearcoatRoughness: 0.04,
                  transparent: true,
                  opacity: 0.88,
                  transmission: 0.28,
                  ior: 1.58,
                  side: THREE.DoubleSide,
                });
              } else if (meta.category === 'dentin') {
                mesh.material = new THREE.MeshStandardMaterial({
                  color: new THREE.Color(meta.colorHex),
                  roughness: 0.36,
                  metalness: 0.0,
                  side: THREE.DoubleSide,
                });
              } else if (meta.category === 'pdl') {
                mesh.material = new THREE.MeshStandardMaterial({
                  color: new THREE.Color(meta.colorHex),
                  roughness: 0.44,
                  metalness: 0.0,
                  transparent: true,
                  opacity: 0.55,
                  side: THREE.DoubleSide,
                });
              } else if (meta.category === 'pulp' || meta.category === 'canal') {
                mesh.material = new THREE.MeshPhysicalMaterial({
                  color: new THREE.Color(meta.colorHex),
                  emissive: new THREE.Color(0x991B1B),
                  emissiveIntensity: 0.45,
                  roughness: 0.20,
                  clearcoat: 0.8,
                  side: THREE.DoubleSide,
                });
              }
            }
          }
        });

        scene.add(root);
        modelRootRef.current = root;
        meshMapRef.current = meshes;
        setModelType('glb');
        setIsLoading(false);
      },
      undefined,
      (err) => {
        console.warn('HeroTooth3D GLB notice, loading procedural anatomical model:', err);
        setupProceduralFallback();
      }
    );

    // ─── Continuous Render Loop (Subtle Natural Float & Auto-Rotation) ───────
    let startTime = performance.now();

    const animate = () => {
      animFrameIdRef.current = requestAnimationFrame(animate);

      const elapsed = (performance.now() - startTime) * 0.001;
      const timeSinceUser = Date.now() - lastUserInteractionRef.current;

      // Auto-rotation resumes smoothly 2.5s after user interaction
      if (modelRootRef.current && timeSinceUser > 2500) {
        modelRootRef.current.rotation.y += 0.004;
        // Subtle vertical breathing float
        modelRootRef.current.position.y = Math.sin(elapsed * 1.2) * 0.06;
      }

      controls.update();
      renderer.render(scene, camera);
    };

    animate();

    // ─── Responsive Resize Observer ──────────────────────────────────────────
    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width: newWidth, height: newHeight } = entry.contentRect;
        if (newWidth > 0 && newHeight > 0 && cameraRef.current && rendererRef.current) {
          cameraRef.current.aspect = newWidth / newHeight;
          cameraRef.current.updateProjectionMatrix();
          rendererRef.current.setSize(newWidth, newHeight);
        }
      }
    });

    resizeObserver.observe(container);

    return () => {
      resizeObserver.disconnect();
      if (animFrameIdRef.current) cancelAnimationFrame(animFrameIdRef.current);
      controls.dispose();
      renderer.dispose();
      scene.clear();
    };
  }, [height]);

  const handleSelectStructure = (structureId: string) => {
    const callout = STRUCTURE_CALLOUTS[structureId];
    setActiveCallout(callout || null);
    if (onStructureHover) onStructureHover(callout?.name || null);
  };

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        width: '100%',
        height: typeof height === 'number' ? `${height}px` : height,
        minHeight: '480px',
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {/* Three.js Canvas */}
      <canvas
        ref={canvasRef}
        style={{
          width: '100%',
          height: '100%',
          cursor: isInteracting ? 'grabbing' : 'grab',
          display: 'block',
        }}
      />

      {/* Loading Overlay */}
      {isLoading && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'rgba(238, 235, 218, 0.75)',
            backdropFilter: 'blur(6px)',
            gap: '12px',
            zIndex: 10,
          }}
        >
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: '50%',
              border: '3px solid #ded8c4',
              borderTopColor: '#282b4a',
              animation: 'spin 1s linear infinite',
            }}
          />
          <span style={{ fontSize: '12px', fontWeight: 600, color: '#282b4a', letterSpacing: '0.04em' }}>
            Initializing 3D Dental Anatomy...
          </span>
        </div>
      )}

      {/* Interactive Anatomical Layer Floating Badges */}
      <div
        style={{
          position: 'absolute',
          top: '20px',
          left: '20px',
          zIndex: 20,
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          pointerEvents: 'auto',
          maxWidth: '240px',
        }}
      >
        <div
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            padding: '4px 10px',
            borderRadius: '6px',
            backgroundColor: 'rgba(255, 255, 255, 0.85)',
            backdropFilter: 'blur(8px)',
            border: '1px solid #ded8c4',
            fontSize: '10.5px',
            fontWeight: 700,
            color: '#282b4a',
            boxShadow: '0 2px 8px rgba(40, 43, 74, 0.06)',
          }}
        >
          <Layers size={12} color="#282b4a" />
          <span>Anatomical Cutaway Reference</span>
        </div>

        {Object.values(STRUCTURE_CALLOUTS).slice(0, 4).map((struct) => {
          const isActive = activeCallout?.id === struct.id;
          return (
            <button
              key={struct.id}
              onClick={() => handleSelectStructure(struct.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '6px 12px',
                borderRadius: '8px',
                border: isActive ? '1.5px solid #282b4a' : '1px solid rgba(222, 216, 196, 0.8)',
                backgroundColor: isActive ? '#282b4a' : 'rgba(255, 255, 255, 0.82)',
                color: isActive ? '#FFFFFF' : '#282b4a',
                fontSize: '11px',
                fontWeight: 600,
                cursor: 'pointer',
                textAlign: 'left',
                backdropFilter: 'blur(8px)',
                boxShadow: '0 2px 6px rgba(40, 43, 74, 0.04)',
                transition: 'all 0.15s ease',
              }}
            >
              <div
                style={{
                  width: '8px',
                  height: '8px',
                  borderRadius: '50%',
                  backgroundColor: struct.category === 'pulp' ? '#DC2626' : (struct.category === 'enamel' ? '#CA8A04' : '#282b4a'),
                }}
              />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ lineHeight: 1.2 }}>{struct.name}</div>
                <div style={{ fontSize: '9px', opacity: isActive ? 0.85 : 0.65 }}>{struct.badge}</div>
              </div>
            </button>
          );
        })}
      </div>

      {/* Floating Active Structure Card */}
      {activeCallout && (
        <div
          style={{
            position: 'absolute',
            bottom: '20px',
            left: '20px',
            right: '20px',
            zIndex: 20,
            padding: '14px 18px',
            borderRadius: '10px',
            backgroundColor: 'rgba(255, 255, 255, 0.94)',
            backdropFilter: 'blur(12px)',
            border: '1px solid #ded8c4',
            boxShadow: '0 8px 24px rgba(40, 43, 74, 0.10)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '16px',
            animation: 'heroSlideUp 0.3s ease-out both',
          }}
        >
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
              <span style={{ fontSize: '13px', fontWeight: 800, color: '#282b4a' }}>{activeCallout.name}</span>
              <span style={{ fontSize: '10px', fontWeight: 700, padding: '1px 6px', borderRadius: '4px', backgroundColor: '#f7f5ed', color: '#575a75', border: '1px solid #ded8c4' }}>
                {activeCallout.badge}
              </span>
            </div>
            <p style={{ fontSize: '11.5px', color: '#575a75', margin: 0, lineHeight: 1.4 }}>
              {activeCallout.desc}
            </p>
          </div>
          <button
            onClick={() => setActiveCallout(null)}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#575a75',
              cursor: 'pointer',
              fontSize: '11px',
              fontWeight: 600,
            }}
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Control Tools Bottom Right */}
      <div
        style={{
          position: 'absolute',
          bottom: '20px',
          right: '20px',
          zIndex: 20,
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        <button
          onClick={resetCamera}
          title="Reset 3D Camera"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '4px',
            padding: '6px 12px',
            borderRadius: '6px',
            backgroundColor: 'rgba(255, 255, 255, 0.85)',
            backdropFilter: 'blur(8px)',
            border: '1px solid #ded8c4',
            color: '#282b4a',
            fontSize: '11px',
            fontWeight: 600,
            cursor: 'pointer',
            boxShadow: '0 2px 6px rgba(40, 43, 74, 0.05)',
          }}
        >
          <RotateCcw size={12} />
          <span>Reset View</span>
        </button>

        <div
          style={{
            padding: '6px 12px',
            borderRadius: '6px',
            backgroundColor: 'rgba(255, 255, 255, 0.85)',
            backdropFilter: 'blur(8px)',
            border: '1px solid #ded8c4',
            color: '#575a75',
            fontSize: '10.5px',
            fontWeight: 500,
            boxShadow: '0 2px 6px rgba(40, 43, 74, 0.05)',
          }}
        >
          Drag to rotate • Scroll to zoom
        </div>
      </div>
    </div>
  );
});
