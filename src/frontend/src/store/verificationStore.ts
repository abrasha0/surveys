import { create } from 'zustand';
import { SURVEY_PAGE_COUNT } from '../constants';

const PAGES_KEY = 'ankieter:verification:v1';
const DRAFTS_KEY = 'ankieter:drafts:v1';
const PERSIST_DELAY_MS = 500;

type DraftValues = Record<string, unknown>;

export interface SurveyUIState {
  selectedPage: number;
  showErrors: boolean;
  draftValues: DraftValues;
}

interface VerificationStore {
  surveysUI: Record<number, SurveyUIState>;
  setSelectedPage: (surveyId: number, page: number) => void;
  setShowErrors: (surveyId: number, show: boolean) => void;
  updateDraft: (surveyId: number, values: DraftValues) => void;
  mergeServerDraft: (surveyId: number, values: DraftValues) => void;
  persistDraft: (surveyId: number) => void;
  initSurvey: (surveyId: number) => void;
  hydrate: () => void;
  clearAllCache: () => void;
}

export const DEFAULT_SURVEY_UI: SurveyUIState = Object.freeze({
  selectedPage: 0,
  showErrors: false,
  draftValues: Object.freeze({}) as DraftValues,
});

const persistTimers = new Map<number, ReturnType<typeof setTimeout>>();

function readStorage<T>(key: string): Record<string, T> {
  try {
    const raw = localStorage.getItem(key);
    const parsed: unknown = raw ? JSON.parse(raw) : {};
    return parsed && typeof parsed === 'object' ? (parsed as Record<string, T>) : {};
  } catch {
    return {};
  }
}

function writeStorage(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Storage full or unavailable: the in-memory state still works.
  }
}

export const useVerificationStore = create<VerificationStore>((set, get) => {
  const patchSurvey = (surveyId: number, patch: Partial<SurveyUIState>) =>
    set((s) => ({
      surveysUI: {
        ...s.surveysUI,
        [surveyId]: { ...(s.surveysUI[surveyId] ?? DEFAULT_SURVEY_UI), ...patch },
      },
    }));

  return {
    surveysUI: {},

    setSelectedPage: (surveyId, page) => {
      const clamped = Math.max(0, Math.min(SURVEY_PAGE_COUNT - 1, page));
      patchSurvey(surveyId, { selectedPage: clamped });
      const pages = readStorage<number>(PAGES_KEY);
      pages[String(surveyId)] = clamped;
      writeStorage(PAGES_KEY, pages);
    },

    setShowErrors: (surveyId, show) => patchSurvey(surveyId, { showErrors: show }),

    updateDraft: (surveyId, values) => {
      const current = get().surveysUI[surveyId] ?? DEFAULT_SURVEY_UI;
      patchSurvey(surveyId, { draftValues: { ...current.draftValues, ...values } });
    },

    // Fills in fields saved on the server (e.g. from another browser) that are
    // missing locally. Local edits win because they are never older than the
    // last server sync from this browser.
    mergeServerDraft: (surveyId, values) => {
      const current = get().surveysUI[surveyId] ?? DEFAULT_SURVEY_UI;
      const hasMissing = Object.keys(values).some((key) => !(key in current.draftValues));
      if (!hasMissing) return;
      patchSurvey(surveyId, { draftValues: { ...values, ...current.draftValues } });
    },

    // Writes the draft to localStorage, debounced per survey.
    persistDraft: (surveyId) => {
      clearTimeout(persistTimers.get(surveyId));
      persistTimers.set(
        surveyId,
        setTimeout(() => {
          persistTimers.delete(surveyId);
          const state = get().surveysUI[surveyId];
          if (!state) return;
          const drafts = readStorage<DraftValues>(DRAFTS_KEY);
          drafts[String(surveyId)] = state.draftValues;
          writeStorage(DRAFTS_KEY, drafts);
        }, PERSIST_DELAY_MS)
      );
    },

    initSurvey: (surveyId) => {
      if (get().surveysUI[surveyId]) return;
      const key = String(surveyId);
      patchSurvey(surveyId, {
        selectedPage: readStorage<number>(PAGES_KEY)[key] ?? 0,
        draftValues: readStorage<DraftValues>(DRAFTS_KEY)[key] ?? {},
      });
    },

    hydrate: () => {
      const pages = readStorage<number>(PAGES_KEY);
      const drafts = readStorage<DraftValues>(DRAFTS_KEY);
      const surveysUI: Record<number, SurveyUIState> = {};
      for (const key of new Set([...Object.keys(pages), ...Object.keys(drafts)])) {
        surveysUI[Number(key)] = {
          selectedPage: pages[key] ?? 0,
          showErrors: false,
          draftValues: drafts[key] ?? {},
        };
      }
      set({ surveysUI });
    },

    clearAllCache: () => {
      persistTimers.forEach((timer) => clearTimeout(timer));
      persistTimers.clear();
      try {
        localStorage.removeItem(PAGES_KEY);
        localStorage.removeItem(DRAFTS_KEY);
      } catch {
        // Storage unavailable: nothing to clear.
      }
      set({ surveysUI: {} });
    },
  };
});
