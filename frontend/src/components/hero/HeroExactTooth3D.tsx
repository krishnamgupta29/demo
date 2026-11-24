import React, { useEffect, useRef, memo } from 'react';
import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { buildAnatomicalToothGeometry } from '../3d/anatomicalToothBuilder';
import { TEETH_DATA } from '../3d/toothData';

export interface HeroExactTooth3DProps {
  theme?: 'light' | 'dark';
  width?: number | string;
  height?: number | string;
}

export const HeroExactTooth3D = memo<HeroExactTooth3DProps>(({
  theme = 'dark',
  width = '100%',
  height = '100%',
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const toothGroupRef = useRef<THREE.Group | null>(null);
  const ring1Ref = useRef<THREE.Mesh | null>(null);
  const ring2Ref = useRef<THREE.Mesh | null>(null);
  const animFrameIdRef = useRef<number | null>(null);
  const lastUserInteractionRef = useRef<number>(Date.now());

  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;

    const w = container.clientWidth || 360;
    const h = container.clientHeight || 260;

    const scene = new THREE.Scene();
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(30, w / h, 0.1, 50);
    camera.position.set(2.4, 0.8, 2.8);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
      powerPreference: 'high-performance',
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2.0));
    renderer.setSize(w, h);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = theme === 'dark' ? 1.4 : 1.25;
    rendererRef.current = renderer;

    const controls = new OrbitControls(camera, canvas);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.rotateSpeed = 0.8;
    controls.zoomSpeed = 0.8;
    controls.enablePan = false;
    controls.minDistance = 1.6;
    controls.maxDistance = 5.0;
    controls.target.set(0, 0, 0);
    controlsRef.current = controls;

    controls.addEventListener('start', () => {
      lastUserInteractionRef.current = Date.now();
    });
    controls.addEventListener('end', () => {
      lastUserInteractionRef.current = Date.now();
    });

    // ─── Studio Lighting ─────────────────────────────────────────────────────
    const isDark = theme === 'dark';

    // Ambient
    const ambientLight = new THREE.AmbientLight(
      isDark ? 0x2A324B : 0xFFFAF0,
      isDark ? 1.8 : 2.2
    );
    scene.add(ambientLight);

    // Key Light
    const keyLight = new THREE.DirectionalLight(0xFFFEF7, isDark ? 3.6 : 3.0);
    keyLight.position.set(-3.2, 4.0, 3.5);
    scene.add(keyLight);

    // Rim Light (Accentuates tooth contour)
    const rimLight = new THREE.DirectionalLight(
      isDark ? 0xFDE047 : 0xCBD5E1,
      isDark ? 2.8 : 1.6
    );
    rimLight.position.set(3.5, 3.0, -3.5);
    scene.add(rimLight);

    // Warm Under-glow
    const underLight = new THREE.DirectionalLight(
      isDark ? 0xEAB308 : 0xF5E6C8,
      isDark ? 1.4 : 0.8
    );
    underLight.position.set(0, -3.5, 1.5);
    scene.add(underLight);

    // ─── 3D Orbital Rings ───────────────────────────────────────────────────
    const ring1Geom = new THREE.TorusGeometry(1.42, 0.013, 16, 120);
    const ring1Mat = new THREE.MeshStandardMaterial({
      color: isDark ? 0xFDE047 : 0x282B4A,
      emissive: isDark ? 0xF59E0B : 0x000000,
      emissiveIntensity: isDark ? 0.85 : 0.0,
      roughness: 0.25,
      metalness: 0.85,
    });
    const ring1 = new THREE.Mesh(ring1Geom, ring1Mat);
    ring1.rotation.x = Math.PI * 0.42;
    ring1.rotation.y = Math.PI * 0.12;
    scene.add(ring1);
    ring1Ref.current = ring1;

    const ring2Geom = new THREE.TorusGeometry(1.68, 0.013, 16, 120);
    const ring2Mat = new THREE.MeshStandardMaterial({
      color: isDark ? 0xFEF08A : 0x383C64,
      emissive: isDark ? 0xCA8A04 : 0x000000,
      emissiveIntensity: isDark ? 0.65 : 0.0,
      roughness: 0.3,
      metalness: 0.8,
    });
    const ring2 = new THREE.Mesh(ring2Geom, ring2Mat);
    ring2.rotation.x = -Math.PI * 0.38;
    ring2.rotation.y = -Math.PI * 0.16;
    scene.add(ring2);
    ring2Ref.current = ring2;

    // ─── Tooth Model Setup ───────────────────────────────────────────────────
    const rootGroup = new THREE.Group();
    scene.add(rootGroup);
    toothGroupRef.current = rootGroup;

    const setupProceduralMolar = () => {
      const meta = TEETH_DATA.find((t) => t.fdi === 16) || TEETH_DATA[0];
      const geom = buildAnatomicalToothGeometry(meta);

      const enamelMat = new THREE.MeshPhysicalMaterial({
        color: new THREE.Color(0xFFFEF8),
        roughness: 0.12,
        metalness: 0.0,
        clearcoat: 1.0,
        clearcoatRoughness: 0.04,
        transmission: 0.18,
        ior: 1.54,
        side: THREE.DoubleSide,
      });

      const mesh = new THREE.Mesh(geom, enamelMat);
      geom.computeBoundingBox();
      const center = geom.boundingBox?.getCenter(new THREE.Vector3()) || new THREE.Vector3();
      mesh.position.sub(center);
      mesh.scale.set(0.95, 0.95, 0.95);
      rootGroup.add(mesh);
    };

    const loader = new GLTFLoader();
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
            mesh.material = new THREE.MeshPhysicalMaterial({
              color: new THREE.Color(0xFFFEF8),
              roughness: 0.12,
              metalness: 0.0,
              clearcoat: 1.0,
              clearcoatRoughness: 0.04,
              transmission: 0.20,
              ior: 1.56,
              side: THREE.DoubleSide,
            });
          }
        });

        root.scale.set(0.92, 0.92, 0.92);
        rootGroup.add(root);
      },
      undefined,
      () => {
        setupProceduralMolar();
      }
    );

    // ─── Render Animation Loop ───────────────────────────────────────────────
    let startTime = performance.now();

    const animate = () => {
      animFrameIdRef.current = requestAnimationFrame(animate);

      const elapsed = (performance.now() - startTime) * 0.001;
      const timeSinceUser = Date.now() - lastUserInteractionRef.current;

      // Gentle continuous tooth rotation & subtle breathing oscillation
      if (toothGroupRef.current && timeSinceUser > 1800) {
        toothGroupRef.current.rotation.y += 0.0035;
        toothGroupRef.current.position.y = Math.sin(elapsed * 1.2) * 0.04;
      }

      // Orbital rings rotation
      if (ring1Ref.current) {
        ring1Ref.current.rotation.z += 0.0028;
      }
      if (ring2Ref.current) {
        ring2Ref.current.rotation.z -= 0.0022;
      }

      controls.update();
      renderer.render(scene, camera);
    };

    animate();

    const resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width: newW, height: newH } = entry.contentRect;
        if (newW > 0 && newH > 0 && cameraRef.current && rendererRef.current) {
          cameraRef.current.aspect = newW / newH;
          cameraRef.current.updateProjectionMatrix();
          rendererRef.current.setSize(newW, newH);
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
  }, [theme]);

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        width: typeof width === 'number' ? `${width}px` : width,
        height: typeof height === 'number' ? `${height}px` : height,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: 'grab',
      }}
    >
      <canvas
        ref={canvasRef}
        style={{
          width: '100%',
          height: '100%',
          display: 'block',
          outline: 'none',
        }}
      />
    </div>
  );
});
