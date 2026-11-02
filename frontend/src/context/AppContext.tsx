import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  Language,
  OverviewMeasures,
  ActiveFilters,
  ReferenceProvince,
} from '../types';
import {
  getSessionStatus,
  getOverview,
  getActiveFilters,
  updateActiveFilters as apiUpdateFilters,
  purgeSession as apiPurgeSession,
  generateSyntheticData,
} from '../services/api';

const DEFAULT_FILTERS: ActiveFilters = {
  scope_mode: 'all_imported',
  province_code: null,
  province_codes: [],
  district_code: null,
  year: null,
  sex: null,
  nationality: null,
  patient_type: null,
  address_type: 'residence',
  comparator_province_code: null,
  lang: 'th',
};

interface AppContextType {
  lang: Language;
  setLang: (lang: Language) => void;
  figLang: Language;
  setFigLang: (lang: Language) => void;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  isLoaded: boolean;
  isSynthetic: boolean;
  measures: OverviewMeasures | null;
  filters: ActiveFilters;
  filterOptions: any;
  referenceProvinces: ReferenceProvince[];
  filterVersion: number;
  updateFilters: (partial: Partial<ActiveFilters>) => Promise<void>;
  resetFilters: () => Promise<void>;
  loading: boolean;
  isBackendWaking: boolean;
  error: string | null;
  refreshData: () => Promise<void>;
  purgeSession: () => Promise<void>;
  loadSynthetic: () => Promise<void>;
}

const AppContext = createContext<AppContextType | undefined>(undefined);

export const AppProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [lang, setLangState] = useState<Language>('th');
  const [figLang, setFigLangState] = useState<Language>('th');
  const [activeTab, setActiveTab] = useState<string>('import');
  const [isLoaded, setIsLoaded] = useState<boolean>(false);
  const [isSynthetic, setIsSynthetic] = useState<boolean>(false);
  const [measures, setMeasures] = useState<OverviewMeasures | null>(null);
  const [filters, setFilters] = useState<ActiveFilters>(DEFAULT_FILTERS);
  const [filterOptions, setFilterOptions] = useState<any>(null);
  const [referenceProvinces, setReferenceProvinces] = useState<ReferenceProvince[]>([]);
  const [filterVersion, setFilterVersion] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(false);
  const [isBackendWaking, setIsBackendWaking] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const setLang = (newLang: Language) => {
    setLangState(newLang);
    setFigLangState(newLang);
    if (isLoaded) {
      apiUpdateFilters({ lang: newLang }).catch(console.error);
    }
  };

  const setFigLang = (newFigLang: Language) => {
    setFigLangState(newFigLang);
    setFilters((prev) => ({ ...prev, lang: newFigLang }));
    if (isLoaded) {
      apiUpdateFilters({ lang: newFigLang }).catch(console.error);
    }
  };

  const refreshData = async () => {
    try {
      setLoading(true);
      setError(null);
      const status = await getSessionStatus();
      setIsBackendWaking(false);
      if (status.loaded) {
        setIsLoaded(true);
        setIsSynthetic(status.is_synthetic);
        const [overview, fltRes] = await Promise.all([
          getOverview(),
          getActiveFilters(),
        ]);
        setMeasures(overview);
        if (fltRes?.filters) {
          setFilters({
            ...DEFAULT_FILTERS,
            ...fltRes.filters,
            province_codes: fltRes.filters.province_codes || [],
          });
          if (fltRes.filters.lang) {
            setFigLangState(fltRes.filters.lang);
          }
        }
        if (fltRes?.options) {
          setFilterOptions(fltRes.options);
        }
        if (fltRes?.reference_provinces) {
          setReferenceProvinces(fltRes.reference_provinces);
        }
        setFilterVersion((v) => v + 1);
      } else {
        setIsLoaded(false);
        setIsSynthetic(false);
        setMeasures(null);
        setFilters(DEFAULT_FILTERS);
      }
    } catch (err: any) {
      console.warn('Backend waking up or network delay, auto-retrying...', err);
      setIsBackendWaking(true);
      setError(err.message || 'Connecting to backend...');
      setTimeout(() => {
        refreshData();
      }, 4000);
    } finally {
      setLoading(false);
    }
  };

  const updateFilters = async (partial: Partial<ActiveFilters>) => {
    if (!isLoaded) return;
    try {
      setLoading(true);
      const res = await apiUpdateFilters(partial);
      if (res?.filters) {
        setFilters({
          ...DEFAULT_FILTERS,
          ...res.filters,
          province_codes: res.filters.province_codes || [],
        });
        if (res.filters.lang) {
          setFigLangState(res.filters.lang);
        }
      }
      if (res?.options) {
        setFilterOptions(res.options);
      }
      const overview = await getOverview();
      setMeasures(overview);
      setFilterVersion((v) => v + 1);
    } catch (err: any) {
      setError(err.message || 'Failed to update filters');
    } finally {
      setLoading(false);
    }
  };

  const resetFilters = async () => {
    await updateFilters({
      scope_mode: 'all_imported',
      province_code: null,
      province_codes: [],
      district_code: null,
      year: null,
      sex: null,
      nationality: null,
      patient_type: null,
      address_type: 'residence',
      comparator_province_code: null,
      lang: figLang,
    });
  };

  const handlePurge = async () => {
    try {
      setLoading(true);
      await apiPurgeSession();
      setIsLoaded(false);
      setIsSynthetic(false);
      setMeasures(null);
      setFilters(DEFAULT_FILTERS);
      setActiveTab('import');
    } catch (err: any) {
      setError(err.message || 'Failed to purge session');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadSynthetic = async () => {
    try {
      setLoading(true);
      setError(null);
      await generateSyntheticData();
      await refreshData();
      setActiveTab('overview');
    } catch (err: any) {
      setError(err.message || 'Failed to generate synthetic data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshData().then(() => {
      // Initial load completed
    });
  }, []);

  return (
    <AppContext.Provider
      value={{
        lang,
        setLang,
        figLang,
        setFigLang,
        activeTab,
        setActiveTab,
        isLoaded,
        isSynthetic,
        measures,
        filters,
        filterOptions,
        referenceProvinces,
        filterVersion,
        updateFilters,
        resetFilters,
        loading,
        isBackendWaking,
        error,
        refreshData,
        purgeSession: handlePurge,
        loadSynthetic: handleLoadSynthetic,
      }}
    >
      {children}
    </AppContext.Provider>
  );
};

export const useApp = () => {
  const context = useContext(AppContext);
  if (!context) throw new Error('useApp must be used within an AppProvider');
  return context;
};
