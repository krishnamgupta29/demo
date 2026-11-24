import * as THREE from 'three';
import * as BufferGeometryUtils from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { ToothMeta } from './toothData';

/*
 * DENTRACE — True Anatomical 3D Human Tooth Geometry
 * ==================================================
 * Continuous, 100% Watertight Lofted Solid Geometries:
 * 1. Anatomic Crown-to-Root Waist: Distinct cervical constriction with bulbous crown contours.
 * 2. 100% Watertight Closed Solids: Sealed incisal/occlusal biting tables and apical caps.
 * 3. True Organic Forms matching reference:
 *    - Incisors: Wide spade chisel with convex labial bulge, cervical constriction, tapered curved root.
 *    - Canines: Diamond spearhead cusp, prominent vertical labial ridge, robust root.
 *    - Premolars: Bulbous bicuspid crown (buccal & lingual cusps + central groove), tapered root.
 *    - Molars: Quad-cusp occlusal table with central fossa + distinct divergent roots (2 lower, 3 upper).
 * 4. Warm Polished Ivory Enamel Color Gradient:
 *    - Pure polished incisal enamel: #FFFFFC
 *    - Warm crown body: #F8F2E2
 *    - Cementoenamel neck: #EBDBB3
 *    - Radicular dentin: #D8C292
 *    - Apical root tip: #BA9B62
 */

const COLOR_INCISAL = new THREE.Color(0xFFFEFA);
const COLOR_CROWN   = new THREE.Color(0xF7F0DF);
const COLOR_CERVIX  = new THREE.Color(0xEBDBB3);
const COLOR_ROOT    = new THREE.Color(0xD8C292);
const COLOR_APEX    = new THREE.Color(0xB89A5F);

export function buildAnatomicalToothGeometry(meta: ToothMeta): THREE.BufferGeometry {
  const { type } = meta;
  if (type === 'molar') return buildMolar(meta);
  if (type === 'premolar') return buildPremolar(meta);
  if (type === 'canine') return buildCanine(meta);
  return buildIncisor(meta);
}

// ─── Smooth Multi-Stop Vertex Color Gradient ─────────────────────────────────
function applyVertexColors(
  geom: THREE.BufferGeometry,
  isUpper: boolean,
  yBitingTip: number,
  yCervix: number,
  yApexTip: number
) {
  const pos = geom.attributes.position;
  const count = pos.count;
  const colors = new Float32Array(count * 3);
  const col = new THREE.Color();

  for (let i = 0; i < count; i++) {
    const y = pos.getY(i);

    if (isUpper) {
      if (y <= yCervix) {
        const t = Math.min(1, Math.max(0, (yCervix - y) / Math.max(0.001, yCervix - yBitingTip)));
        if (t > 0.65) {
          col.lerpColors(COLOR_CROWN, COLOR_INCISAL, (t - 0.65) / 0.35);
        } else {
          col.lerpColors(COLOR_CERVIX, COLOR_CROWN, t / 0.65);
        }
      } else {
        const t = Math.min(1, Math.max(0, (y - yCervix) / Math.max(0.001, yApexTip - yCervix)));
        if (t > 0.50) {
          col.lerpColors(COLOR_ROOT, COLOR_APEX, (t - 0.50) / 0.50);
        } else {
          col.lerpColors(COLOR_CERVIX, COLOR_ROOT, t / 0.50);
        }
      }
    } else {
      if (y >= yCervix) {
        const t = Math.min(1, Math.max(0, (y - yCervix) / Math.max(0.001, yBitingTip - yCervix)));
        if (t > 0.65) {
          col.lerpColors(COLOR_CROWN, COLOR_INCISAL, (t - 0.65) / 0.35);
        } else {
          col.lerpColors(COLOR_CERVIX, COLOR_CROWN, t / 0.65);
        }
      } else {
        const t = Math.min(1, Math.max(0, (yCervix - y) / Math.max(0.001, yCervix - yApexTip)));
        if (t > 0.50) {
          col.lerpColors(COLOR_ROOT, COLOR_APEX, (t - 0.50) / 0.50);
        } else {
          col.lerpColors(COLOR_CERVIX, COLOR_ROOT, t / 0.50);
        }
      }
    }

    colors[i * 3 + 0] = col.r;
    colors[i * 3 + 1] = col.g;
    colors[i * 3 + 2] = col.b;
  }

  geom.setAttribute('color', new THREE.BufferAttribute(colors, 3));
}

