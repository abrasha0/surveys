import { useEffect, useRef } from 'react';
import { useSaveDraft } from '../api/hooks';
import { useVerificationStore } from '../store/verificationStore';

const SYNC_INTERVAL = 30000;

export function useDraftSync(surveyId: number | null) {
  const saveDraftMutation = useSaveDraft();
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastValuesRef = useRef<string>('');

  const draftValues = useVerificationStore((s) =>
    surveyId !== null ? s.surveysUI[surveyId]?.draftValues : undefined
  );

  useEffect(() => {
    if (surveyId === null || !draftValues) return;

    const valuesJson = JSON.stringify(draftValues);
    if (valuesJson === lastValuesRef.current) return;
    lastValuesRef.current = valuesJson;

    if (timerRef.current) {
      clearInterval(timerRef.current);
    }

    timerRef.current = setInterval(() => {
      saveDraftMutation.mutate({ surveyId, values: draftValues });
    }, SYNC_INTERVAL);

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
      if (Object.keys(draftValues).length > 0) {
        saveDraftMutation.mutate({ surveyId, values: draftValues });
      }
    };
  }, [surveyId, draftValues, saveDraftMutation]);
}