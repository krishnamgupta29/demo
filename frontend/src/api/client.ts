import {
  SystemHealth,
  SystemReadiness,
  ModelEntry,
  StudyListResponse,
  StudyDetail,
  AnalysisResponse,
  Finding,
  ClinicianReviewPayload,
  ClinicalEvidencePackage,
  EvidenceReadinessReport,
  InsurancePreAuthDraft,
  AuditTrailEntry,
  CDTCodeItem,
  PatientInfoPayload,
  ClaimReportRequest,
} from './types';

const BASE_URL = '/api/v1';

class APIError extends Error {
  status: number;
  data: any;
  constructor(message: string, status: number, data?: any) {
    super(message);
    this.name = 'APIError';
    this.status = status;
    this.data = data;
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const headers = new Headers(options.headers || {});
  
  if (!(options.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (response.status === 204) {
    return {} as T;
  }

  if (!response.ok) {
    let errorDetail = response.statusText;
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || JSON.stringify(errJson);
    } catch {
      // ignore
    }
    throw new APIError(errorDetail, response.status);
  }

  return response.json() as Promise<T>;
}

export const api = {
  // System Health & Diagnostics
  getHealth: () => request<SystemHealth>('/health'),
  getReadiness: () => request<SystemReadiness>('/readiness'),
  listModels: async () => {
    const res = await request<{ total: number; models: ModelEntry[] }>('/models');
    return res.models || [];
  },

  // Studies & Ingestion
  listStudies: (limit = 50, offset = 0, patientId?: string) => {
    const q = new URLSearchParams({ limit: String(limit), offset: String(offset) });
    if (patientId) q.append('patient_id', patientId);
    return request<StudyListResponse>(`/studies?${q.toString()}`);
  },

  getStudy: (studyId: string) =>
    request<StudyDetail>(`/studies/${studyId}`),

  getPreviewUrl: (studyId: string) =>
    `${BASE_URL}/studies/${studyId}/preview`,

  getOriginalUrl: (studyId: string) =>
    `${BASE_URL}/studies/${studyId}/original`,

  uploadStudy: async (file: File, patientId?: string, indication?: string, modality?: string) => {
    const formData = new FormData();
    formData.append('file', file);
    if (patientId) formData.append('patient_anonymous_id', patientId);
    if (indication) formData.append('clinical_indication', indication);
    if (modality) formData.append('modality', modality);

    return request<StudyDetail>('/studies/upload', {
      method: 'POST',
      body: formData,
    });
  },

  deleteStudy: (studyId: string, hardDelete = true) =>
    request<void>(`/studies/${studyId}?hard_delete=${hardDelete}`, {
      method: 'DELETE',
    }),

  updateModality: (studyId: string, modality: string) =>
    request<StudyDetail>(`/studies/${studyId}/modality`, {
      method: 'PATCH',
      body: JSON.stringify({ modality }),
    }),

  createAnnotation: (studyId: string, payload: {
    tooth_fdi?: number | null;
    pathology_class: string;
    bbox: { x_min: number; y_min: number; x_max: number; y_max: number };
    clinical_notes?: string;
    anatomical_structure?: string;
  }) =>
    request<Finding>(`/studies/${studyId}/annotations`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  deleteAnnotation: (studyId: string, annotationId: string) =>
    request<void>(`/studies/${studyId}/annotations/${annotationId}`, {
      method: 'DELETE',
    }),

  analyzeStudy: (
    studyId: string,
    modelId = 'liodon-panoramic-screener',
    confThreshold = 0.25,
    iouThreshold = 0.35
  ) =>
    request<AnalysisResponse>(`/studies/${studyId}/analyze`, {
      method: 'POST',
      body: JSON.stringify({
        model_id: modelId,
        conf_threshold: confThreshold,
        iou_threshold: iouThreshold,
      }),
    }),

  // Clinical Evidence
  getEvidence: (studyId: string) =>
    request<ClinicalEvidencePackage>(`/clinical/studies/${studyId}/evidence`),

  submitReview: (studyId: string, findingId: string, payload: ClinicianReviewPayload) =>
    request<any>(`/clinical/studies/${studyId}/findings/${findingId}/review`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  recordExamination: (studyId: string, data: {
    tooth_fdi?: number;
    pulp_vitality?: string;
    percussion_sensitivity?: boolean;
    palpation_sensitivity?: boolean;
    pocket_depth_mm?: number;
    probing_depth_mm?: number;
    clinical_notes?: string;
  }) => {
    const payload = {
      ...data,
      probing_depth_mm: data.probing_depth_mm ?? data.pocket_depth_mm,
    };
    return request<any>(`/clinical/studies/${studyId}/examination`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  recordSymptom: (studyId: string, data: {
    symptom_description: string;
    tooth_fdi?: number;
    duration_days?: number;
    severity?: string;
  }) =>
    request<any>(`/clinical/studies/${studyId}/symptoms`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  selectProcedure: (studyId: string, data: {
    procedure_name: string;
    clinician_rationale: string;
    tooth_fdi?: number;
    suggested_cdt_code?: string;
    cdt_code_verified_by_dentist?: boolean;
    urgency?: string;
    selected_by?: string;
  }) =>
    request<any>(`/clinical/studies/${studyId}/procedure`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getReadinessReport: (studyId: string) =>
    request<EvidenceReadinessReport>(`/clinical/studies/${studyId}/readiness`),

  getAuditTrail: (studyId: string) =>
    request<AuditTrailEntry[]>(`/clinical/studies/${studyId}/audit-trail`),

  // Insurance & Pre-Authorization
  getPreAuthDraft: (studyId: string) =>
    request<InsurancePreAuthDraft>(`/insurance/studies/${studyId}/draft`),

  generatePreAuthDraft: (studyId: string, forceDeterministic = false, modelTag = 'qwen2.5:3b') =>
    request<{ draft: InsurancePreAuthDraft; performance_metrics: any }>(
      `/insurance/studies/${studyId}/draft?force_regenerate=true&model_tag=${forceDeterministic ? 'deterministic' : modelTag}`,
      { method: 'POST' }
    ),

  updatePreAuthDraft: (studyId: string, data: Partial<InsurancePreAuthDraft> & { dentist_name: string; license_number: string }) =>
    request<InsurancePreAuthDraft>(`/insurance/studies/${studyId}/draft`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  getPdfUrl: (studyId: string) =>
    `${BASE_URL}/insurance/studies/${studyId}/claim-pack/pdf`,

  getCDTCatalog: () =>
    request<CDTCodeItem[]>('/insurance/cdt-catalog'),

  // Patient Intake Demographics & Custom PDF Generation
  getPatientInfo: (studyId: string) =>
    request<PatientInfoPayload | null>(`/clinical/studies/${studyId}/patient-info`),

  savePatientInfo: (studyId: string, data: PatientInfoPayload) =>
    request<PatientInfoPayload>(`/clinical/studies/${studyId}/patient-info`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  generateCustomClaimPackPdf: async (studyId: string, req: ClaimReportRequest): Promise<Blob> => {
    const url = `${BASE_URL}/insurance/studies/${studyId}/claim-pack/pdf`;
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(req),
    });
    if (!response.ok) {
      const errText = await response.text().catch(() => response.statusText);
      throw new Error(`Failed to generate clinical PDF report: ${errText}`);
    }
    return response.blob();
  },
};