// ─── Watertight Continuous Cross-Section Loft Generator ──────────────────────
interface RingDef {
  y: number;
  fn: (theta: number) => { x: number; z: number };
}

function buildLoftedSolid(rings: RingDef[], numSides: number = 32): THREE.BufferGeometry {
  const numRings = rings.length;
  const positions: number[] = [];
  const indices: number[] = [];

  for (let r = 0; r < numRings; r++) {
    const ring = rings[r];
    for (let s = 0; s < numSides; s++) {
      const theta = (s / numSides) * Math.PI * 2;
      const pt = ring.fn(theta);
      positions.push(pt.x, ring.y, pt.z);
    }
  }

  // 1. Bottom Cap (Sealed at Ring 0)
  const bottomCenterIdx = positions.length / 3;
  let avgZ0 = 0;
  for (let s = 0; s < numSides; s++) avgZ0 += positions[s * 3 + 2];
  avgZ0 /= numSides;
  positions.push(0, rings[0].y, avgZ0);

  for (let s = 0; s < numSides; s++) {
    const nextS = (s + 1) % numSides;
    indices.push(bottomCenterIdx, nextS, s);
  }

  // 2. Wall Quads
  for (let r = 0; r < numRings - 1; r++) {
    const rStart = r * numSides;
    const nextRStart = (r + 1) * numSides;
    for (let s = 0; s < numSides; s++) {
      const nextS = (s + 1) % numSides;
      const v00 = rStart + s;
      const v01 = rStart + nextS;
      const v10 = nextRStart + s;
      const v11 = nextRStart + nextS;

      indices.push(v00, v01, v10);
      indices.push(v01, v11, v10);
    }
  }

  // 3. Top Cap (Sealed at Ring numRings - 1)
  const topCenterIdx = positions.length / 3;
  const topRingStart = (numRings - 1) * numSides;
  let avgZTop = 0;
  for (let s = 0; s < numSides; s++) avgZTop += positions[(topRingStart + s) * 3 + 2];
  avgZTop /= numSides;
  positions.push(positions[topRingStart * 3], rings[numRings - 1].y, avgZTop);

  for (let s = 0; s < numSides; s++) {
    const nextS = (s + 1) % numSides;
    indices.push(topCenterIdx, topRingStart + s, topRingStart + nextS);
  }

  const geom = new THREE.BufferGeometry();
  geom.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geom.setIndex(indices);
  geom.computeVertexNormals();

  return geom;
}

