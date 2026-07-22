import { create } from 'zustand';

const STORAGE_KEY = 'ankieter:verification:v1';
const TOTAL_PAGES = 5;

interface SurveyUIState {
  selectedPage: number;
  showErrors: boolean;
  draftValues: Record<string, unknown>;
}

interface VerificationStore {
  surveysUI: Record<number, SurveyUIState>;
  getSurveyUI: (surveyId: number) => SurveyUIState;
  setSelectedPage: (surveyId: number, page: number) => void;
  setShowErrors: (surveyId: number, show: boolean) => void;
  updateDraft: (surveyId: number, values: Record<string, unknown>) => void;
  initSurvey: (surveyId: number) => void;
  hydrate: () => void;
}

function defaultUIState(): SurveyUIState {
  return { selectedPage: 0, showErrors: false, draftValues: {} };
}

export const useVerificationStore = create<VerificationStore>((set, get) => ({
  surveysUI: {},

  getSurveyUI: (surveyId: number): SurveyUIState => {
    const state = get().surveysUI[surveyId];
    if (!state) {
      const fresh = defaultUIState();
      set((s) => ({ surveysUI: { ...s.surveysUI, [surveyId]: fresh } }));
      return fresh;
    }
    return state;
  },

  setSelectedPage: (surveyId: number, page: number) => {
    const clamped = Math.max(0, Math.min(TOTAL_PAGES - 1, page));
    set((s) => ({
      surveysUI: {
        ...s.surveysUI,
        [surveyId]: {
          ...(s.surveysUI[surveyId] ?? defaultUIState()),
          selectedPage: clamped,
        },
      },
    }));
    const raw = localStorage.getItem(STORAGE_KEY);
    const stored: Record<string, number> = raw ? JSON.parse(raw) : {};
    stored[String(surveyId)] = clamped;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
  },

  setShowErrors: (surveyId: number, show: boolean) => {
    set((s) => ({
      surveysUI: {
        ...s.surveysUI,
        [surveyId]: {
          ...(s.surveysUI[surveyId] ?? defaultUIState()),
          showErrors: show,
        },
      },
    }));
  },

  updateDraft: (surveyId: number, values: Record<string, unknown>) => {
    set((s) => {
      const current = s.surveysUI[surveyId] ?? defaultUIState();
      return {
        surveysUI: {
          ...s.surveysUI,
          [surveyId]: {
            ...current,
            draftValues: { ...current.draftValues, ...values },
          },
        },
      };
    });
  },

  initSurvey: (surveyId: number) => {
    const existing = get().surveysUI[surveyId];
    if (existing) return;
    const raw = localStorage.getItem(STORAGE_KEY);
    const stored: Record<string, number> = raw ? JSON.parse(raw) : {};
    const selectedPage = stored[String(surveyId)] ?? 0;
    set((s) => ({
      surveysUI: {
        ...s.surveysUI,
        [surveyId]: { selectedPage, showErrors: false, draftValues: {} },
      },
    }));
  },

  hydrate: () => {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const stored: Record<string, number> = JSON.parse(raw);
    const surveysUI: Record<number, SurveyUIState> = {};
    for (const [key, page] of Object.entries(stored)) {
      surveysUI[Number(key)] = { selectedPage: page, showErrors: false, draftValues: {} };
    }
    set({ surveysUI });
  },
}));
