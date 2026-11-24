/**
 * DENTRACE TypeScript API Contracts
 * Strongly typed definitions matching backend FastAPI / Pydantic models.
 */

export interface SystemHealth {
  status: string;
  app: string;
  version: string;
  environment: string;
  timestamp: string;
  disclaimer: string;
}

export interface SystemReadiness {
  status: 'ready' | 'degraded';
  checks: {
    database: boolean;
    storage: boolean;
    models: string;
    disk_free_gb?: number;
    available_models?: string[];
    total_registered_models?: number;
    database_error?: string;
    storage_error?: string;
  };
  timestamp: string;
  disclaimer: string;
}

export interface ModelEntry {
  model_id: string;
  model_name: string;
  version: string;
  task: string;
  supported_classes: string[];
  is_available: boolean;
  weight_rel_path?: string;
  provenance?: {
    model_id: string;
    model_name: string;
    version: string;
    format: string;
    weights_hash_sha256?: string;
    is_fine_tuned: boolean;
  };
}

export interface RadiographMetadata {
  original_filename: string;
  storage_rel_path: string;
  preview_rel_path?: string;
  width?: number;
  height?: number;
  width_px?: number;
  height_px?: number;
  channels?: number;
  file_size_bytes?: number;
  sha256_hash?: string;
  mime_type?: string;
  aspect_ratio?: number;
  modality?: string;
}

export interface StudyItem {
  study_id: string;
  patient_anonymous_id: string;
  status: string;
  created_at: string;
  radiograph?: RadiographMetadata;
  quality?: QualityAssessment;
  findings_count?: number;
  clinical_indication?: string;
  acquisition_date?: string;
  is_archived?: boolean;
  has_preview?: boolean;
}

export interface StudyListResponse {
  total: number;
  items: StudyItem[];
  studies?: StudyItem[];
}

export interface PolygonPoint {
  x: number;
  y: number;
}

export interface Finding {
  finding_id: string;
  study_id: string;
  model_id: string;
  pathology_class: string;
  confidence: number;
  bounding_box: {
    x_min: number;
    y_min: number;
    x_max: number;
    y_max: number;
  };
  segmentation_mask?: {
    polygon_points: PolygonPoint[];
    is_true_instance_mask: boolean;
  };
  tooth_fdi?: number;
  quadrant?: number;
  fdi_confidence?: number;
  review_status?: 'pending' | 'accepted' | 'confirmed' | 'rejected' | 'corrected';
  dentist_reviewed_at?: string;
  dentist_notes?: string;
}

export interface QualityAssessment {
  overall_score: number;
  contrast_score: number;
  sharpness_score: number;
  artifacts_detected: string[];
  passed_diagnostic_threshold: boolean;
}

export interface StudyDetail {
  study_id: string;
  patient_anonymous_id?: string;
  status?: string;
  clinical_indication?: string;
  acquisition_date?: string;
  created_at: string;
  radiograph: RadiographMetadata;
  quality_assessment?: QualityAssessment;
  findings: Finding[];
}

export interface AnalysisResponse {
  study_id: string;
  status?: string;
  model_id: string;
  model_name?: string;
  execution_latency_ms?: number;
  findings_detected?: number;
  findings?: Finding[];
  disclaimer?: string;
  notice?: string;
}

export interface ClinicianReviewPayload {
  reviewer_name: string;
  license_number: string;
  decision: 'accepted' | 'confirmed' | 'rejected' | 'corrected';
  confirmed_fdi?: number;
  confirmed_pathology?: string;
  clinical_notes?: string;
}

export interface ClinicalEvidencePackage {
  study_id: string;
  package_id?: string;
  radiograph_id?: string;
  created_at?: string;
  assembled_at?: string;
  ai_observations?: Finding[];
  dentist_confirmations?: Array<any>;
  ai_candidate_observations?: Finding[];
  clinician_confirmed_findings?: Array<any>;
  chairside_examinations?: Array<any>;
  clinical_examinations?: Array<any>;
  patient_symptoms?: Array<any>;
  requested_procedures?: Array<any>;
  payer_template?: any;
}

export interface EvidenceReadinessReport {
  study_id: string;
  evaluated_at: string;
  is_ready_for_submission: boolean;
  overall_readiness_score: number;
  unconfirmed_findings_count: number;
  missing_required_items: string[];
  clinical_warnings: string[];
  findings_summary: Record<string, number>;
}

export interface InsurancePreAuthDraft {
  study_id: string;
  patient_anonymous_id?: string;
  chief_complaint: string;
  clinical_findings: string;
  radiographic_evidence: string;
  diagnostic_summary: string;
  treatment_rationale: string;
  alternative_treatments: string;
  prognosis: string;
  medical_necessity_statement: string;
  suggested_procedure: string;
  suggested_cdt_code: string;
  urgency: string;
  state: 'AI_DRAFT' | 'CLINICIAN_REVISED' | 'DENTIST_APPROVED';
  dentist_name?: string;
  license_number?: string;
  generated_at: string;
  model_used: string;
  disclaimer: string;
}

export interface AuditTrailEntry {
  audit_id: string;
  study_id: string;
  timestamp: string;
  event_type: string;
  actor_name: string;
  actor_role: string;
  details: Record<string, any>;
  sha256_hash: string;
}

export interface CDTCodeItem {
  code: string;
  name: string;
  category: string;
  description: string;
  clinical_notes?: string;
}

export interface PatientInfoPayload {
  patient_name: string;
  patient_id: string;
  age: number;
  sex?: string;
  scan_date: string;
  chief_complaint?: string;
  symptoms?: string;
  history?: string;
  referring_dentist?: string;
}

export interface ClaimReportRequest {
  patient_info?: PatientInfoPayload;
  custom_narrative?: string;
  snapshot_3d_base64?: string;
  selected_fdi?: number;
  selected_pathology?: string;
}