// ─── 1. SOLID INCISOR (Wide Spade Chisel Crown + Conical Root) ────────────────
function buildIncisor(meta: ToothMeta): THREE.BufferGeometry {
  const { isUpper, fdi, quadrant } = meta;
  const isLateral = Math.abs(fdi % 10) === 2;
  const isRight = quadrant === 1 || quadrant === 4;
  const dirY = isUpper ? 1 : -1;
  const distalSign = isRight ? -1 : 1;

  const crownW = isUpper ? (isLateral ? 0.88 : 1.08) : (isLateral ? 0.72 : 0.66);
  const crownH = isUpper ? (isLateral ? 1.10 : 1.20) : (isLateral ? 1.00 : 0.92);
  const rootL  = isUpper ? (isLateral ? 1.70 : 1.85) : (isLateral ? 1.55 : 1.45);

  const numRings = 24;
  const rings: RingDef[] = [];

  const superellipse = (theta: number, a: number, b: number, n: number = 0.45, m: number = 0.85) => {
    const cosT = Math.cos(theta);
    const sinT = Math.sin(theta);
    const sgnX = cosT >= 0 ? 1 : -1;
    const sgnZ = sinT >= 0 ? 1 : -1;
    return {
      x: a * sgnX * Math.pow(Math.abs(cosT), n),
      z: b * sgnZ * Math.pow(Math.abs(sinT), m),
    };
  };

  for (let i = 0; i < numRings; i++) {
    const v = i / (numRings - 1);
    const cervixRatio = crownH / (crownH + rootL);

    let y = 0;
    let crossFn: (theta: number) => { x: number; z: number };

    if (v <= cervixRatio) {
      // ── CROWN ZONE ──
      // u: 0 at biting edge, 1 at cervix
      const u = v / cervixRatio;
      const normIncisal = 1.0 - u;
      y = -dirY * crownH * (1.0 - u);

      // Width: starts wide at chisel biting edge (1.0), narrows slightly at waist (0.65)
      const w = crownW * (0.64 + 0.36 * Math.pow(normIncisal, 0.7));
      // Depth: thin chisel at biting edge (0.16), expands to full bulbous contour at mid-crown (0.55), narrows at cervix (0.38)
      const contour = Math.sin(u * Math.PI) * 0.32;
      const d = 0.16 + contour + (u * 0.22);

      crossFn = (theta: number) => {
        const pt = superellipse(theta, w * 0.50, d * 0.50, 0.40 + u * 0.50, 0.70 + u * 0.30);
        // Convex labial bulge (+Z)
        if (pt.z > 0) {
          pt.z += Math.sin(u * Math.PI) * 0.12;
        } else {
          // Lingual fossa & cingulum near cervix (u > 0.5)
          const cingulum = Math.max(0, u - 0.4) * 0.14;
          pt.z -= cingulum;
        }
        return pt;
      };
    } else {
      // ── ROOT ZONE ──
      // u: 0 at cervix, 1 at apex
      const u = (v - cervixRatio) / (1.0 - cervixRatio);
      y = dirY * rootL * u;

      // Narrow neck at cervix expanding slightly then tapering to apex
      const taper = Math.max(0.08, 1.0 - Math.pow(u, 0.82) * 0.88);
      const w = crownW * 0.64 * taper;
      const d = 0.44 * taper * 1.12;
      const curveX = Math.pow(u, 1.8) * 0.18 * distalSign;

      crossFn = (theta: number) => {
        return {
          x: (w * 0.50) * Math.cos(theta) + curveX,
          z: (d * 0.50) * Math.sin(theta),
        };
      };
    }

    rings.push({ y, fn: crossFn });
  }

  if (dirY < 0) {
    rings.reverse();
  }

  const geom = buildLoftedSolid(rings, 32);
  const yBitingTip = -dirY * crownH;
  const yApexTip   = dirY * rootL;
  applyVertexColors(geom, isUpper, yBitingTip, 0, yApexTip);

  return geom;
}

// ─── 2. SOLID CANINE (Spearhead Cusp + Sturdy Root) ───────────────────────────
function buildCanine(meta: ToothMeta): THREE.BufferGeometry {
  const { isUpper, quadrant } = meta;
  const isRight = quadrant === 1 || quadrant === 4;
  const dirY = isUpper ? 1 : -1;
  const distalSign = isRight ? -1 : 1;

  const crownW = isUpper ? 0.96 : 0.84;
  const crownH = isUpper ? 1.30 : 1.20;
  const rootL  = isUpper ? 2.10 : 1.95;

  const numRings = 24;
  const rings: RingDef[] = [];

  for (let i = 0; i < numRings; i++) {
    const v = i / (numRings - 1);
    const cervixRatio = crownH / (crownH + rootL);

    let y = 0;
    let crossFn: (theta: number) => { x: number; z: number };

    if (v <= cervixRatio) {
      // ── CROWN: Diamond Spearhead Cusp ──
      const u = v / cervixRatio;
      const normCusp = 1.0 - u;
      y = -dirY * crownH * (1.0 - u);

      // Diamond flare at mid-crown (u ≈ 0.4), sharp cusp tip (u = 0), cervical neck (u = 1)
      const diamondFlare = Math.sin(normCusp * Math.PI * 0.75);
      const w = crownW * (0.16 + diamondFlare * 0.84);
      const d = 0.78 * (0.18 + diamondFlare * 0.82);

      crossFn = (theta: number) => {
        const cosT = Math.cos(theta);
        const sinT = Math.sin(theta);
        let x = (w * 0.50) * cosT;
        let z = (d * 0.50) * sinT;

        // Prominent vertical labial ridge (+Z)
        if (z > 0) {
          const ridge = Math.max(0, 1.0 - Math.abs(cosT) * 2.2) * 0.22 * Math.sin(normCusp * Math.PI);
          z += ridge;
        }
        return { x, z };
      };
    } else {
      // ── ROOT ──
      const u = (v - cervixRatio) / (1.0 - cervixRatio);
      y = dirY * rootL * u;

      const taper = Math.max(0.08, 1.0 - Math.pow(u, 0.82) * 0.88);
      const w = crownW * 0.68 * taper;
      const d = 0.66 * taper * 1.12;
      const curveX = Math.pow(u, 1.8) * 0.22 * distalSign;

      crossFn = (theta: number) => {
        return {
          x: (w * 0.50) * Math.cos(theta) + curveX,
          z: (d * 0.50) * Math.sin(theta),
        };
      };
    }

    rings.push({ y, fn: crossFn });
  }

  if (dirY < 0) {
    rings.reverse();
  }

  const geom = buildLoftedSolid(rings, 32);
  const yBitingTip = -dirY * crownH;
  const yApexTip   = dirY * rootL;
  applyVertexColors(geom, isUpper, yBitingTip, 0, yApexTip);

  return geom;
}

