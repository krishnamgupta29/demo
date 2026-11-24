import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { api } from '../api/client';
import { StudyDetail, StudyItem, Finding, PatientInfoPayload, ClaimReportRequest } from '../api/types';
import { DentalArch3D } from '../components/3d/DentalArch3D';
import { HeroTooth3D } from '../components/3d/HeroTooth3D';
import { HeroSectionExact } from '../components/hero/HeroSectionExact';
import { RadiographCanvas } from '../components/workstation/RadiographCanvas';
import {
  Upload,
  FileText,
  AlertCircle,
  FileDown,
  Sparkles,
  ShieldCheck,
  RefreshCw,
  Check,
  X,
  User,
  Calendar,
  Edit3,
  CheckCircle2,
  Download,
  Activity,
  Layers,
  ChevronDown,
  ChevronUp,
  Clock,
  Eye,
  FileCheck,
  Shield,
  Stethoscope,
  Scan,
  Maximize2,
  Minimize2,
  TrendingUp,
  Cpu,
  Wifi,
  WifiOff,
  ArrowRight,
  Zap,
  Lock,
  Box,
  ChevronRight,
  Mail,
  MapPin,
  Globe,
  Terminal,
  ExternalLink,
  Sliders,
  CheckSquare,
  AlertTriangle,
} from 'lucide-react';

// ─── Color Palette (Brand Identity: Navy #282b4a & Warm Ivory #eeebda) ────────
const PRIMARY = '#282b4a';
const PRIMARY_DARK = '#1b1e36';
const PRIMARY_LIGHT = '#3f436c';
const BG_WARM = '#eeebda';
const SURFACE_CARD = '#f7f5ed';
const SURFACE_PANEL = '#ffffff';
const BORDER_WARM = '#ded8c4';
const BORDER_STRONG = '#cbcaa6';
const TEXT_MAIN = '#282b4a';
const TEXT_MUTED = '#575a75';
const YELLOW_CANDIDATE = '#facc15';
const GREEN_CONFIRMED = '#15803d';
const GREY_DISMISSED = '#64748b';

// ─── View State for 4 Connected Experiences ────────────────────────────────
type AppView = 'landing' | 'registration' | 'studio';

// ─── CSS Keyframes & Global Animations ──────────────────────────────────────
const GLOBAL_EXPERIENCE_STYLES = `
@keyframes heroFadeIn {
  from { opacity: 0; transform: translateY(28px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes heroSlideUp {
  from { opacity: 0; transform: translateY(18px); }
  to   { opacity: 1; transform: translateY(0); }
}
@keyframes floatGentle {
  0%, 100% { transform: translateY(0); }
  50%      { transform: translateY(-6px); }
}
@keyframes pulseSubtle {
  0%, 100% { opacity: 0.8; }
  50%      { opacity: 1; }
}
@keyframes sectionEnter {
  from { opacity: 0; transform: translateY(20px); }
  to   { opacity: 1; transform: translateY(0); }
}
html {
  scroll-behavior: smooth;
}
`;

