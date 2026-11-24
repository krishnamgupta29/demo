import React, { useEffect, useRef, useState, useCallback, memo } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import {
  TOOTH_MAPPING,
  FDI_TO_MESH_ID,
  MESH_ID_TO_FDI,
  NON_TOOTH_STRUCTURES,
  isToothMesh,
} from './fdiMapping';
import { Finding } from '../../api/types';
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

export interface DentalArchGLTFProps {
  selectedFdi?: number | null;
  onSelectTooth?: (fdi: number) => void;
  findings?: Finding[];
  height?: number | string;
}

const WISDOM_TO_ADJACENT: Record<number, number> = {
  18: 17,
  28: 27,
  38: 37,
  48: 47,
};

export const DentalArchGLTF = memo<DentalArchGLTFProps>(({
  selectedFdi = null,
  onSelectTooth,
  findings = [],
  height = '100%',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const [activeFdi, setActiveFdi] = useState<number | null>(selectedFdi ?? null);
  const [hoveredFdi, setHoveredFdi] = useState<number | null>(null);
  const [studioTheme, setStudioTheme] = useState<'dark' | 'light'>('dark');

  // Anatomy layer toggles: Default gums visible, bones off for clean clinical visibility
  const [showGums, setShowGums] = useState<boolean>(true);
  const [showBones, setShowBones] = useState<boolean>(false);
  const [archFilter, setArchFilter] = useState<'all' | 'upper' | 'lower'>('all');

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const meshMapRef = useRef<Map<string, THREE.Mesh>>(new Map());
  const animFrameIdRef = useRef<number | null>(null);
  const onSelectToothRef = useRef(onSelectTooth);

  useEffect(() => {
    onSelectToothRef.current = onSelectTooth;
  }, [onSelectTooth]);

  useEffect(() => {
    if (selectedFdi !== undefined && selectedFdi !== activeFdi) {
      setActiveFdi(selectedFdi);
    }
  }, [selectedFdi]);

  const findingsMap = React.useMemo(() => {
    const map = new Map<number, Finding[]>();
    findings.forEach((f) => {
      const fdi = f.tooth_fdi;
      if (fdi) {
        const list = map.get(fdi) || [];
        list.push(f);
        map.set(fdi, list);
      }
    });
    return map;
  }, [findings]);

  // Smooth View Controls via OrbitControls
  const resetView = useCallback(() => {
    if (!cameraRef.current || !controlsRef.current) return;
    cameraRef.current.position.set(0.0, 1.2, 4.2);
    controlsRef.current.target.set(0.0, 0.0, 0.0);
    controlsRef.current.update();
  }, []);

  const zoomIn = useCallback(() => {
    if (!cameraRef.current || !controlsRef.current) return;
    const cam = cameraRef.current;
    const target = controlsRef.current.target;
    const offset = cam.position.clone().sub(target);
    const newLen = Math.max(0.5, offset.length() * 0.78);
    offset.setLength(newLen);
    cam.position.copy(target).add(offset);
    controlsRef.current.update();
  }, []);

  const zoomOut = useCallback(() => {
    if (!cameraRef.current || !controlsRef.current) return;
    const cam = cameraRef.current;
    const target = controlsRef.current.target;
    const offset = cam.position.clone().sub(target);
    const newLen = Math.min(10.0, offset.length() * 1.25);
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

    const camera = new THREE.PerspectiveCamera(42, width / heightPx, 0.1, 100);
    camera.position.set(0.0, 1.2, 4.2);
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
    renderer.toneMappingExposure = isDark ? 1.4 : 1.1;
    rendererRef.current = renderer;

    // ─── Three.js Industry-Standard OrbitControls ─────────────────────────────
    const controls = new OrbitControls(camera, canvas);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.rotateSpeed = 0.9;
    controls.zoomSpeed = 1.2;
    controls.panSpeed = 0.8;
    controls.minDistance = 0.4;
    controls.maxDistance = 10.0;
    controls.target.set(0.0, 0.0, 0.0);
    controlsRef.current = controls;

    // Studio Lighting
    const ambientLight = new THREE.AmbientLight(isDark ? 0x2A2E2C : 0xEEEEF2, isDark ? 1.6 : 1.8);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0xFFFBF0, isDark ? 2.8 : 1.8);
    keyLight.position.set(-3.5, 4.0, 4.5);
    keyLight.castShadow = true;
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0xE5F0FF, isDark ? 1.8 : 1.2);
    fillLight.position.set(4.0, 1.5, 3.5);
    scene.add(fillLight);

    const rimLight = new THREE.DirectionalLight(0xFFFFFF, isDark ? 3.2 : 1.5);
    rimLight.position.set(0.0, 4.5, -4.0);
    scene.add(rimLight);

    const rootLight = new THREE.DirectionalLight(0xFFF4E6, isDark ? 1.4 : 0.8);
    rootLight.position.set(0.0, -4.0, 2.0);
    scene.add(rootLight);

    const loader = new GLTFLoader();
    setIsLoading(true);
    setLoadError(null);

    const meshes = new Map<string, THREE.Mesh>();

    loader.load(
      '/models/teeth.glb',
      (gltf) => {
        const root = gltf.scene;

        const teethBox = new THREE.Box3();
        root.traverse((obj) => {
          if ((obj as THREE.Mesh).isMesh && isToothMesh(obj.name)) {
            teethBox.expandByObject(obj);
          }
        });

        const teethCenter = teethBox.getCenter(new THREE.Vector3());
        root.position.set(-teethCenter.x, -teethCenter.y, -teethCenter.z);

        root.traverse((obj) => {
          if ((obj as THREE.Mesh).isMesh) {
            const mesh = obj as THREE.Mesh;
            mesh.castShadow = true;
            mesh.receiveShadow = true;

            const name = mesh.name;
            meshes.set(name, mesh);

            if (NON_TOOTH_STRUCTURES.gums.includes(name)) {
              mesh.visible = showGums;
              mesh.material = new THREE.MeshStandardMaterial({
                color: new THREE.Color(0xB95A64),
                roughness: 0.42,
                metalness: 0.02,
                side: THREE.DoubleSide,
              });
            } else if (NON_TOOTH_STRUCTURES.bones.includes(name)) {
              mesh.visible = showBones;
              mesh.material = new THREE.MeshStandardMaterial({
                color: new THREE.Color(0xD2C8B8),
                roughness: 0.55,
                metalness: 0.0,
                transparent: true,
                opacity: 0.65,
                side: THREE.DoubleSide,
              });
            } else if (name in TOOTH_MAPPING) {
              mesh.visible = true;
              mesh.material = new THREE.MeshPhysicalMaterial({
                color: new THREE.Color(0xFAF7EE),
                roughness: 0.16,
                metalness: 0.0,
                clearcoat: 1.0,
                clearcoatRoughness: 0.05,
                reflectivity: 0.85,
                ior: 1.55,
                side: THREE.DoubleSide,
              });
            }
          }
        });

        // ─── Tareeqa 2: Ghosted Translucent Wisdom Teeth (FDI 18, 28, 38, 48) ────
        const WISDOM_SPECS = [
          { fdi: 18, parentMeshId: 'upper-right-second-molar', meshId: 'upper-right-third-molar', offset: new THREE.Vector3(-0.010, 0.060, -0.105) },
          { fdi: 28, parentMeshId: 'upper-left-second-molar', meshId: 'upper-left-third-molar', offset: new THREE.Vector3(0.002, 0.080, -0.100) },
          { fdi: 38, parentMeshId: 'lower-left-second-molar', meshId: 'lower-left-third-molar', offset: new THREE.Vector3(0.029, 0.105, -0.120) },
          { fdi: 48, parentMeshId: 'lower-right-second-molar', meshId: 'lower-right-third-molar', offset: new THREE.Vector3(-0.009, -0.004, -0.150) },
        ];

        WISDOM_SPECS.forEach((spec) => {
          const parent = meshes.get(spec.parentMeshId);
          if (parent) {
            const ghost = parent.clone();
            ghost.name = spec.meshId;
            ghost.scale.set(0.88, 0.88, 0.88);
            ghost.position.add(spec.offset);
            ghost.material = new THREE.MeshPhysicalMaterial({
              color: new THREE.Color(0xE2E8F0),
              transparent: true,
              opacity: 0.20,
              roughness: 0.15,
              metalness: 0.05,
              transmission: 0.70,
              clearcoat: 1.0,
              side: THREE.DoubleSide,
              depthWrite: false,
            });
            ghost.castShadow = false;
            ghost.receiveShadow = false;
            root.add(ghost);
            meshes.set(spec.meshId, ghost);
          }
        });

        scene.add(root);
        meshMapRef.current = meshes;
        setIsLoading(false);
      },
      undefined,
      (err) => {
        console.error('Failed to load dental arch GLB:', err);
        setLoadError('Failed to load 3D dental model asset.');
        setIsLoading(false);
      }
    );

    // Track mouse down to distinguish between drag and click
    let pointerDownPos = { x: 0, y: 0 };
    const onMouseDown = (e: MouseEvent) => {
      pointerDownPos = { x: e.clientX, y: e.clientY };
    };

    const onMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      const mouse = new THREE.Vector2(
        ((e.clientX - rect.left) / rect.width) * 2 - 1,
        -((e.clientY - rect.top) / rect.height) * 2 + 1
      );

      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(mouse, camera);

      const toothMeshes = Array.from(meshes.entries())
        .filter(([name, m]) => m.visible && name in TOOTH_MAPPING)
        .map(([_, m]) => m);

      const intersects = raycaster.intersectObjects(toothMeshes, false);

      if (intersects.length > 0) {
        const hit = intersects[0].object as THREE.Mesh;
        const fdi = MESH_ID_TO_FDI[hit.name];
        if (fdi) {
          setHoveredFdi(fdi);
        }
      } else {
        setHoveredFdi(null);
      }
    };

    const onMouseUp = (e: MouseEvent) => {
      const dist = Math.hypot(e.clientX - pointerDownPos.x, e.clientY - pointerDownPos.y);
      if (dist < 5) {
        // Genuine click
        const rect = canvas.getBoundingClientRect();
        const mouse = new THREE.Vector2(
          ((e.clientX - rect.left) / rect.width) * 2 - 1,
          -((e.clientY - rect.top) / rect.height) * 2 + 1
        );
        const raycaster = new THREE.Raycaster();
        raycaster.setFromCamera(mouse, camera);

        const toothMeshes = Array.from(meshes.entries())
          .filter(([name, m]) => m.visible && name in TOOTH_MAPPING)
          .map(([_, m]) => m);

        const intersects = raycaster.intersectObjects(toothMeshes, false);
        if (intersects.length > 0) {
          const hit = intersects[0].object as THREE.Mesh;
          const fdi = MESH_ID_TO_FDI[hit.name];
          if (fdi) {
            setActiveFdi(fdi);
            onSelectToothRef.current?.(fdi);
          }
        }
      }
    };

    canvas.addEventListener('mousedown', onMouseDown);
    canvas.addEventListener('mousemove', onMouseMove);
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
      canvas.removeEventListener('mousemove', onMouseMove);
      canvas.removeEventListener('mouseup', onMouseUp);
      window.removeEventListener('resize', handleResize);
      controls.dispose();
      renderer.dispose();
    };
  }, [studioTheme]);

  useEffect(() => {
    if (!containerRef.current || !cameraRef.current || !rendererRef.current) return;
    const w = containerRef.current.clientWidth;
    const h = typeof height === 'number' ? height : containerRef.current.clientHeight;
    if (w && h) {
      cameraRef.current.aspect = w / h;
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(w, h);
    }
  }, [height]);

  useEffect(() => {
    meshMapRef.current.forEach((mesh, name) => {
      if (NON_TOOTH_STRUCTURES.gums.includes(name)) {
        if (!showGums) {
          mesh.visible = false;
          return;
        }
        if (name === 'upper-gum') mesh.visible = archFilter === 'all' || archFilter === 'upper';
        if (name === 'lower-gum') mesh.visible = archFilter === 'all' || archFilter === 'lower';
        return;
      }

      if (NON_TOOTH_STRUCTURES.bones.includes(name)) {
        if (!showBones) {
          mesh.visible = false;
          return;
        }
        if (name === 'right-maxilla' || name === 'left-maxilla') {
          mesh.visible = archFilter === 'all' || archFilter === 'upper';
        } else if (name === 'mandible') {
          mesh.visible = archFilter === 'all' || archFilter === 'lower';
        }
        return;
      }

      const entry = TOOTH_MAPPING[name];
      if (!entry) return;

      const isUpper = entry.isUpper;
      if (archFilter === 'upper' && !isUpper) {
        mesh.visible = false;
        return;
      }
      if (archFilter === 'lower' && isUpper) {
        mesh.visible = false;
        return;
      }
      mesh.visible = true;

      const mat = mesh.material as THREE.MeshPhysicalMaterial;
      const fdi = entry.fdi;
      const isSelected = fdi === activeFdi;
      const isHovered = fdi === hoveredFdi;
      const toothFindings = findingsMap.get(fdi) || [];
      const hasFinding = toothFindings.length > 0;

      const isWisdom = Boolean(entry.isWisdom);

      if (isWisdom) {
        if (isSelected) {
          mat.transparent = false;
          mat.opacity = 1.0;
          mat.depthWrite = true;
          mat.transmission = 0.0;
          mat.color.setHex(0x0284C7);
          mat.emissive.setHex(0x38BDF8);
          mat.emissiveIntensity = 0.85;
        } else if (isHovered) {
          mat.transparent = false;
          mat.opacity = 1.0;
          mat.depthWrite = true;
          mat.transmission = 0.0;
          mat.color.setHex(0x10B981);
          mat.emissive.setHex(0x059669);
          mat.emissiveIntensity = 0.50;
        } else if (hasFinding) {
          mat.transparent = true;
          mat.opacity = 0.80;
          mat.depthWrite = true;
          mat.transmission = 0.25;
          mat.color.setHex(0xFACC15);
          mat.emissive.setHex(0xF59E0B);
          mat.emissiveIntensity = 0.75;
        } else {
          mat.transparent = true;
          mat.depthWrite = false;
          mat.roughness = 0.15;
          mat.transmission = 0.70;
          mat.color.setHex(0xE2E8F0);
          mat.emissive.setHex(0x000000);
          mat.emissiveIntensity = 0.0;
          mat.opacity = 0.18;
        }
      } else {
        mat.transparent = false;
        mat.opacity = 1.0;
        mat.depthWrite = true;
        if (hasFinding) {
          // ALL teeth with report-included findings MUST highlight simultaneously in bright yellow (#FACC15).
          // Selection must NOT hide the yellow finding indicator.
          mat.color.setHex(0xFACC15); // bright yellow (#FACC15)
          if (isSelected) {
            // Selected tooth with finding: high-intensity vibrant gold glow + pulse
            mat.emissive.setHex(0xF59E0B); // amber-500 emissive
            mat.emissiveIntensity = 0.95;
          } else if (isHovered) {
            mat.emissive.setHex(0xFDE047); // yellow-300
            mat.emissiveIntensity = 0.75;
          } else {
            mat.emissive.setHex(0xEAB308); // yellow-500
            mat.emissiveIntensity = 0.55;
          }
        } else if (isSelected) {
          // Selected tooth without finding: distinct deep indigo / slate focus (#282b4a accent)
          mat.color.setHex(0x3F436C);
          mat.emissive.setHex(0x282B4A);
          mat.emissiveIntensity = 0.80;
        } else if (isHovered) {
          mat.color.setHex(0x10B981);
          mat.emissive.setHex(0x059669);
          mat.emissiveIntensity = 0.40;
        } else {
          mat.color.setHex(0xFAF7EE);
          mat.emissive.setHex(0x000000);
          mat.emissiveIntensity = 0.0;
        }
      }
    });
  }, [activeFdi, hoveredFdi, findingsMap, showGums, showBones, archFilter]);

  const isDark = studioTheme === 'dark';
  const selectedToothMeshId = activeFdi ? FDI_TO_MESH_ID[activeFdi] : undefined;
  const selectedToothEntry = selectedToothMeshId ? TOOTH_MAPPING[selectedToothMeshId] : undefined;
  const activeToothFindings = activeFdi ? findingsMap.get(activeFdi) || [] : [];

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
    >      <canvas ref={canvasRef} style={{ width: '100%', height: '100%', display: 'block', cursor: 'grab' }} />

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
            <span>Loading 3D Anatomy Model...</span>
          </div>
        </div>
      )}

      {/* ─── Compact Controls: Reset, Zoom, Gums, Bone, Theme ─────────────── */}
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
          title="Reset 3D Angle"
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
          title="Zoom In (or scroll wheel)"
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
          title="Zoom Out (or scroll wheel)"
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

        {/* Gums (Masoode) Toggle */}
        <button
          onClick={() => setShowGums(!showGums)}
          title="Toggle Gums (Gingiva)"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '3px',
            padding: '2.5px 7px',
            fontSize: '10.5px',
            fontWeight: 500,
            borderRadius: '4px',
            border: showGums ? '1px solid rgba(244, 63, 94, 0.4)' : '1px solid transparent',
            cursor: 'pointer',
            backgroundColor: showGums ? 'rgba(159, 18, 57, 0.65)' : 'rgba(30, 41, 59, 0.7)',
            color: showGums ? '#FECDD3' : '#94A3B8',
          }}
        >
          {showGums ? <Eye style={{ width: 11, height: 11, color: '#FDA4AF' }} /> : <EyeOff style={{ width: 11, height: 11 }} />}
          <span>Gums</span>
        </button>

        {/* Jaw Bone Toggle */}
        <button
          onClick={() => setShowBones(!showBones)}
          title="Toggle Jaw Bone (Maxilla & Mandible)"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '3px',
            padding: '2.5px 7px',
            fontSize: '10.5px',
            fontWeight: 500,
            borderRadius: '4px',
            border: showBones ? '1px solid rgba(245, 158, 11, 0.4)' : '1px solid transparent',
            cursor: 'pointer',
            backgroundColor: showBones ? 'rgba(180, 83, 9, 0.65)' : 'rgba(30, 41, 59, 0.7)',
            color: showBones ? '#FDE68A' : '#94A3B8',
          }}
        >
          {showBones ? <Eye style={{ width: 11, height: 11, color: '#FCD34D' }} /> : <EyeOff style={{ width: 11, height: 11 }} />}
          <span>Bone</span>
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

      {/* Dynamic Selected Tooth Clinical Indicator Banner (Shows for EVERY selected tooth) */}
      {activeFdi && selectedToothEntry ? (
        <div
          style={{
            position: 'absolute',
            bottom: 8,
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: 'rgba(10, 15, 20, 0.92)',
            backdropFilter: 'blur(8px)',
            color: '#FFFFFF',
            border: selectedToothEntry.isWisdom
              ? '1px solid rgba(56, 189, 248, 0.5)'
              : activeToothFindings.length > 0
              ? '1px solid rgba(245, 158, 11, 0.5)'
              : '1px solid rgba(59, 130, 246, 0.4)',
            padding: '3px 10px',
            borderRadius: '5px',
            fontSize: '10.5px',
            fontWeight: 500,
            zIndex: 25,
            pointerEvents: 'none',
            whiteSpace: 'nowrap',
            boxShadow: '0 4px 12px rgba(0,0,0,0.45)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
          }}
        >
          {/* FDI Tag Pill */}
          <span
            style={{
              backgroundColor: selectedToothEntry.isWisdom ? '#0284C7' : '#2563EB',
              color: '#FFFFFF',
              fontWeight: 700,
              padding: '1px 5px',
              borderRadius: '3px',
              fontSize: '10px',
            }}
          >
            FDI #{activeFdi}
          </span>

          {/* Anatomical Name */}
          <span style={{ color: '#F1F5F9', fontWeight: 600 }}>
            {selectedToothEntry.name}
          </span>

          {/* Wisdom Tag if applicable */}
          {selectedToothEntry.isWisdom && (
            <span style={{ color: '#38BDF8', fontSize: '9.5px', fontStyle: 'italic' }}>
              (Ghosted 3D)
            </span>
          )}

          {/* Finding Status */}
          {activeToothFindings.length > 0 ? (
            <span
              style={{
                color: '#FCD34D',
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: '3px',
              }}
            >
              • {activeToothFindings.map((f) => `${f.pathology_class.replace(/_/g, ' ')} (${Math.round((f.confidence || 0) * 100)}%)`).join(', ')}
            </span>
          ) : (
            <span style={{ color: '#94A3B8', fontSize: '10px' }}>
              • Healthy Reference
            </span>
          )}
        </div>
      ) : (
        <div
          style={{
            position: 'absolute',
            bottom: 8,
            left: '50%',
            transform: 'translateX(-50%)',
            backgroundColor: 'rgba(10, 15, 20, 0.85)',
            backdropFilter: 'blur(8px)',
            color: '#94A3B8',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            padding: '3px 12px',
            borderRadius: '5px',
            fontSize: '10px',
            fontWeight: 500,
            zIndex: 25,
            pointerEvents: 'none',
            whiteSpace: 'nowrap',
          }}
        >
          Select a tooth or finding to inspect
        </div>
      )}
    </div>
  );
});

DentalArchGLTF.displayName = 'DentalArchGLTF';
