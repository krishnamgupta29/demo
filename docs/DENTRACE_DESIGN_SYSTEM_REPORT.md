# DENTRACE — Design System & Visual Identity Report
**Document Version:** 1.0.0  
**Design Direction:** High-End Editorial Dental Technology Workstation  
**Core Palette:** Primary Navy `#282b4a` & Warm Ivory `#eeebda`  

---

## 1. Design Philosophy

DENTRACE is designed as an authoritative, professional clinical technology product. It deliberately rejects generic "AI SaaS dashboard" tropes:
- **No excessive neon purple glows or cyber-gradients.**
- **No repetitive card slabs or cluttered widgets.**
- **No glassmorphism used purely for decoration.**
- **No tiny unreadable text or arbitrary floating AI badges.**
- **Strong typography pairing, intentional whitespace, fine editorial borders, and restrained interactive motion.**

---

## 2. Color Palette & Semantic Tokens

### Primary Palette
- **Primary Navy (`#282b4a`)**: The foundational brand anchor, used for headers, primary action buttons, active navigation states, and high-emphasis text.
- **Warm Ivory Neutral (`#eeebda`)**: The ambient workspace background providing comfortable, glare-free readability during long diagnostic sessions.
- **Primary Dark Navy (`#1b1e36`)**: Deep tonal background for footers, regulatory banners, and modal backdrops.
- **Primary Light Navy (`#3f436c`)**: Secondary brand accents, subtle icon containers, and interactive hover states.

### Surface Tiers
- **Surface Panel (`#ffffff`)**: Clean, crisp cards, canvas viewports, and primary input surfaces.
- **Surface Card (`#f7f5ed`)**: Muted ivory panels for secondary tools, feature grids, and status pills.
- **Border Warm (`#ded8c4`)**: Subtle 1px structural separators between sections and cards.
- **Border Strong (`#cbcaa6`)**: Accented borders for active dropzones and emphasized boundaries.

### Clinical Status Indicators
- **AI Candidate Anomaly (`#facc15` / Yellow)**: Standardized color for neural anomaly reticles and affected 3D tooth highlights.
- **Dentist Confirmed (`#15803d` / Green)**: Applied when a licensed clinician verifies an anomaly.
- **Clinician Dismissed (`#64748b` / Slate Grey)**: Applied when a false positive is dismissed and excluded from reports.
- **Regulatory Warning (`#ca8a04` / Amber)**: Used for disclaimer alerts, modality mismatch warnings, and unverified inputs.

---

## 3. Typography Scale & Hierarchy

- **Font Family**: `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
- **Monospace Code/Identifiers**: `'JetBrains Mono', 'Fira Code', 'Courier New', monospace`

| Level | Size | Weight | Line Height | Usage |
|---|---|---|---|---|
| **Display Hero** | `44px – 68px` | `900` | `1.05` | Product title `DENTRACE` in hero |
| **Section Title** | `30px – 34px` | `800` | `1.15` | Major landing page and workstation section headers |
| **Modal / Card Title** | `18px – 22px` | `700 – 800` | `1.30` | Feature headers, launchpad cards, registration titles |
| **Body Prominent** | `15px – 16px` | `500 – 600` | `1.65` | Subheadings, descriptive copy, primary button labels |
| **Body Standard** | `13px – 14px` | `400 – 500` | `1.55` | Feature descriptions, form field values, findings descriptions |
| **Micro / Metadata** | `10px – 11.5px`| `600 – 700` | `1.40` | Badges, coordinates, CDT codes, disclaimers, audit stamps |

---

## 4. 3D Anatomical Presentation Standards

### 1. Central Hero Tooth (`HeroTooth3D`)
- **Visual Subject**: Maxillary first molar anatomical cutaway.
- **Lighting**: Three-point studio illumination:
  - Key Light: `0xFFFEF5` (warm ivory) from upper left with soft shadows.
  - Fill Light: `0xE0E7FF` (cool navy bounce) from right.
  - Rim Light: `0xFFFFFF` (crisp white) defining crown silhouette.
  - Under Light: `0xFDE68A` providing radicular dentin warmth.
- **Materials**: Physically Based Rendering (PBR) with ACESFilmic tone mapping:
  - Enamel: Translucent physical material with clearcoat, roughness 0.14, IOR 1.58, transmission 0.28.
  - Dentin: Matte mineralized material with roughness 0.36.
  - Pulp & Root Canals: Physical material with emissive red glow (`#991B1B`) highlighting vascular conduits.
- **Interactions**: Continuous gentle rotation ($0.004\,\text{rad/frame}$) and vertical breathing float ($y = \sin(t) \cdot 0.06$). Mouse/touch OrbitControls take over on user drag with smooth damping.

### 2. Dental Arch Spatial Reference (`DentalArchGLTF`)
- Complete 28-solid-tooth anatomical arch with 4 translucent wisdom tooth placeholders.
- Guaranteed simultaneous bright yellow (`#FACC15`) highlights on all affected teeth.
- Prominently labeled: *"Reference 3D Dental Anatomy — Not Patient-Specific."*

---

## 5. Animation Guidelines & Reduced-Motion Respect

- **Hover Transitions**: `150ms – 200ms ease` on buttons, cards, and interactive chips.
- **View Transitions**: `sectionEnter` (`20px` slide-up with `0.4s ease-out` opacity fade).
- **Reduced Motion**: All transforms and keyframes degrade gracefully to standard static rendering when user operating system prefers reduced motion.