export const DentraceStudioView: React.FC = () => {
  // ─── 4-Stage Connected Experience State ─────────────────────────────────────
  // 1. 'landing'      = Public presentation & marketing
  // 2. 'registration' = Patient intake & examination setup
  // 3. 'studio'       = Clinical examination, canvas & 3D findings
  // 4. Modal          = Simple, professional 5-page PDF claim report
  // Default directly to Studio Workspace
  const [view, setView] = useState<AppView>('studio');
  const [theme, setTheme] = useState<'light' | 'dark'>(() => {
    const saved = localStorage.getItem('dentrace_theme');
    return saved === 'light' || saved === 'dark' ? saved : 'dark';
  });

  const handleToggleTheme = useCallback(() => {
    setTheme((prev) => {
      const next = prev === 'light' ? 'dark' : 'light';
      localStorage.setItem('dentrace_theme', next);
      return next;
    });
  }, []);

  // ─── Persistent Application State ──────────────────────────────────────────
  const [currentStudy, setCurrentStudy] = useState<StudyDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [analyzing, setAnalyzing] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [recentStudies, setRecentStudies] = useState<StudyItem[]>([]);
  const [systemHealth, setSystemHealth] = useState<'healthy' | 'checking' | 'offline'>('checking');

  // Patient History State
  const [patientHistory, setPatientHistory] = useState<StudyItem[]>([]);
  const [loadingHistory, setLoadingHistory] = useState<boolean>(false);
  const [comparingStudy, setComparingStudy] = useState<StudyDetail | null>(null);

  // Active interaction state
  const [selectedFdi, setSelectedFdi] = useState<number | null>(null);
  const [selectedFindingId, setSelectedFindingId] = useState<string | null>(null);
  const [activeModel, setActiveModel] = useState<string>('liodon-panoramic-screener');
  const [activeAnatomicalStructure, setActiveAnatomicalStructure] = useState<string | null>(null);

  // Modality Selection State
  const [selectedModality, setSelectedModality] = useState<string>('panoramic_opg');

  // Workflow progress stepper active step
  const activeStep = useMemo(() => {
    if (!currentStudy) return 1;
    if (currentStudy.findings && currentStudy.findings.length > 0) return 4;
    if (analyzing) return 3;
    return 2;
  }, [currentStudy, analyzing]);

  const handleSelectAnatomicalStructure = useCallback((structure: string) => {
    setActiveAnatomicalStructure(structure);
  }, []);

  // ─── Persistent Unique Patient Identifier ─────────────────────────────────
  // Generated ONCE and never re-generated on re-renders
  const uniquePatientId = useMemo(() => {
    const hex = Math.random().toString(36).substring(2, 8).toUpperCase();
    return `PT-${hex}`;
  }, []);

  // Patient Intake Form State (9 Fields)
  const [patientInfo, setPatientInfo] = useState<PatientInfoPayload>({
    patient_name: '',
    patient_id: uniquePatientId,
    age: 0,
    sex: 'unspecified',
    scan_date: new Date().toISOString().split('T')[0],
    chief_complaint: '',
    symptoms: '',
    history: '',
    referring_dentist: '',
  });

  const [patientFormErrors, setPatientFormErrors] = useState<Record<string, string>>({});
  const [fdiEditFindingId, setFdiEditFindingId] = useState<string | null>(null);
  const [manualFdiInput, setManualFdiInput] = useState<number | ''>('');

  // Pre-Authorization Report Studio Modal State
  const [showReportModal, setShowReportModal] = useState<boolean>(false);
  const [reportNarrative, setReportNarrative] = useState<string>('');
  const [isGeneratingNarrative, setIsGeneratingNarrative] = useState<boolean>(false);
  const [isExportingPdf, setIsExportingPdf] = useState<boolean>(false);
  const [snapshotPreviewUrl, setSnapshotPreviewUrl] = useState<string | null>(null);
  const [dentistAttested, setDentistAttested] = useState<boolean>(true);

  // Drag and drop state
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ─── Inject CSS Keyframes ───────────────────────────────────────────────────
  useEffect(() => {
    const id = 'dentrace-global-experience-styles';
    if (!document.getElementById(id)) {
      const style = document.createElement('style');
      style.id = id;
      style.textContent = GLOBAL_EXPERIENCE_STYLES;
      document.head.appendChild(style);
    }
  }, []);

  // ─── Health & Studies Polling ─────────────────────────────────────────────
  const refreshStudiesList = async () => {
    try {
      const res = await api.listStudies(50, 0);
      setRecentStudies(res.items || res.studies || []);
    } catch {
      // ignore
    }
  };

  useEffect(() => {
    fetch('/api/v1/health')
      .then((r) => (r.ok ? setSystemHealth('healthy') : setSystemHealth('offline')))
      .catch(() => setSystemHealth('offline'));
    refreshStudiesList();

    // Directly populate Studio with active clinical study on launch
    api.listStudies(50, 0).then((res) => {
      const items = res.items || (res as any).studies || [];
      const sample = items.find((s) => s.study_id === 'CASE-C4CAC301') || items.find((s) => (s.radiograph as any)?.modality === 'panoramic_opg' && s.status === 'analyzed') || items[0];
      if (sample) {
        api.getStudy(sample.study_id).then((detail) => {
          setCurrentStudy(detail);
          setSelectedModality((detail.radiograph as any)?.modality || 'panoramic_opg');
          if (detail.patient_anonymous_id) {
            setPatientInfo((prev) => ({ ...prev, patient_id: detail.patient_anonymous_id || prev.patient_id }));
          }
          if (detail.findings && detail.findings.length > 0) {
            setSelectedFindingId(detail.findings[0].finding_id);
            if (detail.findings[0].tooth_fdi) {
              setSelectedFdi(detail.findings[0].tooth_fdi);
            }
          }
        }).catch((err) => {
          console.error('[DEBUG] Failed to load initial sample study:', err);
        });
      }
    }).catch((err) => {
      console.error('[DEBUG] Failed to list studies:', err);
    });
  }, []);

  // Fetch previous scans strictly matching current patient ID
  const fetchPatientHistory = useCallback(async (patientId: string) => {
    if (!patientId || patientId.trim() === '') {
      setPatientHistory([]);
      return;
    }
    setLoadingHistory(true);
    try {
      const res = await api.listStudies(10, 0, patientId.trim());
      const items = res.items || res.studies || [];
      setPatientHistory(items.filter((s) => s.study_id !== currentStudy?.study_id).slice(0, 3));
    } catch (e) {
      console.warn('Patient history fetch notice:', e);
      setPatientHistory([]);
    } finally {
      setLoadingHistory(false);
    }
  }, [currentStudy?.study_id]);

  useEffect(() => {
    if (patientInfo.patient_id && view === 'studio') {
      fetchPatientHistory(patientInfo.patient_id);
    }
  }, [patientInfo.patient_id, fetchPatientHistory, view]);

  // Synchronize patient info when study loads
  useEffect(() => {
    if (currentStudy) {
      api.getPatientInfo(currentStudy.study_id)
        .then((saved) => {
          if (saved) {
            setPatientInfo(saved);
          } else if (currentStudy.patient_anonymous_id) {
            setPatientInfo((prev) => ({
              ...prev,
              patient_id: currentStudy.patient_anonymous_id || prev.patient_id,
            }));
          }
        })
        .catch(() => {});
      const mod = (currentStudy.radiograph as any)?.modality;
      if (mod) setSelectedModality(mod);
    }
  }, [currentStudy?.study_id]);

  // ─── Form Validation Engine ────────────────────────────────────────────────
  const validatePatientForm = (): boolean => {
    const errors: Record<string, string> = {};
    if (!patientInfo.patient_name || patientInfo.patient_name.trim() === '') {
      errors.patient_name = 'Patient full name is required.';
    }
    if (!patientInfo.patient_id || patientInfo.patient_id.trim() === '') {
      errors.patient_id = 'Patient ID is required.';
    }
    const ageNum = Number(patientInfo.age);
    if (!patientInfo.age || isNaN(ageNum) || ageNum < 1 || ageNum > 125) {
      errors.age = 'Age must be a valid number between 1 and 125.';
    }
    if (!patientInfo.scan_date || patientInfo.scan_date.trim() === '') {
      errors.scan_date = 'Examination date is required.';
    }
    if (!patientInfo.chief_complaint || patientInfo.chief_complaint.trim() === '') {
      errors.chief_complaint = 'Chief clinical complaint is required.';
    }
    setPatientFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleStartRegistration = () => {
    setView('registration');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleCompleteRegistration = async () => {
    if (!validatePatientForm()) {
      setErrorMessage('Please complete all required fields highlighted in red.');
      return;
    }
    setErrorMessage(null);
    setSuccessMessage(`Patient record validated for ${patientInfo.patient_name} (${patientInfo.patient_id}).`);
    setTimeout(() => setSuccessMessage(null), 3000);
    setView('studio');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  // ─── Case Loading & Uploading ──────────────────────────────────────────────
  const handleSelectCase = async (studyId: string) => {
    if (!studyId || studyId === currentStudy?.study_id) return;
    setLoading(true);
    setErrorMessage(null);
    setComparingStudy(null);
    try {
      const detail = await api.getStudy(studyId);
      setCurrentStudy(detail);
      if (detail.findings && detail.findings.length > 0) {
        setSelectedFindingId(detail.findings[0].finding_id);
        if (detail.findings[0].tooth_fdi) {
          setSelectedFdi(detail.findings[0].tooth_fdi);
        }
      } else {
        setSelectedFindingId(null);
        setSelectedFdi(null);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to switch case.');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadSample = async () => {
    setLoading(true);
    setErrorMessage(null);
    setComparingStudy(null);
    try {
      const sampleId = 'CASE-D49166F1';
      const detail = await api.getStudy(sampleId).catch(async () => {
        const res = await api.listStudies(1, 0);
        const first = (res.items || res.studies || [])[0];
        if (first) return await api.getStudy(first.study_id);
        throw new Error('No existing cases found in database.');
      });

      setCurrentStudy(detail);
      setSelectedModality((detail.radiograph as any)?.modality || 'panoramic_opg');
      if (detail.findings && detail.findings.length > 0) {
        setSelectedFindingId(detail.findings[0].finding_id);
        if (detail.findings[0].tooth_fdi) {
          setSelectedFdi(detail.findings[0].tooth_fdi);
        }
      }
      setPatientInfo((prev) => ({
        ...prev,
        patient_name: prev.patient_name || 'Eleanor Vance',
        patient_id: detail.patient_anonymous_id || prev.patient_id,
        age: prev.age || 38,
        chief_complaint: prev.chief_complaint || 'Localized sensitivity on quadrant 3 upon cold mastication',
      }));
      setView('studio');
      setSuccessMessage(`Loaded verified case ${detail.study_id} with ${detail.findings?.length || 0} candidate detections.`);
      setTimeout(() => setSuccessMessage(null), 3500);
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to load sample clinical case.');
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (file: File) => {
    if (!file) return;

    const validTypes = ['image/png', 'image/jpeg', 'application/dicom'];
    const validExtensions = ['.png', '.jpg', '.jpeg', '.dcm', '.dicom'];
    const fileName = file.name.toLowerCase();
    const hasValidExt = validExtensions.some((ext) => fileName.endsWith(ext));

    if (!validTypes.includes(file.type) && !hasValidExt) {
      setErrorMessage('Unsupported format. Please upload PNG, JPEG, or DICOM radiographs.');
      return;
    }

    setLoading(true);
    setAnalyzing(true);
    setErrorMessage(null);
    setComparingStudy(null);

    try {
      const activePatientId = patientInfo.patient_id || uniquePatientId;
      const uploadedStudy = await api.uploadStudy(
        file,
        activePatientId,
        patientInfo.chief_complaint || 'Dental Radiograph Intake',
        selectedModality
      );

      try {
        await api.savePatientInfo(uploadedStudy.study_id, {
          ...patientInfo,
          patient_id: activePatientId,
        });
      } catch (e) {}

      // Modality-guided neural inference routing
      const mod = selectedModality || (uploadedStudy.radiograph as any)?.modality;
      if (mod === 'intraoral_periapical') {
        setActiveModel('iopa-periapical-screener');
        try {
          await api.analyzeStudy(uploadedStudy.study_id, 'iopa-periapical-screener', 0.20, 0.35);
        } catch (analErr) {
          console.warn('Inference notice:', analErr);
        }
      } else if (mod === 'panoramic_opg') {
        const modelToUse = activeModel === 'iopa-periapical-screener' ? 'liodon-panoramic-screener' : activeModel;
        setActiveModel(modelToUse);
        try {
          await api.analyzeStudy(uploadedStudy.study_id, modelToUse, 0.25, 0.35);
        } catch (analErr) {
          console.warn('Inference notice:', analErr);
        }
      }

      const reloaded = await api.getStudy(uploadedStudy.study_id);
      setCurrentStudy(reloaded);

      if (reloaded.findings && reloaded.findings.length > 0) {
        setSelectedFindingId(reloaded.findings[0].finding_id);
        if (reloaded.findings[0].tooth_fdi) {
          setSelectedFdi(reloaded.findings[0].tooth_fdi);
        }
      }
      refreshStudiesList();
      fetchPatientHistory(activePatientId);
      setSuccessMessage(`Ingested ${file.name} under ${selectedModality.replace(/_/g, ' ').toUpperCase()}.`);
      setTimeout(() => setSuccessMessage(null), 3500);
    } catch (err: any) {
      setErrorMessage(err.message || 'Error processing uploaded radiograph.');
    } finally {
      setLoading(false);
      setAnalyzing(false);
    }
  };

  // ─── AI Model Inference & Safety Gating ────────────────────────────────────
  const handleRunAnalysis = async (studyId?: string, overrideModel?: string) => {
    const targetId = studyId || currentStudy?.study_id;
    if (!targetId) return;
    setAnalyzing(true);
    setErrorMessage(null);
    try {
      const currentMod = overrideModel === 'liodon-panoramic-screener'
        ? 'panoramic_opg'
        : overrideModel === 'iopa-periapical-screener'
        ? 'intraoral_periapical'
        : (currentStudy?.radiograph as any)?.modality || selectedModality;

      if (currentMod === 'unknown') {
        setErrorMessage('Radiograph modality is unconfirmed. Please select and confirm modality before running AI analysis.');
        setAnalyzing(false);
        return;
      }
      if (currentMod === 'bitewing') {
        setErrorMessage('Automated AI models are unsupported for bitewing modality. Please utilize manual inspection tools.');
        setAnalyzing(false);
        return;
      }

      let modelToUse = overrideModel || activeModel;
      if (currentMod === 'intraoral_periapical') {
        modelToUse = 'iopa-periapical-screener';
        setActiveModel('iopa-periapical-screener');
      } else if (currentMod === 'panoramic_opg') {
        modelToUse = 'liodon-panoramic-screener';
        setActiveModel('liodon-panoramic-screener');
      }
      const analRes = await api.analyzeStudy(targetId, modelToUse, 0.20, 0.35);
      if (analRes.status === 'modality_unsupported') {
        setErrorMessage(analRes.notice || 'Automated AI analysis is not supported for this radiograph modality.');
      } else {
        setSuccessMessage(`Analysis complete: ${analRes.findings_detected || 0} candidate anomaly reticles identified.`);
        setTimeout(() => setSuccessMessage(null), 3500);
      }
      const reloaded = await api.getStudy(targetId);
      setCurrentStudy(reloaded);
      if (reloaded.findings && reloaded.findings.length > 0) {
        setSelectedFindingId(reloaded.findings[0].finding_id);
        if (reloaded.findings[0].tooth_fdi) {
          setSelectedFdi(reloaded.findings[0].tooth_fdi);
        }
      }
      refreshStudiesList();
    } catch (err: any) {
      setErrorMessage(err.message || 'Error executing AI model analysis.');
    } finally {
      setAnalyzing(false);
    }
  };

  const handleUpdateModality = async (modality: string) => {
    setSelectedModality(modality);
    if (!currentStudy) return;
    try {
      const updated = await api.updateModality(currentStudy.study_id, modality);
      setCurrentStudy(updated);
      const targetModel = modality === 'panoramic_opg' ? 'liodon-panoramic-screener' : 'iopa-periapical-screener';
      setActiveModel(targetModel);
      setSuccessMessage(`Modality switched to ${modality.replace(/_/g, ' ').toUpperCase()}. Re-running neural screener...`);
      setTimeout(() => setSuccessMessage(null), 3000);

      await handleRunAnalysis(updated.study_id, targetModel);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to update radiograph modality.');
    }
  };

  // ─── Tooth Selection & Clinician Audit ─────────────────────────────────────
  const handleSelectTooth = useCallback((fdi: number) => {
    setSelectedFdi(fdi);
    setCurrentStudy((prev) => {
      if (!prev) return prev;
      const matching = prev.findings.find((f) => f.tooth_fdi === fdi);
      if (matching) {
        setSelectedFindingId(matching.finding_id);
      }
      return prev;
    });
  }, []);

  const handleReviewFinding = async (findingId: string, decision: 'confirmed' | 'rejected') => {
    if (!currentStudy) return;
    try {
      await api.submitReview(currentStudy.study_id, findingId, {
        reviewer_name: patientInfo.referring_dentist || 'Dr. Reviewer, DDS',
        license_number: 'LIC-DDS-LOCAL',
        decision: decision,
      });

      setCurrentStudy((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          findings: prev.findings.map((item) =>
            item.finding_id === findingId ? { ...item, review_status: decision } : item
          ),
        };
      });
      setSuccessMessage(`Finding ${findingId} marked as ${decision.toUpperCase()}.`);
      setTimeout(() => setSuccessMessage(null), 2500);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to record review decision.');
    }
  };

  const handleCorrectFdi = async (findingId: string, newFdi: number) => {
    if (!currentStudy || !newFdi) return;
    try {
      await api.submitReview(currentStudy.study_id, findingId, {
        reviewer_name: patientInfo.referring_dentist || 'Dr. Reviewer, DDS',
        license_number: 'LIC-DDS-LOCAL',
        decision: 'corrected',
        confirmed_fdi: newFdi,
      });

      setCurrentStudy((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          findings: prev.findings.map((item) =>
            item.finding_id === findingId ? { ...item, tooth_fdi: newFdi, review_status: 'confirmed' } : item
          ),
        };
      });
      setFdiEditFindingId(null);
      setSuccessMessage(`Corrected finding #${findingId} to FDI #${newFdi}. Audit event logged.`);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to correct tooth number.');
    }
  };

  const handleCreateAnnotation = async (bbox: { x_min: number; y_min: number; x_max: number; y_max: number }) => {
    if (!currentStudy) return;
    try {
      const created = await api.createAnnotation(currentStudy.study_id, {
        tooth_fdi: selectedFdi,
        pathology_class: 'caries',
        bbox,
        clinical_notes: 'Clinician manual region annotation',
        anatomical_structure: activeAnatomicalStructure || undefined,
      });

      setCurrentStudy((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          findings: [...prev.findings, created],
        };
      });
      setSelectedFindingId(created.finding_id);
      setSuccessMessage(`Manual annotation saved for FDI #${selectedFdi || 'General'}.`);
      setTimeout(() => setSuccessMessage(null), 3000);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to save manual annotation region.');
    }
  };

  const handleDeleteAnnotation = async (findingId: string) => {
    if (!currentStudy) return;
    try {
      await api.deleteAnnotation(currentStudy.study_id, findingId);
      setCurrentStudy((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          findings: prev.findings.filter((f) => f.finding_id !== findingId),
        };
      });
      if (selectedFindingId === findingId) setSelectedFindingId(null);
      setSuccessMessage('Annotation region removed.');
      setTimeout(() => setSuccessMessage(null), 2500);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to delete annotation.');
    }
  };

  // ─── 5-Page Pre-Authorization Report Studio ────────────────────────────────
  const handleOpenReportStudio = async () => {
    if (!currentStudy) return;

    try {
      const canvas = document.querySelector('canvas') as HTMLCanvasElement | null;
      if (canvas) {
        const snap = canvas.toDataURL('image/png');
        setSnapshotPreviewUrl(snap);
      }
    } catch (e) {
      console.warn('Canvas snapshot capture notice:', e);
    }

    setShowReportModal(true);

    if (!reportNarrative) {
      setIsGeneratingNarrative(true);
      try {
        const res = await api.generatePreAuthDraft(currentStudy.study_id, false, 'qwen2.5:3b');
        if (res && res.draft) {
          const initialText = [
            `Patient: ${patientInfo.patient_name} (Age: ${patientInfo.age}, Scan Date: ${patientInfo.scan_date})`,
            `Chief Complaint: ${patientInfo.chief_complaint || 'Routine dental evaluation'}`,
            '',
            `Clinical Findings & Diagnostic Justification:`,
            `Panoramic radiograph analysis identifies clinical indications requiring dental restorative intervention. Radiographic observations indicate suspected pathology localized to the flagged dental quadrant.`,
            '',
            `Proposed Treatment:`,
            `Comprehensive oral evaluation, direct composite restorative therapy (CDT D2391) and indicated endodontic / periodontal assessment.`,
            '',
            `Clinician Attestation:`,
            `I personally reviewed the panoramic radiograph and clinical evidence and attest to the medical necessity of the proposed procedure.`,
          ].join('\n');
          setReportNarrative(initialText);
        }
      } catch (err) {
        const fallbackText = `Patient: ${patientInfo.patient_name} (Case: ${patientInfo.patient_id})\nChief Complaint: ${patientInfo.chief_complaint || 'Routine examination'}\n\nClinical Justification:\nComprehensive evaluation and dental anomaly detection based on panoramic radiograph. Proposed composite restoration (CDT D2391) and indicated monitoring.`;
        setReportNarrative(fallbackText);
      } finally {
        setIsGeneratingNarrative(false);
      }
    }
  };

  const handleDownloadReport = async () => {
    if (!currentStudy) return;
    if (!validatePatientForm()) {
      setShowReportModal(false);
      setView('registration');
      setErrorMessage('Please complete patient demographic fields before exporting PDF.');
      return;
    }

    setIsExportingPdf(true);
    setErrorMessage(null);

    try {
      let snapB64 = snapshotPreviewUrl;
      if (!snapB64) {
        const canvas = document.querySelector('canvas') as HTMLCanvasElement | null;
        if (canvas) snapB64 = canvas.toDataURL('image/png');
      }

      const activeF = findings.find((f) => f.finding_id === selectedFindingId) || findings[0];

      const reportReq: ClaimReportRequest = {
        patient_info: patientInfo,
        custom_narrative: reportNarrative,
        snapshot_3d_base64: snapB64 || undefined,
        selected_fdi: selectedFdi || activeF?.tooth_fdi,
        selected_pathology: activeF?.pathology_class || 'Caries',
      };

      const pdfBlob = await api.generateCustomClaimPackPdf(currentStudy.study_id, reportReq);

      const blobUrl = window.URL.createObjectURL(pdfBlob);
      const downloadLink = document.createElement('a');
      downloadLink.href = blobUrl;
      downloadLink.download = `DENTRACE_${currentStudy.study_id}_ClinicalReport_5Page.pdf`;
      document.body.appendChild(downloadLink);
      downloadLink.click();
      document.body.removeChild(downloadLink);
      window.URL.revokeObjectURL(blobUrl);

      setSuccessMessage('Clean, professional 5-Page Clinical Report PDF generated and downloaded successfully.');
      setTimeout(() => setSuccessMessage(null), 4000);
      setShowReportModal(false);
    } catch (err: any) {
      setErrorMessage(err.message || 'Failed to generate PDF report.');
    } finally {
      setIsExportingPdf(false);
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  };

  const handleReset = () => {
    setCurrentStudy(null);
    setSelectedFindingId(null);
    setSelectedFdi(null);
    setErrorMessage(null);
    setReportNarrative('');
    setComparingStudy(null);
  };

  const handleReturnToLanding = () => {
    setView('studio');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const findings = useMemo(() => currentStudy?.findings || [], [currentStudy?.findings]);
  const confirmedCount = findings.filter((f) => f.review_status === 'confirmed').length;
  const dismissedCount = findings.filter((f) => f.review_status === 'rejected').length;

  // Direct Studio Workspace Only
  if (view === 'landing') {
    setView('studio');
    return null;
  }

  // ═══════════════════════════════════════════════════════════════════════════
  //  EXPERIENCE 2: PATIENT REGISTRATION & EXAMINATION SETUP
  // ═══════════════════════════════════════════════════════════════════════════
  if (view === 'registration') {
    return (
      <div style={{ minHeight: '100vh', backgroundColor: BG_WARM, color: TEXT_MAIN, display: 'flex', flexDirection: 'column' }}>
        {/* Registration Header */}
        <header
          style={{
            padding: '16px 48px',
            backgroundColor: '#FFFFFF',
            borderBottom: `1px solid ${BORDER_WARM}`,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <button
              type="button"
              onClick={handleReturnToLanding}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                background: 'transparent',
                border: 'none',
                color: PRIMARY,
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
              }}
            >
              <ChevronDown size={16} style={{ transform: 'rotate(90deg)' }} />
              <span>Back to Landing Page</span>
            </button>
            <div style={{ width: '1px', height: '18px', backgroundColor: BORDER_WARM }} />
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div
                style={{
                  width: '28px',
                  height: '28px',
                  borderRadius: '6px',
                  backgroundColor: PRIMARY,
                  color: '#FFFFFF',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 800,
                  fontSize: '12px',
                }}
              >
                DT
              </div>
              <span style={{ fontSize: '15px', fontWeight: 800, color: PRIMARY }}>DENTRACE Registration</span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '12px', color: TEXT_MUTED }}>
            <span style={{ fontWeight: 600, color: PRIMARY }}>Step 1 of 2:</span>
            <span>Demographic Intake &amp; Modality Selection</span>
          </div>
        </header>

        {/* Alerts */}
        <div style={{ maxWidth: '880px', width: '100%', margin: '0 auto', padding: '16px 48px 0', boxSizing: 'border-box' }}>
          {errorMessage && (
            <div
              style={{
                backgroundColor: '#FEF2F2',
                border: '1px solid #FECACA',
                color: '#991B1B',
                borderRadius: '8px',
                padding: '10px 16px',
                marginBottom: '14px',
                fontSize: '12.5px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertCircle size={16} />
                <span>{errorMessage}</span>
              </div>
              <button onClick={() => setErrorMessage(null)} style={{ background: 'transparent', border: 'none', color: '#991B1B', cursor: 'pointer' }}>
                <X size={14} />
              </button>
            </div>
          )}
        </div>

        {/* Registration Form Body */}
        <div style={{ flex: 1, display: 'flex', justifyContent: 'center', padding: '24px 48px 60px', animation: 'sectionEnter 0.4s ease-out both' }}>
          <div style={{ width: '100%', maxWidth: '880px' }}>
            <div style={{ marginBottom: '28px' }}>
              <h1 style={{ fontSize: '30px', fontWeight: 800, color: PRIMARY, margin: '0 0 6px 0', letterSpacing: '-0.02em' }}>
                Patient Registration &amp; Examination Setup
              </h1>
              <p style={{ fontSize: '14.5px', color: TEXT_MUTED, margin: 0, lineHeight: 1.5 }}>
                Fill in the required clinical details below. An immutable, unique Patient ID has been automatically generated for this session.
              </p>
            </div>

            <div
              style={{
                backgroundColor: SURFACE_PANEL,
                border: `1px solid ${BORDER_WARM}`,
                borderRadius: '16px',
                padding: '36px',
                boxShadow: '0 4px 16px rgba(40, 43, 74, 0.05)',
              }}
            >
              {/* Row 1: Name & Read-Only Patient ID */}
              <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '20px', marginBottom: '20px' }}>
                <FormField label="1. Patient Full Name" required error={patientFormErrors.patient_name}>
                  <input
                    type="text"
                    value={patientInfo.patient_name}
                    onChange={(e) => setPatientInfo({ ...patientInfo, patient_name: e.target.value })}
                    placeholder="e.g. Eleanor Vance"
                    style={inputStyle(!!patientFormErrors.patient_name)}
                  />
                </FormField>

                <FormField label="2. Patient Identifier (Auto-Generated Unique)" required>
                  <div style={{ position: 'relative' }}>
                    <input
                      type="text"
                      value={patientInfo.patient_id}
                      readOnly
                      style={{
                        ...inputStyle(false),
                        backgroundColor: '#F8FAFC',
                        color: PRIMARY,
                        fontFamily: 'monospace',
                        fontWeight: 700,
                        cursor: 'not-allowed',
                        paddingRight: '36px',
                      }}
                    />
                    <Lock size={15} color="#94A3B8" style={{ position: 'absolute', right: '12px', top: '12px' }} />
                  </div>
                  <span style={{ fontSize: '10.5px', color: TEXT_MUTED, display: 'block', marginTop: '3px' }}>
                    Immutable unique session token (locked against edits)
                  </span>
                </FormField>
              </div>

              {/* Row 2: Age, Sex, Scan Date */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1.2fr', gap: '20px', marginBottom: '20px' }}>
                <FormField label="3. Age (Years)" required error={patientFormErrors.age}>
                  <input
                    type="number"
                    min="1"
                    max="125"
                    value={patientInfo.age || ''}
                    onChange={(e) => setPatientInfo({ ...patientInfo, age: parseInt(e.target.value) || 0 })}
                    placeholder="e.g. 38"
                    style={inputStyle(!!patientFormErrors.age)}
                  />
                </FormField>

                <FormField label="4. Sex">
                  <select
                    value={patientInfo.sex || 'unspecified'}
                    onChange={(e) => setPatientInfo({ ...patientInfo, sex: e.target.value })}
                    style={inputStyle(false)}
                  >
                    <option value="female">Female</option>
                    <option value="male">Male</option>
                    <option value="other">Other</option>
                    <option value="unspecified">Unspecified</option>
                  </select>
                </FormField>

                <FormField label="5. Examination Date" required error={patientFormErrors.scan_date}>
                  <input
                    type="date"
                    value={patientInfo.scan_date}
                    onChange={(e) => setPatientInfo({ ...patientInfo, scan_date: e.target.value })}
                    style={inputStyle(!!patientFormErrors.scan_date)}
                  />
                </FormField>
              </div>

              {/* Row 3: Chief Complaint (Required) & Symptoms */}
              <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '20px', marginBottom: '20px' }}>
                <FormField label="6. Chief Complaint" required error={patientFormErrors.chief_complaint}>
                  <input
                    type="text"
                    value={patientInfo.chief_complaint || ''}
                    onChange={(e) => setPatientInfo({ ...patientInfo, chief_complaint: e.target.value })}
                    placeholder="e.g. Sensitivity upon cold mastication on lower left quadrant"
                    style={inputStyle(!!patientFormErrors.chief_complaint)}
                  />
                </FormField>

                <FormField label="7. Symptoms">
                  <input
                    type="text"
                    value={patientInfo.symptoms || ''}
                    onChange={(e) => setPatientInfo({ ...patientInfo, symptoms: e.target.value })}
                    placeholder="e.g. Sharp response to cold liquids; mild ache"
                    style={inputStyle(false)}
                  />
                </FormField>
              </div>

              {/* Row 4: Relevant History & Referring Dentist */}
              <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '20px', marginBottom: '28px' }}>
                <FormField label="8. Relevant Dental History">
                  <input
                    type="text"
                    value={patientInfo.history || ''}
                    onChange={(e) => setPatientInfo({ ...patientInfo, history: e.target.value })}
                    placeholder="e.g. Composite restorations in 2022; no known systemic contraindications"
                    style={inputStyle(false)}
                  />
                </FormField>

                <FormField label="9. Referring Dentist or Clinic">
                  <input
                    type="text"
                    value={patientInfo.referring_dentist || ''}
                    onChange={(e) => setPatientInfo({ ...patientInfo, referring_dentist: e.target.value })}
                    placeholder="e.g. Dr. Robert Thorne, DDS"
                    style={inputStyle(false)}
                  />
                </FormField>
              </div>

              {/* Modality Selector with Strict Model Restrictions */}
              <div style={{ borderTop: `1px solid ${BORDER_WARM}`, paddingTop: '24px', marginBottom: '32px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                  <Scan size={18} color={PRIMARY} />
                  <span style={{ fontSize: '15px', fontWeight: 700, color: PRIMARY }}>
                    Examination Radiograph Modality
                  </span>
                  <span style={{ fontSize: '12px', color: '#DC2626', fontWeight: 600 }}>*</span>
                </div>
                <p style={{ fontSize: '12.5px', color: TEXT_MUTED, margin: '0 0 16px 0' }}>
                  Safety constraint: OPG-trained neural models will only run on supported Panoramic OPG scans. Bitewing radiographs are restricted to manual calipers inspection.
                </p>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
                  {[
                    { id: 'panoramic_opg', label: 'Panoramic OPG', sub: 'DENTEX Supported' },
                    { id: 'intraoral_periapical', label: 'Periapical (IOPA)', sub: 'YOLO11n Supported' },
                    { id: 'bitewing', label: 'Bitewing', sub: 'Manual Calipers Only' },
                    { id: 'unknown', label: 'Unknown / Other', sub: 'Requires Review' },
                  ].map((m) => {
                    const isSelected = selectedModality === m.id;
                    return (
                      <button
                        key={m.id}
                        type="button"
                        onClick={() => setSelectedModality(m.id)}
                        style={{
                          padding: '14px 12px',
                          borderRadius: '10px',
                          border: isSelected ? `2px solid ${PRIMARY}` : `1.5px solid ${BORDER_WARM}`,
                          backgroundColor: isSelected ? PRIMARY : SURFACE_CARD,
                          color: isSelected ? '#FFFFFF' : TEXT_MAIN,
                          cursor: 'pointer',
                          textAlign: 'center',
                          transition: 'all 0.15s ease',
                        }}
                      >
                        <div style={{ fontSize: '13px', fontWeight: 700 }}>{m.label}</div>
                        <div style={{ fontSize: '10.5px', opacity: isSelected ? 0.85 : 0.65, marginTop: '2px' }}>
                          {m.sub}
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Action Buttons */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
                <button
                  type="button"
                  onClick={handleCompleteRegistration}
                  style={{
                    padding: '14px 32px',
                    borderRadius: '8px',
                    border: 'none',
                    backgroundColor: PRIMARY,
                    color: '#FFFFFF',
                    fontSize: '15px',
                    fontWeight: 700,
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    boxShadow: '0 4px 14px rgba(40, 43, 74, 0.20)',
                    transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = PRIMARY_LIGHT)}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = PRIMARY)}
                >
                  <span>Proceed to DENTRACE Studio</span>
                  <ArrowRight size={17} />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Registration Footer */}
        <footer style={{ padding: '20px 48px', borderTop: `1px solid ${BORDER_WARM}`, textAlign: 'center' }}>
          <span style={{ fontSize: '11px', color: '#991B1B', fontWeight: 500 }}>
            Draft for dentist review. Not a diagnosis. Not certified under FDA / CE / MDR. Academic College Decision Support.
          </span>
        </footer>
      </div>
    );
  }

  // ═══════════════════════════════════════════════════════════════════════════
  //  EXPERIENCE 3: DENTRACE STUDIO (EXAMINATION WORKSPACE)
  // ═══════════════════════════════════════════════════════════════════════════
  return (
    <div
      style={{
        minHeight: '100vh',
        width: '100%',
        backgroundColor: BG_WARM,
        color: TEXT_MAIN,
        fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* ─── Sticky Clinical Header ───────────────────────────────────────── */}
      <header
        style={{
          position: 'sticky',
          top: 0,
          zIndex: 100,
          backgroundColor: '#FFFFFF',
          borderBottom: `1px solid ${BORDER_WARM}`,
          boxShadow: '0 1px 3px rgba(40, 43, 74, 0.05)',
          padding: '0 24px',
          height: '56px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}
      >
        {/* Left: Brand & Return */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <button
            type="button"
            onClick={handleReturnToLanding}
            title="Return to DENTRACE Overview"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              background: 'transparent',
              border: 'none',
              cursor: 'pointer',
              color: PRIMARY,
              padding: '4px 6px',
              borderRadius: '4px',
            }}
          >
            <div
              style={{
                width: '30px',
                height: '30px',
                borderRadius: '6px',
                background: PRIMARY,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#FFFFFF',
                fontWeight: 800,
                fontSize: '12px',
              }}
            >
              DT
            </div>
            <span style={{ fontSize: '15px', fontWeight: 800, letterSpacing: '0.04em', color: PRIMARY }}>
              DENTRACE STUDIO
            </span>
          </button>

          {/* Active Patient Badge Pill */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              borderLeft: `1px solid ${BORDER_WARM}`,
              paddingLeft: '14px',
            }}
          >
            <div
              style={{
                padding: '4px 10px',
                borderRadius: '6px',
                backgroundColor: SURFACE_CARD,
                border: `1px solid ${BORDER_WARM}`,
                fontSize: '11.5px',
                fontWeight: 600,
                color: PRIMARY,
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
              }}
            >
              <User size={13} color={PRIMARY} />
              <span>{patientInfo.patient_name || 'Patient'} ({patientInfo.patient_id})</span>
              <span style={{ color: TEXT_MUTED }}>• {patientInfo.age || 38}y</span>
            </div>

            {currentStudy && (
              <select
                value={currentStudy.study_id}
                onChange={(e) => handleSelectCase(e.target.value)}
                style={{
                  fontFamily: 'monospace',
                  fontWeight: 700,
                  fontSize: '11px',
                  color: PRIMARY,
                  background: SURFACE_CARD,
                  border: `1px solid ${BORDER_WARM}`,
                  borderRadius: '4px',
                  padding: '4px 8px',
                  cursor: 'pointer',
                }}
              >
                <option value={currentStudy.study_id}>Active: {currentStudy.study_id}</option>
                {recentStudies
                  .filter((s) => s.study_id !== currentStudy.study_id)
                  .map((s) => (
                    <option key={s.study_id} value={s.study_id}>
                      {s.study_id} ({s.radiograph?.original_filename ? s.radiograph.original_filename.slice(0, 16) : 'Scan'})
                    </option>
                  ))}
              </select>
            )}
          </div>
        </div>

        {/* Right Tools */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>

          {currentStudy && (
            <>
              <button
                type="button"
                onClick={handleOpenReportStudio}
                style={{
                  background: PRIMARY,
                  color: '#FFFFFF',
                  border: 'none',
                  padding: '7px 14px',
                  borderRadius: '5px',
                  fontSize: '11.5px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  boxShadow: '0 2px 4px rgba(40, 43, 74, 0.15)',
                  transition: 'background 0.15s ease',
                }}
                onMouseEnter={(e) => (e.currentTarget.style.background = PRIMARY_LIGHT)}
                onMouseLeave={(e) => (e.currentTarget.style.background = PRIMARY)}
              >
                <FileDown size={13} />
                <span>Download 5-Page PDF Report</span>
              </button>

              <button
                type="button"
                onClick={handleReset}
                style={{
                  background: SURFACE_CARD,
                  color: PRIMARY,
                  border: `1px solid ${BORDER_WARM}`,
                  padding: '7px 12px',
                  borderRadius: '5px',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                }}
              >
                <Upload size={12} />
                <span>New Case</span>
              </button>
            </>
          )}
        </div>
      </header>

      {/* ─── Studio Workspace Body ────────────────────────────────────────── */}
      <main style={{ flex: 1, padding: '20px 24px', maxWidth: '1440px', width: '100%', margin: '0 auto', boxSizing: 'border-box', animation: 'sectionEnter 0.4s ease-out both' }}>
        {/* Alerts & Notifications */}
        {successMessage && (
          <div style={{ backgroundColor: '#F0FDF4', border: '1px solid #86EFAC', color: '#15803D', borderRadius: '6px', padding: '8px 14px', marginBottom: '14px', fontSize: '12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <CheckCircle2 size={15} />
              <span>{successMessage}</span>
            </div>
            <button onClick={() => setSuccessMessage(null)} style={{ background: 'transparent', border: 'none', color: '#15803D', cursor: 'pointer' }}>
              <X size={14} />
            </button>
          </div>
        )}

        {errorMessage && (
          <div style={{ backgroundColor: '#FEF2F2', border: '1px solid #FECACA', color: '#991B1B', borderRadius: '6px', padding: '8px 14px', marginBottom: '14px', fontSize: '12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <AlertCircle size={15} />
              <span>{errorMessage}</span>
            </div>
            <button onClick={() => setErrorMessage(null)} style={{ background: 'transparent', border: 'none', color: '#991B1B', cursor: 'pointer' }}>
              <X size={14} />
            </button>
          </div>
        )}

        {/* Processing Spinner Banner */}
        {(loading || analyzing) && (
          <div style={{ backgroundColor: PRIMARY, color: '#FFFFFF', borderRadius: '6px', padding: '10px 18px', marginBottom: '14px', display: 'flex', alignItems: 'center', gap: '12px', fontSize: '12.5px', fontWeight: 500, boxShadow: '0 4px 12px rgba(40, 43, 74, 0.2)' }}>
            <RefreshCw size={16} style={{ animation: 'spin 1s linear infinite' }} />
            <span>
              {analyzing
                ? 'Processing radiograph: Real instance segmentation, deterministic FDI tooth indexing & spatial mapping...'
                : 'Loading clinical study assets...'}
            </span>
          </div>
        )}

        {/* ─── Modality Selection Strip ────────────────────────────────────── */}
        <section
          style={{
            backgroundColor: SURFACE_PANEL,
            border: `1px solid ${BORDER_WARM}`,
            borderRadius: '8px',
            padding: '14px 20px',
            marginBottom: '18px',
            boxShadow: '0 1px 3px rgba(40, 43, 74, 0.04)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Scan size={16} color={PRIMARY} />
            <span style={{ fontSize: '13px', fontWeight: 700, color: PRIMARY }}>Radiograph Modality:</span>
            <span style={{ fontSize: '11px', color: TEXT_MUTED }}>(Confirmed modality guides neural inference routing)</span>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {[
              { id: 'panoramic_opg', label: 'Panoramic OPG (DENTEX)', supported: true },
              { id: 'intraoral_periapical', label: 'Intraoral Periapical (IOPA YOLO11n)', supported: true },
            ].map((m) => {
              const isSelected = selectedModality === m.id;
              return (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => handleUpdateModality(m.id)}
                  style={{
                    padding: '6px 14px',
                    borderRadius: '6px',
                    border: isSelected ? `2px solid ${PRIMARY}` : `1px solid ${BORDER_WARM}`,
                    backgroundColor: isSelected ? PRIMARY : SURFACE_CARD,
                    color: isSelected ? '#FFFFFF' : TEXT_MAIN,
                    fontSize: '11.5px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all 0.15s ease',
                  }}
                >
                  {m.label}
                </button>
              );
            })}
          </div>
        </section>

        {/* ─── Core Examination Studio Split ──────────────────────────────── */}
        {!currentStudy ? (
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '20px', minHeight: '480px' }}>
            {/* Upload Dropzone */}
            <div
              onDrop={onDrop}
              onDragOver={(e) => { e.preventDefault(); setIsDragOver(true); }}
              onDragLeave={() => setIsDragOver(false)}
              onClick={() => fileInputRef.current?.click()}
              style={{
                backgroundColor: isDragOver ? '#F5F3E7' : SURFACE_PANEL,
                border: isDragOver ? `2px dashed ${PRIMARY}` : `2px dashed ${BORDER_STRONG}`,
                borderRadius: '8px',
                padding: '40px 24px',
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                textAlign: 'center',
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".png,.jpg,.jpeg,.dcm,.dicom"
                style={{ display: 'none' }}
                onChange={(e) => {
                  if (e.target.files && e.target.files[0]) {
                    handleFileUpload(e.target.files[0]);
                  }
                }}
              />
              <div
                style={{
                  width: '54px',
                  height: '54px',
                  borderRadius: '50%',
                  backgroundColor: SURFACE_CARD,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  marginBottom: '14px',
                  color: PRIMARY,
                }}
              >
                <Upload size={24} />
              </div>
              <h3 style={{ fontSize: '16px', fontWeight: 700, color: PRIMARY, margin: '0 0 6px 0' }}>
                Ingest Dental Radiograph for Patient {patientInfo.patient_name || 'Record'}
              </h3>
              <p style={{ fontSize: '12px', color: TEXT_MUTED, maxWidth: '380px', lineHeight: 1.5, margin: '0 0 16px 0' }}>
                Drag and drop a panoramic OPG, periapical IOPA, or DICOM raster file to initiate automated anomaly detection and 3D dental mapping.
              </p>
              <button
                type="button"
                style={{ backgroundColor: PRIMARY, color: '#FFFFFF', border: 'none', padding: '9px 20px', borderRadius: '6px', fontSize: '12px', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                <FileText size={13} />
                <span>Browse Radiograph File</span>
              </button>
              <div style={{ marginTop: '16px', fontSize: '11px', color: TEXT_MUTED, display: 'flex', gap: '8px' }}>
                <span>PNG • JPEG • DICOM</span>
                <span>•</span>
                <span>Zero Cloud Egress</span>
              </div>
            </div>

            {/* 3D Reference Architecture Preview */}
            <div
              style={{
                backgroundColor: SURFACE_PANEL,
                border: `1px solid ${BORDER_WARM}`,
                borderRadius: '8px',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '13px', fontWeight: 700, color: PRIMARY }}>3D Anatomical Dental Arch Reference</span>
              </div>
              <div style={{ flex: 1, minHeight: '360px', borderRadius: '6px', overflow: 'hidden' }}>
                <DentalArch3D selectedFdi={selectedFdi} onSelectTooth={setSelectedFdi} findings={[]} height="100%" />
              </div>
            </div>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.35fr) minmax(0, 1fr)', gap: '18px', alignItems: 'stretch' }}>
            {/* Left Column: Canvas Viewer */}
            <div style={{ backgroundColor: SURFACE_PANEL, border: `1px solid ${BORDER_WARM}`, borderRadius: '8px', padding: '14px', display: 'flex', flexDirection: 'column', minHeight: '620px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '13px', fontWeight: 700, color: PRIMARY }}>
                    {((currentStudy.radiograph as any)?.modality === 'intraoral_periapical')
                      ? 'Intraoral Periapical (IOPA)'
                      : ((currentStudy.radiograph as any)?.modality === 'bitewing')
                      ? 'Bitewing Radiograph'
                      : 'Panoramic Radiograph (OPG)'}
                  </span>
                  <span style={{ fontSize: '11px', color: TEXT_MUTED }}>
                    · {currentStudy.radiograph?.width_px || (currentStudy.radiograph as any)?.width || 2872} × {currentStudy.radiograph?.height_px || (currentStudy.radiograph as any)?.height || 1316} px
                  </span>
                </div>
              </div>

              {comparingStudy && (
                <div style={{ backgroundColor: '#FEF3C7', border: '1px solid #F59E0B', borderRadius: '4px', padding: '6px 10px', marginBottom: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11px' }}>
                  <span style={{ color: '#92400E', fontWeight: 600 }}>
                    Comparing current scan ({currentStudy.study_id}) against historical scan ({comparingStudy.study_id})
                  </span>
                  <button onClick={() => setComparingStudy(null)} style={{ background: 'transparent', border: 'none', color: '#92400E', cursor: 'pointer', fontWeight: 700 }}>Close Comparison</button>
                </div>
              )}

              <div style={{ flex: 1, minHeight: '520px', borderRadius: '6px', overflow: 'hidden' }}>
                <RadiographCanvas
                  imageUrl={api.getPreviewUrl(currentStudy.study_id)}
                  findings={findings}
                  selectedFindingId={selectedFindingId}
                  onSelectFinding={(id) => {
                    setSelectedFindingId(id);
                    const f = findings.find((item) => item.finding_id === id);
                    if (f?.tooth_fdi) setSelectedFdi(f.tooth_fdi);
                  }}
                  selectedToothFdi={selectedFdi}
                  height="100%"
                  originalWidth={currentStudy.radiograph?.width_px || (currentStudy.radiograph as any)?.width}
                  originalHeight={currentStudy.radiograph?.height_px || (currentStudy.radiograph as any)?.height}
                  onCreateRegion={handleCreateAnnotation}
                  onDeleteAnnotation={handleDeleteAnnotation}
                />
              </div>
            </div>

            {/* Right Column: 3D Dental Model & Findings Ledger */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              {/* 3D Model Top */}
              <div style={{ backgroundColor: SURFACE_PANEL, border: `1px solid ${BORDER_WARM}`, borderRadius: '8px', padding: '14px', display: 'flex', flexDirection: 'column', minHeight: '340px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Layers size={15} color={PRIMARY} />
                    <span style={{ fontSize: '13px', fontWeight: 700, color: PRIMARY }}>3D Anatomical Spatial Model</span>
                  </div>
                </div>
                <div style={{ flex: 1, minHeight: '270px', borderRadius: '6px', overflow: 'hidden' }}>
                  <DentalArch3D
                    selectedFdi={selectedFdi}
                    onSelectTooth={handleSelectTooth}
                    findings={findings}
                    height="100%"
                    onSelectAnatomicalStructure={handleSelectAnatomicalStructure}
                    activeAnatomicalStructure={activeAnatomicalStructure}
                  />
                </div>
              </div>

              {/* Findings Ledger Bottom */}
              <div style={{ backgroundColor: SURFACE_PANEL, border: `1px solid ${BORDER_WARM}`, borderRadius: '8px', padding: '14px', display: 'flex', flexDirection: 'column', flex: 1, minHeight: '280px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: `1px solid ${BORDER_WARM}`, paddingBottom: '8px', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontSize: '13px', fontWeight: 700, color: PRIMARY }}>
                      AI Detections &amp; Clinician Audit ({findings.length})
                    </span>
                    <span style={{ fontSize: '10px', padding: '1px 6px', borderRadius: '3px', backgroundColor: '#DCFCE7', color: '#15803D', fontWeight: 600 }}>
                      {confirmedCount} Confirmed
                    </span>
                    {dismissedCount > 0 && (
                      <span style={{ fontSize: '10px', padding: '1px 6px', borderRadius: '3px', backgroundColor: '#F1F5F9', color: '#64748B', fontWeight: 600 }}>
                        {dismissedCount} Dismissed
                      </span>
                    )}
                  </div>
                  {findings.length > 0 && (
                    <button
                      onClick={() => handleRunAnalysis()}
                      disabled={analyzing}
                      style={{ background: SURFACE_CARD, border: `1px solid ${BORDER_WARM}`, color: PRIMARY, fontSize: '10.5px', fontWeight: 600, padding: '3px 8px', borderRadius: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
                    >
                      <RefreshCw size={11} />
                      <span>Re-analyze</span>
                    </button>
                  )}
                </div>

                <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '6px', maxHeight: '240px', paddingRight: '4px' }}>
                  {findings.map((f) => {
                    const isSelected = f.finding_id === selectedFindingId;
                    const isToothSelected = selectedFdi && f.tooth_fdi === selectedFdi;
                    const isConfirmed = f.review_status === 'confirmed';
                    const isDismissed = f.review_status === 'rejected';

                    return (
                      <div
                        key={f.finding_id}
                        onClick={() => {
                          setSelectedFindingId(f.finding_id);
                          if (f.tooth_fdi) setSelectedFdi(f.tooth_fdi);
                        }}
                        style={{
                          padding: '8px 10px',
                          borderRadius: '5px',
                          backgroundColor: isConfirmed ? '#F0FDF4' : isDismissed ? '#F8FAFC' : isSelected || isToothSelected ? '#EEF2FF' : SURFACE_CARD,
                          border: isConfirmed ? '1px solid #86EFAC' : isDismissed ? '1px solid #CBD5E1' : isSelected || isToothSelected ? `1px solid ${PRIMARY}` : `1px solid ${BORDER_WARM}`,
                          opacity: isDismissed ? 0.65 : 1.0,
                          cursor: 'pointer',
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'center',
                        }}
                      >
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span style={{ fontFamily: 'monospace', fontWeight: 700, fontSize: '10px', padding: '1px 5px', borderRadius: '3px', backgroundColor: isConfirmed ? '#DCFCE7' : isDismissed ? '#E2E8F0' : YELLOW_CANDIDATE, color: isConfirmed ? '#15803D' : isDismissed ? '#475569' : '#78350F' }}>
                              {f.tooth_fdi ? `FDI #${f.tooth_fdi}` : 'Unassigned'}
                            </span>
                            <span style={{ fontSize: '11.5px', fontWeight: 600, color: PRIMARY, textTransform: 'capitalize' }}>
                              {f.pathology_class.replace(/_/g, ' ')}
                            </span>
                            <span style={{ fontSize: '10.5px', color: TEXT_MUTED }}>
                              ({Math.round((f.confidence || 0) * 100)}% conf)
                            </span>
                          </div>
                          <div style={{ fontSize: '9.5px', color: TEXT_MUTED, marginTop: '2px' }}>
                            {f.finding_id} • Status: {f.review_status || 'AI Candidate'}
                          </div>

                          {fdiEditFindingId === f.finding_id && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginTop: '6px' }} onClick={(e) => e.stopPropagation()}>
                              <span style={{ fontSize: '10px', fontWeight: 600, color: PRIMARY }}>FDI:</span>
                              <input type="number" placeholder="11-48" value={manualFdiInput} onChange={(e) => setManualFdiInput(e.target.value ? parseInt(e.target.value) : '')} style={{ width: '56px', padding: '2px 4px', fontSize: '10.5px', borderRadius: '3px', border: `1px solid ${BORDER_WARM}` }} />
                              <button type="button" onClick={() => manualFdiInput && handleCorrectFdi(f.finding_id, Number(manualFdiInput))} style={{ backgroundColor: PRIMARY, color: '#FFFFFF', border: 'none', padding: '2px 6px', borderRadius: '3px', fontSize: '10px', cursor: 'pointer' }}>Save</button>
                              <button type="button" onClick={() => setFdiEditFindingId(null)} style={{ backgroundColor: 'transparent', border: 'none', color: TEXT_MUTED, fontSize: '10px', cursor: 'pointer' }}>Cancel</button>
                            </div>
                          )}
                        </div>

                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          <button type="button" title="Edit tooth number" onClick={(e) => { e.stopPropagation(); setFdiEditFindingId(f.finding_id); setManualFdiInput(f.tooth_fdi || ''); }} style={{ background: '#FFFFFF', border: `1px solid ${BORDER_WARM}`, borderRadius: '3px', padding: '3px 6px', fontSize: '9.5px', fontWeight: 600, color: PRIMARY, cursor: 'pointer' }}>
                            <Edit3 size={10} />
                          </button>
                          <button type="button" onClick={(e) => { e.stopPropagation(); handleReviewFinding(f.finding_id, 'confirmed'); }} style={{ padding: '3px 8px', borderRadius: '3px', border: 'none', fontSize: '10px', fontWeight: 600, cursor: 'pointer', backgroundColor: isConfirmed ? GREEN_CONFIRMED : '#E2E8F0', color: isConfirmed ? '#FFFFFF' : '#334155', display: 'flex', alignItems: 'center', gap: '2px' }}>
                            <Check size={11} />
                            <span>{isConfirmed ? 'Confirmed' : 'Confirm'}</span>
                          </button>
                          <button type="button" onClick={(e) => { e.stopPropagation(); handleReviewFinding(f.finding_id, 'rejected'); }} style={{ padding: '3px 8px', borderRadius: '3px', border: 'none', fontSize: '10px', fontWeight: 600, cursor: 'pointer', backgroundColor: isDismissed ? GREY_DISMISSED : '#F1F5F9', color: isDismissed ? '#FFFFFF' : '#64748B', display: 'flex', alignItems: 'center', gap: '2px' }}>
                            <X size={11} />
                            <span>{isDismissed ? 'Dismissed' : 'Dismiss'}</span>
                          </button>
                        </div>
                      </div>
                    );
                  })}

                  {findings.length === 0 && (
                    <div style={{ padding: '24px 16px', textAlign: 'center', color: TEXT_MUTED, fontSize: '12px', backgroundColor: SURFACE_CARD, borderRadius: '6px', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                      <div>
                        {currentStudy.status === 'analyzed'
                          ? 'Analysis completed: No abnormalities detected under current threshold.'
                          : (currentStudy.radiograph as any)?.modality === 'unknown'
                          ? 'Modality unconfirmed. Please select modality above to initiate automated screening.'
                          : 'Analysis not performed. Click below to execute local neural screening.'}
                      </div>
                      {currentStudy.status !== 'analyzed' && (
                        <button type="button" onClick={() => handleRunAnalysis()} disabled={analyzing} style={{ backgroundColor: PRIMARY, color: '#FFFFFF', border: 'none', padding: '7px 16px', borderRadius: '5px', fontSize: '11.5px', fontWeight: 600, cursor: 'pointer' }}>
                          {analyzing ? 'Analyzing...' : 'Run Neural AI Screener'}
                        </button>
                      )}
                    </div>
                  )}
                </div>

                <div style={{ fontSize: '9.5px', color: TEXT_MUTED, marginTop: '8px', borderTop: `1px solid ${BORDER_WARM}`, paddingTop: '4px', display: 'flex', justifyContent: 'space-between' }}>
                  <span>Dismissed findings excluded from insurance claims.</span>
                  <span>Tooth assignment solver audited at 95.89% quadrant accuracy.</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* ─── 4. SIMPLE, PROFESSIONAL 5-PAGE PDF REPORT STUDIO MODAL ────────── */}
      {showReportModal && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(27, 30, 54, 0.65)', backdropFilter: 'blur(4px)', zIndex: 350, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px' }}>
          <div style={{ backgroundColor: '#FFFFFF', borderRadius: '8px', width: '100%', maxWidth: '820px', maxHeight: '90vh', display: 'flex', flexDirection: 'column', boxShadow: '0 25px 50px -12px rgba(40, 43, 74, 0.35)', overflow: 'hidden', border: `1px solid ${BORDER_WARM}` }}>
            {/* Modal Header */}
            <div style={{ padding: '14px 20px', borderBottom: `1px solid ${BORDER_WARM}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: SURFACE_CARD }}>
              <div>
                <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 700, color: PRIMARY }}>Clinical Pre-Authorization 5-Page PDF Claim Studio</h3>
                <span style={{ fontSize: '11px', color: TEXT_MUTED }}>Case: {currentStudy?.study_id} • Patient: {patientInfo.patient_name} ({patientInfo.patient_id})</span>
              </div>
              <button onClick={() => setShowReportModal(false)} style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: TEXT_MUTED }}><X size={18} /></button>
            </div>

            {/* Modal Body */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{ backgroundColor: SURFACE_CARD, border: `1px solid ${BORDER_WARM}`, borderRadius: '6px', padding: '10px 14px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '11.5px' }}>
                <div>
                  <strong style={{ color: PRIMARY }}>Clean 5-Page Specification: </strong>
                  <span style={{ color: TEXT_MUTED }}>Page 1: Demographics • Page 2: Original Radiograph • Page 3: Tooth Findings • Page 4: 3D Reference • Page 5: Pre-Auth &amp; Signature</span>
                </div>
                <div style={{ fontSize: '10.5px', color: '#15803D', fontWeight: 600 }}>ReportLab 100% Localhost</div>
              </div>

              {/* 3D Reference Model Snapshot */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <label style={{ fontSize: '11.5px', fontWeight: 700, color: PRIMARY }}>Page 4: 3D Anatomical Spatial Model Snapshot</label>
                </div>
                {snapshotPreviewUrl ? (
                  <div style={{ height: '140px', backgroundColor: '#0A0D0C', borderRadius: '6px', border: `1px solid ${BORDER_WARM}`, display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden' }}>
                    <img src={snapshotPreviewUrl} alt="3D Canvas Snapshot" style={{ maxHeight: '100%', maxWidth: '100%', objectFit: 'contain' }} />
                  </div>
                ) : (
                  <div style={{ padding: '20px', backgroundColor: SURFACE_CARD, borderRadius: '6px', border: `1px dashed ${BORDER_WARM}`, textAlign: 'center', fontSize: '11px', color: TEXT_MUTED }}>
                    Standard dental arch spatial reference snapshot will be automatically compiled.
                  </div>
                )}
              </div>

              {/* Narrative Editor */}
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                  <label style={{ fontSize: '11.5px', fontWeight: 700, color: PRIMARY }}>Page 5: Clinical Justification Narrative (Dentist Editable)</label>
                  {isGeneratingNarrative && (
                    <span style={{ fontSize: '10.5px', color: PRIMARY_LIGHT, display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <RefreshCw size={11} style={{ animation: 'spin 1s linear infinite' }} /> Synthesizing with local LLM...
                    </span>
                  )}
                </div>
                <textarea
                  value={reportNarrative}
                  onChange={(e) => setReportNarrative(e.target.value)}
                  rows={6}
                  style={{ width: '100%', padding: '8px 10px', fontSize: '11.5px', fontFamily: 'monospace', borderRadius: '4px', border: `1px solid ${BORDER_WARM}`, boxSizing: 'border-box', lineHeight: 1.45 }}
                />
              </div>

              {/* Candidate CDT Codes */}
              <div style={{ backgroundColor: SURFACE_CARD, border: `1px solid ${BORDER_WARM}`, borderRadius: '6px', padding: '10px 12px' }}>
                <div style={{ fontSize: '11px', fontWeight: 700, color: PRIMARY, marginBottom: '4px' }}>Candidate CDT Procedure Codes</div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', fontSize: '10.5px' }}>
                  <div style={{ padding: '6px', backgroundColor: '#FFFFFF', border: `1px solid ${BORDER_WARM}`, borderRadius: '4px' }}>
                    <strong style={{ color: PRIMARY }}>D2391</strong>
                    <div style={{ fontSize: '9.5px', color: TEXT_MUTED }}>Resin composite — 1 surface posterior</div>
                  </div>
                  <div style={{ padding: '6px', backgroundColor: '#FFFFFF', border: `1px solid ${BORDER_WARM}`, borderRadius: '4px' }}>
                    <strong style={{ color: PRIMARY }}>D3330</strong>
                    <div style={{ fontSize: '9.5px', color: TEXT_MUTED }}>Endodontic therapy, molar</div>
                  </div>
                  <div style={{ padding: '6px', backgroundColor: '#FFFFFF', border: `1px solid ${BORDER_WARM}`, borderRadius: '4px' }}>
                    <strong style={{ color: PRIMARY }}>D7210</strong>
                    <div style={{ fontSize: '9.5px', color: TEXT_MUTED }}>Surgical removal of impacted tooth</div>
                  </div>
                </div>
              </div>

              {/* Attestation */}
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                <input type="checkbox" id="dentist-attest" checked={dentistAttested} onChange={(e) => setDentistAttested(e.target.checked)} style={{ marginTop: '2px', cursor: 'pointer' }} />
                <label htmlFor="dentist-attest" style={{ fontSize: '11px', color: PRIMARY, cursor: 'pointer', lineHeight: 1.4 }}>
                  <strong>Licensed Practitioner Attestation:</strong> I attest under professional dental license that I have personally evaluated the diagnostic radiographs, verified indicated tooth designations, and confirmed clinical necessity of proposed restorative procedures.
                </label>
              </div>
            </div>

            {/* Modal Footer */}
            <div style={{ padding: '12px 20px', borderTop: `1px solid ${BORDER_WARM}`, display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: SURFACE_CARD }}>
              <span style={{ fontSize: '10.5px', color: TEXT_MUTED }}>Compiles clean 5-page PDF using original high-resolution storage radiograph.</span>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button type="button" onClick={() => setShowReportModal(false)} style={{ padding: '6px 14px', borderRadius: '4px', border: `1px solid ${BORDER_WARM}`, backgroundColor: '#FFFFFF', fontSize: '11px', fontWeight: 600, color: PRIMARY, cursor: 'pointer' }}>Cancel</button>
                <button type="button" onClick={handleDownloadReport} disabled={isExportingPdf || !dentistAttested} style={{ padding: '7px 18px', borderRadius: '4px', border: 'none', backgroundColor: isExportingPdf || !dentistAttested ? '#94A3B8' : PRIMARY, fontSize: '11.5px', fontWeight: 600, color: '#FFFFFF', cursor: isExportingPdf || !dentistAttested ? 'not-allowed' : 'pointer', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  {isExportingPdf ? (
                    <><RefreshCw size={12} style={{ animation: 'spin 1s linear infinite' }} /><span>Generating 5-Page PDF...</span></>
                  ) : (
                    <><Download size={13} /><span>Download 5-Page Report PDF</span></>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ─── Reusable Form Field Component ─────────────────────────────────────────
const FormField: React.FC<{
  label: string;
  required?: boolean;
  error?: string;
  children: React.ReactNode;
}> = ({ label, required, error, children }) => (
  <div>
    <label style={{ fontSize: '13px', fontWeight: 600, color: '#282b4a', display: 'block', marginBottom: '6px' }}>
      {label} {required && <span style={{ color: '#DC2626' }}>*</span>}
    </label>
    {children}
    {error && (
      <span style={{ fontSize: '11px', color: '#DC2626', display: 'block', marginTop: '4px' }}>{error}</span>
    )}
  </div>
);

// ─── Reusable Input Style ──────────────────────────────────────────────────
const inputStyle = (hasError: boolean): React.CSSProperties => ({
  width: '100%',
  padding: '10px 14px',
  fontSize: '13.5px',
  borderRadius: '8px',
  border: hasError ? '1.5px solid #DC2626' : '1.5px solid #ded8c4',
  backgroundColor: '#FFFFFF',
  boxSizing: 'border-box',
  transition: 'border-color 0.15s ease',
  outline: 'none',
  color: '#282b4a',
});
