/**
 * DENTRACE — Verified FDI Tooth Mapping for OrganUI teeth-3d Asset
 *
 * Source: BodyParts3D / Anatomography 4.3 (CC BY-SA 2.1 JP) adapted by OrganUI
 * Mesh Model: 28 Teeth (FDI 11-17, 21-27, 31-37, 41-47) + Gums + Maxilla + Mandible
 *
 * NOTE: 3rd Molars (Wisdom Teeth: FDI 18, 28, 38, 48) are not present in this
 * reference 28-tooth anatomical arch asset and are designated as UNMAPPED.
 */

export interface ToothMappingEntry {
  fdi: number;
  meshId: string;
  fma: string;
  name: string;
  quadrant: 1 | 2 | 3 | 4;
  type: 'incisor' | 'canine' | 'premolar' | 'molar';
  isUpper: boolean;
  isWisdom?: boolean;
}

export const TOOTH_MAPPING: Record<string, ToothMappingEntry> = {
  // ─── Quadrant 1: Maxillary Right (FDI 11 - 17) ──────────────────────────────
  'upper-right-central-incisor': {
    fdi: 11,
    meshId: 'upper-right-central-incisor',
    fma: 'FMA55681',
    name: 'Maxillary Right Central Incisor',
    quadrant: 1,
    type: 'incisor',
    isUpper: true,
  },
  'upper-right-lateral-incisor': {
    fdi: 12,
    meshId: 'upper-right-lateral-incisor',
    fma: 'FMA55680',
    name: 'Maxillary Right Lateral Incisor',
    quadrant: 1,
    type: 'incisor',
    isUpper: true,
  },
  'upper-right-canine': {
    fdi: 13,
    meshId: 'upper-right-canine',
    fma: 'FMA55798',
    name: 'Maxillary Right Canine',
    quadrant: 1,
    type: 'canine',
    isUpper: true,
  },
  'upper-right-first-premolar': {
    fdi: 14,
    meshId: 'upper-right-first-premolar',
    fma: 'FMA55689',
    name: 'Maxillary Right 1st Premolar',
    quadrant: 1,
    type: 'premolar',
    isUpper: true,
  },
  'upper-right-second-premolar': {
    fdi: 15,
    meshId: 'upper-right-second-premolar',
    fma: 'FMA55688',
    name: 'Maxillary Right 2nd Premolar',
    quadrant: 1,
    type: 'premolar',
    isUpper: true,
  },
  'upper-right-first-molar': {
    fdi: 16,
    meshId: 'upper-right-first-molar',
    fma: 'FMA55698',
    name: 'Maxillary Right 1st Molar',
    quadrant: 1,
    type: 'molar',
    isUpper: true,
  },
  'upper-right-second-molar': {
    fdi: 17,
    meshId: 'upper-right-second-molar',
    fma: 'FMA55697',
    name: 'Maxillary Right 2nd Molar',
    quadrant: 1,
    type: 'molar',
    isUpper: true,
  },

  // ─── Quadrant 2: Maxillary Left (FDI 21 - 27) ───────────────────────────────
  'upper-left-central-incisor': {
    fdi: 21,
    meshId: 'upper-left-central-incisor',
    fma: 'FMA55682',
    name: 'Maxillary Left Central Incisor',
    quadrant: 2,
    type: 'incisor',
    isUpper: true,
  },
  'upper-left-lateral-incisor': {
    fdi: 22,
    meshId: 'upper-left-lateral-incisor',
    fma: 'FMA55683',
    name: 'Maxillary Left Lateral Incisor',
    quadrant: 2,
    type: 'incisor',
    isUpper: true,
  },
  'upper-left-canine': {
    fdi: 23,
    meshId: 'upper-left-canine',
    fma: 'FMA55799',
    name: 'Maxillary Left Canine',
    quadrant: 2,
    type: 'canine',
    isUpper: true,
  },
  'upper-left-first-premolar': {
    fdi: 24,
    meshId: 'upper-left-first-premolar',
    fma: 'FMA55690',
    name: 'Maxillary Left 1st Premolar',
    quadrant: 2,
    type: 'premolar',
    isUpper: true,
  },
  'upper-left-second-premolar': {
    fdi: 25,
    meshId: 'upper-left-second-premolar',
    fma: 'FMA55691',
    name: 'Maxillary Left 2nd Premolar',
    quadrant: 2,
    type: 'premolar',
    isUpper: true,
  },
  'upper-left-first-molar': {
    fdi: 26,
    meshId: 'upper-left-first-molar',
    fma: 'FMA55699',
    name: 'Maxillary Left 1st Molar',
    quadrant: 2,
    type: 'molar',
    isUpper: true,
  },
  'upper-left-second-molar': {
    fdi: 27,
    meshId: 'upper-left-second-molar',
    fma: 'FMA55700',
    name: 'Maxillary Left 2nd Molar',
    quadrant: 2,
    type: 'molar',
    isUpper: true,
  },

  // ─── Quadrant 3: Mandibular Left (FDI 31 - 37) ──────────────────────────────
  'lower-left-central-incisor': {
    fdi: 31,
    meshId: 'lower-left-central-incisor',
    fma: 'FMA55685',
    name: 'Mandibular Left Central Incisor',
    quadrant: 3,
    type: 'incisor',
    isUpper: false,
  },
  'lower-left-lateral-incisor': {
    fdi: 32,
    meshId: 'lower-left-lateral-incisor',
    fma: 'FMA55686',
    name: 'Mandibular Left Lateral Incisor',
    quadrant: 3,
    type: 'incisor',
    isUpper: false,
  },
  'lower-left-canine': {
    fdi: 33,
    meshId: 'lower-left-canine',
    fma: 'FMA55801',
    name: 'Mandibular Left Canine',
    quadrant: 3,
    type: 'canine',
    isUpper: false,
  },
  'lower-left-first-premolar': {
    fdi: 34,
    meshId: 'lower-left-first-premolar',
    fma: 'FMA55693',
    name: 'Mandibular Left 1st Premolar',
    quadrant: 3,
    type: 'premolar',
    isUpper: false,
  },
  'lower-left-second-premolar': {
    fdi: 35,
    meshId: 'lower-left-second-premolar',
    fma: 'FMA55694',
    name: 'Mandibular Left 2nd Premolar',
    quadrant: 3,
    type: 'premolar',
    isUpper: false,
  },
  'lower-left-first-molar': {
    fdi: 36,
    meshId: 'lower-left-first-molar',
    fma: 'FMA55702',
    name: 'Mandibular Left 1st Molar',
    quadrant: 3,
    type: 'molar',
    isUpper: false,
  },
  'lower-left-second-molar': {
    fdi: 37,
    meshId: 'lower-left-second-molar',
    fma: 'FMA55703',
    name: 'Mandibular Left 2nd Molar',
    quadrant: 3,
    type: 'molar',
    isUpper: false,
  },

  // ─── Quadrant 4: Mandibular Right (FDI 41 - 47) ─────────────────────────────
  'lower-right-central-incisor': {
    fdi: 41,
    meshId: 'lower-right-central-incisor',
    fma: 'FMA55684',
    name: 'Mandibular Right Central Incisor',
    quadrant: 4,
    type: 'incisor',
    isUpper: false,
  },
  'lower-right-lateral-incisor': {
    fdi: 42,
    meshId: 'lower-right-lateral-incisor',
    fma: 'FMA55687',
    name: 'Mandibular Right Lateral Incisor',
    quadrant: 4,
    type: 'incisor',
    isUpper: false,
  },
  'lower-right-canine': {
    fdi: 43,
    meshId: 'lower-right-canine',
    fma: 'FMA55800',
    name: 'Mandibular Right Canine',
    quadrant: 4,
    type: 'canine',
    isUpper: false,
  },
  'lower-right-first-premolar': {
    fdi: 44,
    meshId: 'lower-right-first-premolar',
    fma: 'FMA55692',
    name: 'Mandibular Right 1st Premolar',
    quadrant: 4,
    type: 'premolar',
    isUpper: false,
  },
  'lower-right-second-premolar': {
    fdi: 45,
    meshId: 'lower-right-second-premolar',
    fma: 'FMA55695',
    name: 'Mandibular Right 2nd Premolar',
    quadrant: 4,
    type: 'premolar',
    isUpper: false,
  },
  'lower-right-first-molar': {
    fdi: 46,
    meshId: 'lower-right-first-molar',
    fma: 'FMA55701',
    name: 'Mandibular Right 1st Molar',
    quadrant: 4,
    type: 'molar',
    isUpper: false,
  },
  'lower-right-second-molar': {
    fdi: 47,
    meshId: 'lower-right-second-molar',
    fma: 'FMA55704',
    name: 'Mandibular Right 2nd Molar',
    quadrant: 4,
    type: 'molar',
    isUpper: false,
  },

  // ─── Ghosted Translucent Wisdom Teeth (FDI 18, 28, 38, 48) ───────────────
  'upper-right-third-molar': {
    fdi: 18,
    meshId: 'upper-right-third-molar',
    fma: 'FMA55684',
    name: 'Maxillary Right 3rd Molar (Wisdom Tooth)',
    quadrant: 1,
    type: 'molar',
    isUpper: true,
    isWisdom: true,
  },
  'upper-left-third-molar': {
    fdi: 28,
    meshId: 'upper-left-third-molar',
    fma: 'FMA55685',
    name: 'Maxillary Left 3rd Molar (Wisdom Tooth)',
    quadrant: 2,
    type: 'molar',
    isUpper: true,
    isWisdom: true,
  },
  'lower-left-third-molar': {
    fdi: 38,
    meshId: 'lower-left-third-molar',
    fma: 'FMA55706',
    name: 'Mandibular Left 3rd Molar (Wisdom Tooth)',
    quadrant: 3,
    type: 'molar',
    isUpper: false,
    isWisdom: true,
  },
  'lower-right-third-molar': {
    fdi: 48,
    meshId: 'lower-right-third-molar',
    fma: 'FMA55705',
    name: 'Mandibular Right 3rd Molar (Wisdom Tooth)',
    quadrant: 4,
    type: 'molar',
    isUpper: false,
    isWisdom: true,
  },
};

// Fast lookup maps
export const FDI_TO_MESH_ID: Record<number, string> = {};
export const MESH_ID_TO_FDI: Record<string, number> = {};

Object.entries(TOOTH_MAPPING).forEach(([meshId, entry]) => {
  FDI_TO_MESH_ID[entry.fdi] = meshId;
  MESH_ID_TO_FDI[meshId] = entry.fdi;
});

export const NON_TOOTH_STRUCTURES = {
  gums: ['upper-gum', 'lower-gum'],
  bones: ['right-maxilla', 'left-maxilla', 'mandible'],
};

export function getToothByMeshId(meshId: string): ToothMappingEntry | undefined {
  return TOOTH_MAPPING[meshId];
}

export function getMeshIdByFdi(fdi: number): string | undefined {
  return FDI_TO_MESH_ID[fdi];
}

export function isToothMesh(meshId: string): boolean {
  return meshId in TOOTH_MAPPING;
}
