import { create } from 'zustand';

const STORAGE_KEY = 'ankieter:verification:v1';
const DRAFTS_KEY = 'ankieter:drafts:v1';
const TOTAL_PAGES = 5;

interface SurveyUIState {
  selectedPage: number;
  showErrors: boolean;
  draftValues: Record<string, unknown>;
  lastSaved: number;
}

interface VerificationStore {
  surveysUI: Record<number, SurveyUIState>;
  draftTimers: Record<number, ReturnType<typeof setTimeout>>;
  getSurveyUI: (surveyId: number) => SurveyUIState;
  setSelectedPage: (surveyId: number, page: number) => void;
  setShowErrors: (surveyId: number, show: boolean) => void;
  updateDraft: (surveyId: number, values: Record<string, unknown>) => void;
  mergeServerDraft: (surveyId: number, values: Record<string, unknown>) => void;
  saveDraft: (surveyId: number) => void;
  clearDraft: (surveyId: number) => void;
  initSurvey: (surveyId: number) => void;
  hydrate: () => void;
  clearAllCache: () => void;
  hydrateDrafts: () => void;
}

function defaultUIState(): SurveyUIState {
  return { selectedPage: 0, showErrors: false, draftValues: {}, lastSaved: 0 };
}

function readDraftsFromStorage(): Record<string, Record<string, unknown>> {
  try {
    const raw = localStorage.getItem(DRAFTS_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function writeDraftsToStorage(drafts: Record<string, Record<string, unknown>>) {
  localStorage.setItem(DRAFTS_KEY, JSON.stringify(drafts));
}

export const useVerificationStore = create<VerificationStore>((set, get) => ({
  surveysUI: {},
  draftTimers: {},

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

  // Fills in fields saved on the server (e.g. from another browser) that are
  // missing locally. Local edits win because they are never older than the
  // last server sync from this browser.
  mergeServerDraft: (surveyId: number, values: Record<string, unknown>) => {
    const current = get().surveysUI[surveyId] ?? defaultUIState();
    const missing = Object.keys(values).filter((key) => !(key in current.draftValues));
    if (missing.length === 0) return;
    set((s) => ({
      surveysUI: {
        ...s.surveysUI,
        [surveyId]: {
          ...current,
          draftValues: { ...values, ...current.draftValues },
        },
      },
    }));
  },

  saveDraft: (surveyId: number) => {
    const existing = get().draftTimers[surveyId];
    if (existing) clearTimeout(existing);

    const timer = setTimeout(() => {
      const state = get().surveysUI[surveyId];
      if (!state) return;
      const drafts = readDraftsFromStorage();
      drafts[String(surveyId)] = { ...state.draftValues };
      writeDraftsToStorage(drafts);
      set((s) => ({
        surveysUI: {
          ...s.surveysUI,
          [surveyId]: {
            ...(s.surveysUI[surveyId] ?? defaultUIState()),
            lastSaved: Date.now(),
          },
        },
      }));
    }, 500);

    set((s) => ({
      draftTimers: { ...s.draftTimers, [surveyId]: timer },
    }));
  },

  clearDraft: (surveyId: number) => {
    const existing = get().draftTimers[surveyId];
    if (existing) clearTimeout(existing);
    const drafts = readDraftsFromStorage();
    delete drafts[String(surveyId)];
    writeDraftsToStorage(drafts);
    set((s) => {
      const current = s.surveysUI[surveyId];
      if (!current) return s;
      return {
        surveysUI: {
          ...s.surveysUI,
          [surveyId]: { ...current, draftValues: {}, lastSaved: 0 },
        },
        draftTimers: { ...s.draftTimers, [surveyId]: undefined as unknown as ReturnType<typeof setTimeout> },
      };
    });
  },

  initSurvey: (surveyId: number) => {
    const existing = get().surveysUI[surveyId];
    if (existing) return;
    const raw = localStorage.getItem(STORAGE_KEY);
    const stored: Record<string, number> = raw ? JSON.parse(raw) : {};
    const selectedPage = stored[String(surveyId)] ?? 0;
    const drafts = readDraftsFromStorage();
    const draftValues = drafts[String(surveyId)] ?? {};
    set((s) => ({
      surveysUI: {
        ...s.surveysUI,
        [surveyId]: { selectedPage, showErrors: false, draftValues, lastSaved: 0 },
      },
    }));
  },

  hydrate: () => {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const stored: Record<string, number> = JSON.parse(raw);
    const surveysUI: Record<number, SurveyUIState> = {};
    const drafts = readDraftsFromStorage();
    for (const [key, page] of Object.entries(stored)) {
      const draftValues = drafts[key] ?? {};
      surveysUI[Number(key)] = { selectedPage: page, showErrors: false, draftValues, lastSaved: 0 };
    }
    set({ surveysUI });
  },

  clearAllCache: () => {
    localStorage.removeItem(STORAGE_KEY);
    localStorage.removeItem(DRAFTS_KEY);
    set({ surveysUI: {}, draftTimers: {} });
  },

  hydrateDrafts: () => {
    const drafts = readDraftsFromStorage();
    const surveysUI = { ...get().surveysUI };
    for (const [key, values] of Object.entries(drafts)) {
      const surveyId = Number(key);
      const existing = surveysUI[surveyId] ?? defaultUIState();
      surveysUI[surveyId] = { ...existing, draftValues: { ...values } };
    }
    set({ surveysUI });
  },
}));
