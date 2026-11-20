import { useEffect, useRef } from 'react';
import { useSaveDraft } from '../api/hooks';
import { useVerificationStore } from '../store/verificationStore';

const SYNC_DELAY_MS = 2000;

interface PendingDraft {
  surveyId: number;
  values: Record<string, unknown>;
  key: string;
}

/**
 * Mirrors the local draft of the current survey to the backend.
 *
 * Changes are debounced: a request is sent once the values stop changing for
 * SYNC_DELAY_MS. A pending draft is flushed when the user switches to another
 * survey or leaves the verification view.
 */
export function useDraftSync(surveyId: number | null) {
  const { mutate: saveDraft } = useSaveDraft();
  const pendingRef = useRef<PendingDraft | null>(null);
  const lastSyncedRef = useRef<string>('');

  const draftValues = useVerificationStore((s) =>
    surveyId !== null ? s.surveysUI[surveyId]?.draftValues : undefined
  );

  useEffect(() => {
    if (surveyId === null || !draftValues || Object.keys(draftValues).length === 0) return;

    const key = `${surveyId}:${JSON.stringify(draftValues)}`;
    if (key === lastSyncedRef.current) return;

    pendingRef.current = { surveyId, values: draftValues, key };
    const timer = setTimeout(() => {
      pendingRef.current = null;
      lastSyncedRef.current = key;
      saveDraft({ surveyId, values: draftValues });
    }, SYNC_DELAY_MS);

    return () => clearTimeout(timer);
  }, [surveyId, draftValues, saveDraft]);

  useEffect(() => {
    const pending = pendingRef;
    const lastSynced = lastSyncedRef;
    return () => {
      const draft = pending.current;
      if (draft && draft.surveyId === surveyId) {
        pending.current = null;
        lastSynced.current = draft.key;
        saveDraft({ surveyId: draft.surveyId, values: draft.values });
      }
    };
  }, [surveyId, saveDraft]);
}