// ─── 3. SOLID PREMOLAR (Bulbous Bicuspid Crown + Conical Root) ────────────────
function buildPremolar(meta: ToothMeta): THREE.BufferGeometry {
  const { isUpper, quadrant } = meta;
  const isRight = quadrant === 1 || quadrant === 4;
  const dirY = isUpper ? 1 : -1;
  const distalSign = isRight ? -1 : 1;

  const crownW = isUpper ? 0.88 : 0.80;
  const crownH = 1.10;
  const rootL  = isUpper ? 1.75 : 1.60;

  const numRings = 24;
  const rings: RingDef[] = [];

  for (let i = 0; i < numRings; i++) {
    const v = i / (numRings - 1);
    const cervixRatio = crownH / (crownH + rootL);

    let y = 0;
    let crossFn: (theta: number) => { x: number; z: number };

    if (v <= cervixRatio) {
      // ── CROWN: Bulbous Bicuspid Table ──
      const u = v / cervixRatio;
      const normOcc = 1.0 - u;
      y = -dirY * crownH * (1.0 - u);

      // Bulbous contour at mid crown, narrow neck at cervix (u = 1)
      const bulge = Math.sin(u * Math.PI) * 0.22;
      const w = crownW * (0.80 + bulge);
      const d = 0.88 * (0.80 + bulge);

      crossFn = (theta: number) => {
        let x = (w * 0.50) * Math.cos(theta);
        let z = (d * 0.50) * Math.sin(theta);
        if (Math.abs(Math.cos(theta)) > 0.85 && normOcc > 0.5) {
          x *= 0.92;
        }
        return { x, z };
      };
    } else {
      // ── ROOT ──
      const u = (v - cervixRatio) / (1.0 - cervixRatio);
      y = dirY * rootL * u;

      const taper = Math.max(0.08, 1.0 - Math.pow(u, 0.82) * 0.88);
      const w = crownW * 0.68 * taper;
      const d = 0.70 * taper * 1.12;
      const curveX = Math.pow(u, 1.8) * 0.16 * distalSign;

      crossFn = (theta: number) => {
        return {
          x: (w * 0.50) * Math.cos(theta) + curveX,
          z: (d * 0.50) * Math.sin(theta),
        };
      };
    }

    rings.push({ y, fn: crossFn });
  }

  if (dirY < 0) {
    rings.reverse();
  }

  const geom = buildLoftedSolid(rings, 32);

  const pos = geom.attributes.position;
  const yOcc = -dirY * crownH;
  for (let i = 0; i < pos.count; i++) {
    const py = pos.getY(i);
    if (Math.abs(py - yOcc) < 0.18) {
      const pz = pos.getZ(i);
      const cusp = Math.abs(pz) * 0.16 - 0.06;
      pos.setY(i, py - dirY * cusp);
    }
  }
  geom.computeVertexNormals();

  const yBitingTip = -dirY * crownH;
  const yApexTip   = dirY * rootL;
  applyVertexColors(geom, isUpper, yBitingTip, 0, yApexTip);

  return geom;
}

