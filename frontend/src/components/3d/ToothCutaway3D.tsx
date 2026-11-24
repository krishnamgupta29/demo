import React, { useEffect, useRef, useState, useCallback, memo } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import {
  RotateCcw,
  Moon,
  Sun,
  Eye,
  EyeOff,
  Sparkles,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';

export interface ToothCutaway3DProps {
  height?: number | string;
  selectedPathology?: string;
  selectedFdi?: number | null;
  onSelectAnatomicalStructure?: (structure: string) => void;
  activeAnatomicalStructure?: string | null;
}

interface AnatomicalStructureMeta {
  id: string;
  name: string;
  category: 'enamel' | 'dentin' | 'cementum' | 'pdl' | 'pulp' | 'canal';
  colorHex: number;
  description: string;
}

const CUTAWAY_STRUCTURES: Record<string, AnatomicalStructureMeta> = {
  'enamel-16': {
    id: 'enamel-16',
    name: 'Crown Enamel',
    category: 'enamel',
    colorHex: 0xF5F2E8,
    description: 'Acellular, 96% mineralized hydroxyapatite outer protective layer of the crown.',
  },
  'dentin-coronal-16': {
    id: 'dentin-coronal-16',
    name: 'Coronal Dentin',
    category: 'dentin',
    colorHex: 0xE5D3A3,
    description: 'Mineralized tissue underlying crown enamel containing microscopic dentinal tubules.',
  },
  'dentin-radicular-16': {
    id: 'dentin-radicular-16',
    name: 'Radicular (Root) Dentin',
    category: 'dentin',
    colorHex: 0xD1BD84,
    description: 'Sub-cervical dentin bulk encasing the root canal system down to the apex.',
  },
  'cementum-16': {
    id: 'cementum-16',
    name: 'Root Cementum',
    category: 'cementum',
    colorHex: 0xBFA673,
    description: 'Specialized calcified connective tissue covering root dentin, anchoring Sharpey fibers.',
  },
  'pdl-16': {
    id: 'pdl-16',
    name: 'Periodontal Ligament (PDL)',
    category: 'pdl',
    colorHex: 0xE5989B,
    description: 'Fibrous connective tissue bundle suspending the tooth root within alveolar bone.',
  },
  'pulp-chamber-16': {
    id: 'pulp-chamber-16',
    name: 'Pulp Chamber (Coronal)',
    category: 'pulp',
    colorHex: 0xDC2626,
    description: 'Vascular and neural core containing odontoblasts, fibroblasts, and capillaries.',
  },
  'canal-distobuccal-16': {
    id: 'canal-distobuccal-16',
    name: 'Distobuccal Root Canal',
    category: 'canal',
    colorHex: 0xB91C1C,
    description: 'Posterior-buccal endodontic canal conduit supplying nerves and blood vessels.',
  },
  'canal-palatal-16': {
    id: 'canal-palatal-16',
    name: 'Palatal Root Canal',
    category: 'canal',
    colorHex: 0xB91C1C,
    description: 'Largest single canal in maxillary 1st molar, oriented palatally towards the roof of mouth.',
  },
  'canal-mesiobuccal-1-16': {
    id: 'canal-mesiobuccal-1-16',
    name: 'Mesiobuccal Canal 1 (MB1)',
    category: 'canal',
    colorHex: 0xB91C1C,
    description: 'Primary anterior-buccal canal pathway traversing the mesiobuccal root.',
  },
  'canal-mesiobuccal-2-16': {
    id: 'canal-mesiobuccal-2-16',
    name: 'Mesiobuccal Canal 2 (MB2)',
    category: 'canal',
    colorHex: 0xB91C1C,
    description: 'Secondary accessory MB canal (present in >70% of maxillary molars; critical in endodontics).',
  },
};

// Canonical educational anatomical structure map (8 clinical structures)
const EDUCATIONAL_STRUCTURES: { id: string; name: string; description: string }[] = [
  { id: 'enamel', name: 'Enamel', description: 'Acellular, 96% mineralized hydroxyapatite outer protective layer of the crown.' },
  { id: 'dentin', name: 'Dentin', description: 'Mineralized tissue underlying enamel containing microscopic dentinal tubules.' },
  { id: 'pulp_chamber', name: 'Pulp Chamber', description: 'Vascular and neural core containing odontoblasts, fibroblasts, and capillaries.' },
  { id: 'root_canal', name: 'Root Canal', description: 'Endodontic canal conduit supplying nerves and blood vessels through the root.' },
  { id: 'cementum', name: 'Cementum', description: 'Specialized calcified connective tissue covering root dentin, anchoring Sharpey fibers.' },
  { id: 'periodontal_ligament', name: 'Periodontal Ligament', description: 'Fibrous connective tissue bundle suspending the tooth root within alveolar bone.' },
  { id: 'root_apex', name: 'Root Apex', description: 'Terminal endpoint of the root housing the apical foramen where neurovascular bundle enters.' },
  { id: 'periapical_region', name: 'Periapical Region', description: 'Surrounding bone and soft tissue at the root apex; site of periapical pathology.' },
];

export const ToothCutaway3D = memo<ToothCutaway3DProps>(({
  height = '100%',
  selectedPathology,
  selectedFdi = null,
  onSelectAnatomicalStructure,
  activeAnatomicalStructure,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const [studioTheme, setStudioTheme] = useState<'dark' | 'light'>('dark');
  const [selectedStructureId, setSelectedStructureId] = useState<string>('pulp-chamber-16');
  const [hoveredStructureId, setHoveredStructureId] = useState<string | null>(null);

  // Layer visibility toggles
  const [showEnamel, setShowEnamel] = useState<boolean>(true);
  const [showDentin, setShowDentin] = useState<boolean>(true);
  const [showPDL, setShowPDL] = useState<boolean>(false);
  const [showPulp, setShowPulp] = useState<boolean>(true);

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const meshMapRef = useRef<Map<string, THREE.Mesh>>(new Map());
  const animFrameIdRef = useRef<number | null>(null);

  const resetView = useCallback(() => {
    if (!cameraRef.current || !controlsRef.current) return;
    cameraRef.current.position.set(2.4, 1.4, 2.6);
    controlsRef.current.target.set(0, 0, 0);
    controlsRef.current.update();
  }, []);

  const zoomIn = useCallback(() => {
    if (!cameraRef.current || !controlsRef.current) return;
    const cam = cameraRef.current;
    const target = controlsRef.current.target;
    const offset = cam.position.clone().sub(target);
    const newLen = Math.max(0.4, offset.length() * 0.78);
    offset.setLength(newLen);
    cam.position.copy(target).add(offset);
    controlsRef.current.update();
  }, []);

  const zoomOut = useCallback(() => {
    if (!cameraRef.current || !controlsRef.current) return;
    const cam = cameraRef.current;
    const target = controlsRef.current.target;
    const offset = cam.position.clone().sub(target);
    const newLen = Math.min(8.5, offset.length() * 1.25);
    offset.setLength(newLen);
    cam.position.copy(target).add(offset);
    controlsRef.current.update();
  }, []);

  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    const isDark = studioTheme === 'dark';
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(isDark ? 0x0A0D0C : 0xF6F8F7);
    sceneRef.current = scene;

    const width = container.clientWidth || 400;
    const heightPx = typeof height === 'number' ? height : container.clientHeight || 320;

    const camera = new THREE.PerspectiveCamera(36, width / heightPx, 0.1, 100);
    camera.position.set(2.4, 1.4, 2.6);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: false,
      powerPreference: 'high-performance',
      preserveDrawingBuffer: true,
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2.0));
    renderer.setSize(width, heightPx);
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = isDark ? 1.45 : 1.15;
    rendererRef.current = renderer;

    // ─── Three.js Industry-Standard OrbitControls ─────────────────────────────
    const controls = new OrbitControls(camera, canvas);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.rotateSpeed = 0.9;
    controls.zoomSpeed = 1.2;
    controls.panSpeed = 0.8;
    controls.minDistance = 0.4;
    controls.maxDistance = 8.5;
    controls.target.set(0.0, 0.0, 0.0);
    controlsRef.current = controls;

    const ambientLight = new THREE.AmbientLight(isDark ? 0x2A2E2C : 0xEEEEF2, isDark ? 1.6 : 1.8);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xFFFBF0, isDark ? 3.0 : 1.8);
    keyLight.position.set(-3.0, 4.0, 3.5);
    keyLight.castShadow = true;
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0xE5F0FF, isDark ? 2.0 : 1.2);
    fillLight.position.set(3.5, 2.0, 3.0);
    scene.add(fillLight);

    const rimLight = new THREE.DirectionalLight(0xFFFFFF, isDark ? 3.2 : 1.5);
    rimLight.position.set(0.0, 4.0, -3.5);
    scene.add(rimLight);

    const bottomLight = new THREE.DirectionalLight(0xFFE8D6, isDark ? 1.4 : 0.8);
    bottomLight.position.set(0.0, -3.5, 1.5);
    scene.add(bottomLight);

    const loader = new GLTFLoader();
    setIsLoading(true);
    setLoadError(null);

    const meshes = new Map<string, THREE.Mesh>();

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

            const meta = CUTAWAY_STRUCTURES[name];
            if (meta) {
              if (meta.category === 'enamel') {
                mesh.visible = showEnamel;
                mesh.material = new THREE.MeshPhysicalMaterial({
                  color: new THREE.Color(meta.colorHex),
                  roughness: 0.14,
                  metalness: 0.0,
                  clearcoat: 1.0,
                  clearcoatRoughness: 0.05,
                  transparent: true,
                  opacity: 0.85,
                  transmission: 0.25,
                  ior: 1.56,
                  side: THREE.DoubleSide,
                });
              } else if (meta.category === 'dentin' || meta.category === 'cementum') {
                mesh.visible = showDentin;
                mesh.material = new THREE.MeshStandardMaterial({
                  color: new THREE.Color(meta.colorHex),
                  roughness: 0.38,
                  metalness: 0.0,
                  side: THREE.DoubleSide,
                });
              } else if (meta.category === 'pdl') {
                mesh.visible = showPDL;
                mesh.material = new THREE.MeshStandardMaterial({
                  color: new THREE.Color(meta.colorHex),
                  roughness: 0.45,
                  metalness: 0.0,
                  transparent: true,
                  opacity: 0.60,
                  side: THREE.DoubleSide,
                });
              } else if (meta.category === 'pulp' || meta.category === 'canal') {
                mesh.visible = showPulp;
                mesh.material = new THREE.MeshPhysicalMaterial({
                  color: new THREE.Color(meta.colorHex),
                  emissive: new THREE.Color(0x7F1D1D),
                  emissiveIntensity: 0.35,
                  roughness: 0.22,
                  clearcoat: 0.6,
                  side: THREE.DoubleSide,
                });
              }
            }
          }
        });

        scene.add(root);
        meshMapRef.current = meshes;
        setIsLoading(false);
      },
      undefined,
      (err) => {
        console.error('Failed to load cutaway tooth GLB:', err);
        setLoadError('Failed to load 3D tooth cutaway asset.');
        setIsLoading(false);
      }
    );

    let pointerDownPos = { x: 0, y: 0 };
    const onMouseDown = (e: MouseEvent) => {
      pointerDownPos = { x: e.clientX, y: e.clientY };
    };

    const onMouseUp = (e: MouseEvent) => {
      const dist = Math.hypot(e.clientX - pointerDownPos.x, e.clientY - pointerDownPos.y);
      if (dist < 5) {
        const rect = canvas.getBoundingClientRect();
        const mouse = new THREE.Vector2(
          ((e.clientX - rect.left) / rect.width) * 2 - 1,
          -((e.clientY - rect.top) / rect.height) * 2 + 1
        );
        const raycaster = new THREE.Raycaster();
        raycaster.setFromCamera(mouse, camera);

        const visibleMeshes = Array.from(meshes.values()).filter((m) => m.visible);
        const intersects = raycaster.intersectObjects(visibleMeshes, false);
        if (intersects.length > 0) {
          const hit = intersects[0].object as THREE.Mesh;
          setSelectedStructureId(hit.name);
        }
      }
    };

    canvas.addEventListener('mousedown', onMouseDown);
    canvas.addEventListener('mouseup', onMouseUp);

    const animate = () => {
      animFrameIdRef.current = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    const handleResize = () => {
      if (!container || !camera || !renderer) return;
      const w = container.clientWidth;
      const h = typeof height === 'number' ? height : container.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      if (animFrameIdRef.current) cancelAnimationFrame(animFrameIdRef.current);
      canvas.removeEventListener('mousedown', onMouseDown);
      canvas.removeEventListener('mouseup', onMouseUp);
      window.removeEventListener('resize', handleResize);
      controls.dispose();
      renderer.dispose();
    };
  }, [studioTheme, height]);

  useEffect(() => {
    meshMapRef.current.forEach((mesh, name) => {
      const meta = CUTAWAY_STRUCTURES[name];
      if (!meta) return;

      if (meta.category === 'enamel') mesh.visible = showEnamel;
      else if (meta.category === 'dentin' || meta.category === 'cementum') mesh.visible = showDentin;
      else if (meta.category === 'pdl') mesh.visible = showPDL;
      else if (meta.category === 'pulp' || meta.category === 'canal') mesh.visible = showPulp;

      if (!mesh.visible) return;

      const isSelected = name === selectedStructureId;
      const isHovered = name === hoveredStructureId;

      const pathLower = (selectedPathology || '').toLowerCase();
      const isCariesTarget = (pathLower.includes('caries') && !pathLower.includes('deep')) && (meta.category === 'enamel' || name === 'dentin-coronal-16');
      const isDeepCariesTarget = pathLower.includes('deep') && (name === 'dentin-coronal-16' || meta.category === 'pulp');
      const isPeriapicalTarget = pathLower.includes('periapical') && (meta.category === 'cementum' || meta.category === 'pdl' || name === 'dentin-radicular-16' || meta.category === 'canal');

      if (mesh.material instanceof THREE.MeshStandardMaterial || mesh.material instanceof THREE.MeshPhysicalMaterial) {
        if (isSelected) {
          mesh.material.emissive.setHex(0x2563EB);
          mesh.material.emissiveIntensity = 0.50;
        } else if (isHovered) {
          mesh.material.emissive.setHex(0x10B981);
          mesh.material.emissiveIntensity = 0.35;
        } else if (isCariesTarget) {
          mesh.material.emissive.setHex(0xD97706);
          mesh.material.emissiveIntensity = 0.45;
        } else if (isDeepCariesTarget) {
          mesh.material.emissive.setHex(0xB91C1C);
          mesh.material.emissiveIntensity = 0.50;
        } else if (isPeriapicalTarget) {
          mesh.material.emissive.setHex(0xDC2626);
          mesh.material.emissiveIntensity = 0.45;
        } else if (meta.category === 'pulp' || meta.category === 'canal') {
          mesh.material.emissive.setHex(0x7F1D1D);
          mesh.material.emissiveIntensity = 0.35;
        } else {
          mesh.material.emissive.setHex(0x000000);
          mesh.material.emissiveIntensity = 0.0;
        }
      }
    });
  }, [selectedStructureId, hoveredStructureId, showEnamel, showDentin, showPDL, showPulp, selectedPathology]);

  const isDark = studioTheme === 'dark';

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        width: '100%',
        height: typeof height === 'number' ? `${height}px` : height,
        backgroundColor: isDark ? '#0A0D0C' : '#F6F8F7',
        color: isDark ? '#FFFFFF' : '#111827',
        userSelect: 'none',
        overflow: 'hidden',
      }}
    >
      <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block', cursor: 'grab' }} />

      {/* Loading Overlay */}
      {isLoading && (
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            backgroundColor: 'rgba(0, 0, 0, 0.5)',
            backdropFilter: 'blur(4px)',
            zIndex: 25,
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 14px',
              backgroundColor: '#1E293B',
              borderRadius: '8px',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              fontSize: '12px',
              color: '#FFFFFF',
            }}
          >
            <Sparkles style={{ width: 16, height: 16, color: '#38BDF8' }} />
            <span>Loading Cutaway Tooth Anatomy...</span>
          </div>
        </div>
      )}

      {/* ─── ROW 2: Layer Toggles & Zoom Controls ─────────────────────────── */}
      <div
        style={{
          position: 'absolute',
          top: 44,
          left: 8,
          display: 'flex',
          alignItems: 'center',
          gap: '3px',
          backgroundColor: 'rgba(10, 15, 14, 0.85)',
          backdropFilter: 'blur(8px)',
          padding: '3px 5px',
          borderRadius: '7px',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          zIndex: 25,
          boxShadow: '0 2px 8px rgba(0, 0, 0, 0.35)',
        }}
      >
        {/* Reset View */}
        <button
          onClick={resetView}
          title="Reset to Default Angle"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '3px',
            padding: '2.5px 6px',
            fontSize: '10.5px',
            fontWeight: 600,
            borderRadius: '4px',
            border: 'none',
            cursor: 'pointer',
            backgroundColor: 'rgba(30, 41, 59, 0.8)',
            color: '#CBD5E1',
          }}
        >
          <RotateCcw style={{ width: 11, height: 11 }} />
          <span>Reset</span>
        </button>

        <span style={{ width: '1px', height: '12px', backgroundColor: 'rgba(255, 255, 255, 0.2)', margin: '0 2px' }} />

        {/* Zoom In (+) */}
        <button
          onClick={zoomIn}
          title="Zoom In (Scroll Up)"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '2px',
            padding: '2.5px 6px',
            fontSize: '10.5px',
            fontWeight: 600,
            borderRadius: '4px',
            border: 'none',
            cursor: 'pointer',
            backgroundColor: 'rgba(30, 41, 59, 0.8)',
            color: '#38BDF8',
          }}
        >
          <ZoomIn style={{ width: 11, height: 11 }} />
          <span>+</span>
        </button>

        {/* Zoom Out (-) */}
        <button
          onClick={zoomOut}
          title="Zoom Out (Scroll Down)"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '2px',
            padding: '2.5px 6px',
            fontSize: '10.5px',
            fontWeight: 600,
            borderRadius: '4px',
            border: 'none',
            cursor: 'pointer',
            backgroundColor: 'rgba(30, 41, 59, 0.8)',
            color: '#38BDF8',
          }}
        >
          <ZoomOut style={{ width: 11, height: 11 }} />
          <span>-</span>
        </button>

        <span style={{ width: '1px', height: '12px', backgroundColor: 'rgba(255, 255, 255, 0.2)', margin: '0 2px' }} />

        {/* Enamel Toggle */}
        <button
          onClick={() => setShowEnamel(!showEnamel)}
          title="Toggle Enamel Shell"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '3px',
            padding: '2.5px 7px',
            fontSize: '10.5px',
            fontWeight: 500,
            borderRadius: '4px',
            border: 'none',
            cursor: 'pointer',
            backgroundColor: showEnamel ? 'rgba(51, 65, 85, 0.9)' : 'rgba(15, 23, 42, 0.7)',
            color: showEnamel ? '#FFFFFF' : '#64748B',
          }}
        >
          {showEnamel ? <Eye style={{ width: 11, height: 11, color: '#38BDF8' }} /> : <EyeOff style={{ width: 11, height: 11 }} />}
          <span>Enamel</span>
        </button>

        {/* Dentin Toggle */}
        <button
          onClick={() => setShowDentin(!showDentin)}
          title="Toggle Dentin & Cementum"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '3px',
            padding: '2.5px 7px',
            fontSize: '10.5px',
            fontWeight: 500,
            borderRadius: '4px',
            border: 'none',
            cursor: 'pointer',
            backgroundColor: showDentin ? 'rgba(51, 65, 85, 0.9)' : 'rgba(15, 23, 42, 0.7)',
            color: showDentin ? '#FFFFFF' : '#64748B',
          }}
        >
          {showDentin ? <Eye style={{ width: 11, height: 11, color: '#FBBF24' }} /> : <EyeOff style={{ width: 11, height: 11 }} />}
          <span>Dentin</span>
        </button>

        {/* Pulp & Canal Toggle */}
        <button
          onClick={() => setShowPulp(!showPulp)}
          title="Toggle Pulp Chamber & Root Canals"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '3px',
            padding: '2.5px 7px',
            fontSize: '10.5px',
            fontWeight: 500,
            borderRadius: '4px',
            border: showPulp ? '1px solid rgba(244, 63, 94, 0.4)' : '1px solid transparent',
            cursor: 'pointer',
            backgroundColor: showPulp ? 'rgba(136, 19, 55, 0.65)' : 'rgba(15, 23, 42, 0.7)',
            color: showPulp ? '#FECDD3' : '#64748B',
          }}
        >
          {showPulp ? <Eye style={{ width: 11, height: 11, color: '#FB7185' }} /> : <EyeOff style={{ width: 11, height: 11 }} />}
          <span>Pulp</span>
        </button>

        {/* PDL Toggle */}
        <button
          onClick={() => setShowPDL(!showPDL)}
          title="Toggle Periodontal Ligament (PDL)"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '3px',
            padding: '2.5px 7px',
            fontSize: '10.5px',
            fontWeight: 500,
            borderRadius: '4px',
            border: 'none',
            cursor: 'pointer',
            backgroundColor: showPDL ? 'rgba(51, 65, 85, 0.9)' : 'rgba(15, 23, 42, 0.7)',
            color: showPDL ? '#FFFFFF' : '#64748B',
          }}
        >
          {showPDL ? <Eye style={{ width: 11, height: 11, color: '#F472B6' }} /> : <EyeOff style={{ width: 11, height: 11 }} />}
          <span>PDL</span>
        </button>

        <span style={{ width: '1px', height: '12px', backgroundColor: 'rgba(255, 255, 255, 0.2)', margin: '0 2px' }} />

        {/* Dark / Light Studio Toggle */}
        <button
          onClick={() => setStudioTheme(studioTheme === 'dark' ? 'light' : 'dark')}
          title="Toggle Studio Theme"
          style={{
            padding: '3px',
            backgroundColor: 'transparent',
            border: 'none',
            color: '#CBD5E1',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          {studioTheme === 'dark' ? <Sun style={{ width: 12, height: 12 }} /> : <Moon style={{ width: 12, height: 12 }} />}
        </button>
      </div>

      {/* Right Structure Quick-List: Internal Layers */}
      <div
        style={{
          position: 'absolute',
          right: 8,
          bottom: 8,
          top: 48,
          display: 'flex',
          flexDirection: 'column',
          gap: '2px',
          overflowY: 'auto',
          maxWidth: '155px',
          pointerEvents: 'auto',
          zIndex: 20,
        }}
      >
        <div style={{ fontSize: '9.5px', textTransform: 'uppercase', fontWeight: 700, color: '#94A3B8', padding: '0 4px', marginBottom: '1px' }}>
          Internal Layers
        </div>
        {Object.values(CUTAWAY_STRUCTURES).map((item) => {
          const isSelected = item.id === selectedStructureId;
          return (
            <button
              key={item.id}
              onClick={() => setSelectedStructureId(item.id)}
              style={{
                textAlign: 'left',
                padding: '3px 6px',
                borderRadius: '4px',
                fontSize: '10px',
                border: isSelected ? '1px solid rgba(14, 165, 233, 0.5)' : '1px solid rgba(255, 255, 255, 0.08)',
                backgroundColor: isSelected ? 'rgba(14, 165, 233, 0.25)' : 'rgba(10, 15, 14, 0.75)',
                color: isSelected ? '#38BDF8' : '#CBD5E1',
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                transition: 'all 0.15s',
              }}
            >
              {item.name}
            </button>
          );
        })}
      </div>
    </div>
  );
});

ToothCutaway3D.displayName = 'ToothCutaway3D';
