export interface ToothMeta {
  fdi: number;
  quadrant: number;
  indexInQuad: number; // 0 (central incisor) to 7 (3rd molar)
  type: 'incisor' | 'canine' | 'premolar' | 'molar';
  crownW: number;
  isUpper: boolean;
  name: string;
}

export const TOOTH_NAMES: Record<number, string> = {
  18: "Maxillary Right 3rd Molar", 17: "Maxillary Right 2nd Molar", 16: "Maxillary Right 1st Molar",
  15: "Maxillary Right 2nd Premolar", 14: "Maxillary Right 1st Premolar", 13: "Maxillary Right Canine",
  12: "Maxillary Right Lateral Incisor", 11: "Maxillary Right Central Incisor",
  21: "Maxillary Left Central Incisor", 22: "Maxillary Left Lateral Incisor", 23: "Maxillary Left Canine",
  24: "Maxillary Left 1st Premolar", 25: "Maxillary Left 2nd Premolar", 26: "Maxillary Left 1st Molar",
  27: "Maxillary Left 2nd Molar", 28: "Maxillary Left 3rd Molar",
  38: "Mandibular Left 3rd Molar", 37: "Mandibular Left 2nd Molar", 36: "Mandibular Left 1st Molar",
  35: "Mandibular Left 2nd Premolar", 34: "Mandibular Left 1st Premolar", 33: "Mandibular Left Canine",
  32: "Mandibular Left Lateral Incisor", 31: "Mandibular Left Central Incisor",
  41: "Mandibular Right Central Incisor", 42: "Mandibular Right Lateral Incisor", 43: "Mandibular Right Canine",
  44: "Mandibular Right 1st Premolar", 45: "Mandibular Right 2nd Premolar", 46: "Mandibular Right 1st Molar",
  47: "Mandibular Right 2nd Molar", 48: "Mandibular Right 3rd Molar"
};

export const TEETH_DATA: ToothMeta[] = [
  // Upper Arch (Maxilla) - Q1 (Patient Right)
  { fdi: 11, quadrant: 1, indexInQuad: 0, type: 'incisor',  crownW: 1.05, isUpper: true, name: TOOTH_NAMES[11] },
  { fdi: 12, quadrant: 1, indexInQuad: 1, type: 'incisor',  crownW: 0.85, isUpper: true, name: TOOTH_NAMES[12] },
  { fdi: 13, quadrant: 1, indexInQuad: 2, type: 'canine',   crownW: 0.90, isUpper: true, name: TOOTH_NAMES[13] },
  { fdi: 14, quadrant: 1, indexInQuad: 3, type: 'premolar', crownW: 0.86, isUpper: true, name: TOOTH_NAMES[14] },
  { fdi: 15, quadrant: 1, indexInQuad: 4, type: 'premolar', crownW: 0.86, isUpper: true, name: TOOTH_NAMES[15] },
  { fdi: 16, quadrant: 1, indexInQuad: 5, type: 'molar',    crownW: 1.26, isUpper: true, name: TOOTH_NAMES[16] },
  { fdi: 17, quadrant: 1, indexInQuad: 6, type: 'molar',    crownW: 1.18, isUpper: true, name: TOOTH_NAMES[17] },
  { fdi: 18, quadrant: 1, indexInQuad: 7, type: 'molar',    crownW: 1.06, isUpper: true, name: TOOTH_NAMES[18] },

  // Upper Arch (Maxilla) - Q2 (Patient Left)
  { fdi: 21, quadrant: 2, indexInQuad: 0, type: 'incisor',  crownW: 1.05, isUpper: true, name: TOOTH_NAMES[21] },
  { fdi: 22, quadrant: 2, indexInQuad: 1, type: 'incisor',  crownW: 0.85, isUpper: true, name: TOOTH_NAMES[22] },
  { fdi: 23, quadrant: 2, indexInQuad: 2, type: 'canine',   crownW: 0.90, isUpper: true, name: TOOTH_NAMES[23] },
  { fdi: 24, quadrant: 2, indexInQuad: 3, type: 'premolar', crownW: 0.86, isUpper: true, name: TOOTH_NAMES[24] },
  { fdi: 25, quadrant: 2, indexInQuad: 4, type: 'premolar', crownW: 0.86, isUpper: true, name: TOOTH_NAMES[25] },
  { fdi: 26, quadrant: 2, indexInQuad: 5, type: 'molar',    crownW: 1.26, isUpper: true, name: TOOTH_NAMES[26] },
  { fdi: 27, quadrant: 2, indexInQuad: 6, type: 'molar',    crownW: 1.18, isUpper: true, name: TOOTH_NAMES[27] },
  { fdi: 28, quadrant: 2, indexInQuad: 7, type: 'molar',    crownW: 1.06, isUpper: true, name: TOOTH_NAMES[28] },

  // Lower Arch (Mandible) - Q4 (Patient Right)
  { fdi: 41, quadrant: 4, indexInQuad: 0, type: 'incisor',  crownW: 0.64, isUpper: false, name: TOOTH_NAMES[41] },
  { fdi: 42, quadrant: 4, indexInQuad: 1, type: 'incisor',  crownW: 0.70, isUpper: false, name: TOOTH_NAMES[42] },
  { fdi: 43, quadrant: 4, indexInQuad: 2, type: 'canine',   crownW: 0.78, isUpper: false, name: TOOTH_NAMES[43] },
  { fdi: 44, quadrant: 4, indexInQuad: 3, type: 'premolar', crownW: 0.78, isUpper: false, name: TOOTH_NAMES[44] },
  { fdi: 45, quadrant: 4, indexInQuad: 4, type: 'premolar', crownW: 0.78, isUpper: false, name: TOOTH_NAMES[45] },
  { fdi: 46, quadrant: 4, indexInQuad: 5, type: 'molar',    crownW: 1.26, isUpper: false, name: TOOTH_NAMES[46] },
  { fdi: 47, quadrant: 4, indexInQuad: 6, type: 'molar',    crownW: 1.18, isUpper: false, name: TOOTH_NAMES[47] },
  { fdi: 48, quadrant: 4, indexInQuad: 7, type: 'molar',    crownW: 1.06, isUpper: false, name: TOOTH_NAMES[48] },

  // Lower Arch (Mandible) - Q3 (Patient Left)
  { fdi: 31, quadrant: 3, indexInQuad: 0, type: 'incisor',  crownW: 0.64, isUpper: false, name: TOOTH_NAMES[31] },
  { fdi: 32, quadrant: 3, indexInQuad: 1, type: 'incisor',  crownW: 0.70, isUpper: false, name: TOOTH_NAMES[32] },
  { fdi: 33, quadrant: 3, indexInQuad: 2, type: 'canine',   crownW: 0.78, isUpper: false, name: TOOTH_NAMES[33] },
  { fdi: 34, quadrant: 3, indexInQuad: 3, type: 'premolar', crownW: 0.78, isUpper: false, name: TOOTH_NAMES[34] },
  { fdi: 35, quadrant: 3, indexInQuad: 4, type: 'premolar', crownW: 0.78, isUpper: false, name: TOOTH_NAMES[35] },
  { fdi: 36, quadrant: 3, indexInQuad: 5, type: 'molar',    crownW: 1.26, isUpper: false, name: TOOTH_NAMES[36] },
  { fdi: 37, quadrant: 3, indexInQuad: 6, type: 'molar',    crownW: 1.18, isUpper: false, name: TOOTH_NAMES[37] },
  { fdi: 38, quadrant: 3, indexInQuad: 7, type: 'molar',    crownW: 1.06, isUpper: false, name: TOOTH_NAMES[38] },
];