// ─── 4. SOLID MOLAR (Quad-Cusp Table + Divergent Multi-Roots) ────────────────
function buildMolar(meta: ToothMeta): THREE.BufferGeometry {
  const { isUpper, quadrant, fdi } = meta;
  const isRight = quadrant === 1 || quadrant === 4;
  const is3rd = Math.abs(fdi % 10) === 8;
  const is1st = Math.abs(fdi % 10) === 6;
  const dirY = isUpper ? 1 : -1;
  const mesialSign = isRight ? 1 : -1;

  const scale = is3rd ? 0.88 : is1st ? 1.05 : 0.98;
  const crownW = 1.22 * scale;
  const crownH = 1.10 * scale;
  const crownD = 1.25 * scale;

  const trunkH = 0.34 * scale;
  const rootL  = (isUpper ? 1.80 : 1.65) * scale;

  const yCervix = 0.0;
  const yCrownCenter = -dirY * (crownH * 0.46);
  const yTrunkCenter = dirY * (trunkH * 0.50);
  const yFurcation   = dirY * trunkH;

  // A. Solid Closed Crown — Bulbous contour with 4 sculpted cusps (MB, DB, ML, DL) + central fossa
  const crownGeom = new THREE.CylinderGeometry(crownW * 0.48, crownW * 0.42, crownH, 36, 18);
  const cPos = crownGeom.attributes.position;
  for (let i = 0; i < cPos.count; i++) {
    let x = cPos.getX(i);
    let y = cPos.getY(i);
    let z = cPos.getZ(i) * (crownD / crownW);

    const normOcc = dirY > 0 ? (0.5 - y / crownH) : (0.5 + y / crownH);
    // Mid-crown bulbous belly
    const bulge = Math.sin(normOcc * Math.PI) * 0.12;
    x *= (1.0 + bulge);
    z *= (1.0 + bulge);

    if (normOcc > 0.50) {
      const weight = (normOcc - 0.50) / 0.50;
      const cusps = (Math.cos(x * 3.8) * 0.15 + Math.cos(z * 3.8) * 0.15);
      const fossa = Math.abs(x) < 0.22 && Math.abs(z) < 0.22 ? -0.20 : 0;
      y += (dirY > 0 ? -1 : 1) * (cusps + fossa) * weight;
    }

    cPos.setX(i, x + (z * 0.06 * mesialSign));
    cPos.setY(i, y);
    cPos.setZ(i, z);
  }
  crownGeom.translate(0, yCrownCenter, 0);

  // B. Solid Root Trunk
  const trunkGeom = new THREE.CylinderGeometry(crownW * 0.42, crownW * 0.38, trunkH, 30, 8);
  trunkGeom.translate(0, yTrunkCenter, 0);

  const parts: THREE.BufferGeometry[] = [crownGeom, trunkGeom];

  // C. Solid Divergent Multi-Root Branches with Closed Apical Caps
  const makeSolidRootBranch = (
    radius: number,
    baseX: number,
    baseZ: number,
    curveX: number,
    curveZ: number,
    lengthMult: number = 1.0
  ) => {
    const branchL = rootL * lengthMult;
    const bGeom = new THREE.CylinderGeometry(radius, 0.07, branchL, 22, 16);
    const bPos = bGeom.attributes.position;

    for (let i = 0; i < bPos.count; i++) {
      let x = bPos.getX(i);
      let y = bPos.getY(i);
      let z = bPos.getZ(i);

      const t = dirY > 0 ? (0.5 + y / branchL) : (0.5 - y / branchL);
      const cx = baseX + Math.pow(t, 1.4) * curveX;
      const cz = baseZ + Math.pow(t, 1.4) * curveZ;

      bPos.setX(i, x + cx);
      bPos.setZ(i, z * 1.12 + cz);
    }

    const yCenter = yFurcation + dirY * (branchL * 0.50);
    bGeom.translate(0, yCenter, 0);
    return bGeom;
  };

  if (!isUpper) {
    // Mandibular: 2 divergent roots (Mesial & Distal)
    parts.push(makeSolidRootBranch(0.32 * scale, -0.24 * mesialSign, 0.0, -0.34 * mesialSign, 0.06, 1.0));
    parts.push(makeSolidRootBranch(0.30 * scale,  0.24 * mesialSign, 0.0,  0.32 * mesialSign, -0.08, 0.95));
  } else {
    // Maxillary: 3 divergent roots (Mesiobuccal, Distobuccal, Palatal)
    parts.push(makeSolidRootBranch(0.26 * scale, -0.22 * mesialSign,  0.18, -0.28 * mesialSign,  0.20, 0.95));
    parts.push(makeSolidRootBranch(0.24 * scale,  0.22 * mesialSign,  0.18,  0.28 * mesialSign,  0.20, 0.90));
    parts.push(makeSolidRootBranch(0.32 * scale,  0.0,              -0.24,  0.0,              -0.45, 1.05));
  }

  const merged = BufferGeometryUtils.mergeGeometries(parts, false);
  merged.computeVertexNormals();

  const yBitingTip = -dirY * crownH;
  const yApexTip   = dirY * (trunkH + rootL);
  applyVertexColors(merged, isUpper, yBitingTip, yCervix, yApexTip);

  return merged;
}
