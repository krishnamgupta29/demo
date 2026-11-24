import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { StudyItem, StudyDetail } from '../api/types';
import { api } from '../api/client';

interface StudyContextType {
  currentStudyId: string | null;
  currentStudy: StudyDetail | null;
  studies: StudyItem[];
  loading: boolean;
  error: string | null;
  selectedToothFdi: number | null;
  highlightedFindingId: string | null;
  refreshStudies: () => Promise<void>;
  selectStudy: (studyId: string) => Promise<void>;
  selectTooth: (fdi: number | null) => void;
  setHighlightedFindingId: (findingId: string | null) => void;
  reloadCurrentStudy: () => Promise<void>;
}

const StudyContext = createContext<StudyContextType | undefined>(undefined);

export const StudyProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [studies, setStudies] = useState<StudyItem[]>([]);
  const [currentStudyId, setCurrentStudyId] = useState<string | null>(null);
  const [currentStudy, setCurrentStudy] = useState<StudyDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedToothFdi, setSelectedToothFdi] = useState<number | null>(16);
  const [highlightedFindingId, setHighlightedFindingId] = useState<string | null>(null);

  const refreshStudies = useCallback(async () => {
    try {
      const res = await api.listStudies(50, 0);
      const list = res.items || res.studies || [];
      setStudies(list);
      // If no study currently selected and we have studies, select the first
      if (!currentStudyId && list.length > 0) {
        setCurrentStudyId(list[0].study_id);
      }
    } catch (err: any) {
      console.error('Failed to load studies:', err);
      setError(err.message || 'Failed to load studies');
    }
  }, [currentStudyId]);

  const selectStudy = useCallback(async (studyId: string) => {
    setCurrentStudyId(studyId);
    setLoading(true);
    setError(null);
    try {
      const detail = await api.getStudy(studyId);
      setCurrentStudy(detail);
    } catch (err: any) {
      console.error(`Failed to load study ${studyId}:`, err);
      setError(err.message || `Failed to load study ${studyId}`);
    } finally {
      setLoading(false);
    }
  }, []);

  const reloadCurrentStudy = useCallback(async () => {
    if (currentStudyId) {
      await selectStudy(currentStudyId);
    }
  }, [currentStudyId, selectStudy]);

  useEffect(() => {
    refreshStudies();
  }, []);

  useEffect(() => {
    if (currentStudyId) {
      selectStudy(currentStudyId);
    }
  }, [currentStudyId, selectStudy]);

  return (
    <StudyContext.Provider
      value={{
        currentStudyId,
        currentStudy,
        studies,
        loading,
        error,
        selectedToothFdi,
        highlightedFindingId,
        refreshStudies,
        selectStudy,
        selectTooth: setSelectedToothFdi,
        setHighlightedFindingId,
        reloadCurrentStudy,
      }}
    >
      {children}
    </StudyContext.Provider>
  );
};

export const useStudy = () => {
  const context = useContext(StudyContext);
  if (!context) {
    throw new Error('useStudy must be used within a StudyProvider');
  }
  return context;
};

