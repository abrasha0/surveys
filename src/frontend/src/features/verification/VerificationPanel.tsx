import { useEffect, useMemo, useRef, useState } from 'react';
import { useSurveys, useFieldSpecs, useSurveyResult, useSaveSurvey, useSurveyImages, useUnverifySurvey } from '../../api/hooks';
import { useVerificationStore } from '../../store/verificationStore';
import { useDraftSync } from '../../hooks/useDraftSync';
import ImageViewer from '../../components/ImageViewer';
import PageTabs from '../../components/PageTabs';
import Spinner from '../../components/ui/Spinner';
import SurveyHeader from './SurveyHeader';
import DynamicForm from './DynamicForm';

export default function VerificationPanel() {
  const [currentSurveyId, setCurrentSurveyId] = useState<number | null>(null);
  const formRef = useRef<{ save: () => void; forceSave: () => void }>(null);
  const { data: surveys } = useSurveys();
  const { data: fieldSpecs } = useFieldSpecs();
  const saveSurveyMutation = useSaveSurvey();
  const unverifyMutation = useUnverifySurvey();
  const initSurvey = useVerificationStore((s) => s.initSurvey);
  const mergeServerDraft = useVerificationStore((s) => s.mergeServerDraft);
  const surveyUI = useVerificationStore((s) =>
    currentSurveyId !== null ? s.surveysUI[currentSurveyId] : undefined
  );

  const allSurveys = useMemo(() => surveys ?? [], [surveys]);
  const currentSurvey = useMemo(
    () => allSurveys.find((s) => s.id === currentSurveyId),
    [allSurveys, currentSurveyId]
  );

  const clickableSurveys = useMemo(
    () => allSurveys.filter((s) => s.status === 'ready' || s.status === 'verified' || s.status === 'error'),
    [allSurveys]
  );

  const currentIndex = useMemo(
    () => allSurveys.findIndex((s) => s.id === currentSurveyId),
    [allSurveys, currentSurveyId]
  );

  const { data: surveyResult, isLoading: resultLoading, isFetching: resultFetching } = useSurveyResult(currentSurveyId);
  const { data: imageUrls, isLoading: imagesLoading, isRefetching: imagesRefetching } = useSurveyImages(currentSurveyId, allSurveys);

  useDraftSync(currentSurveyId);

  const formLoading = !surveyResult && (resultLoading || resultFetching);
  const aiResult = surveyResult?.id === currentSurveyId ? surveyResult?.result ?? null : null;
  const serverDraft = surveyResult?.id === currentSurveyId ? surveyResult?.draft ?? null : null;

  useEffect(() => {
    if (currentSurveyId !== null && serverDraft) {
      mergeServerDraft(currentSurveyId, serverDraft);
    }
  }, [currentSurveyId, serverDraft, mergeServerDraft]);

  useEffect(() => {
    if (currentSurveyId === null && clickableSurveys.length > 0) {
      const first = clickableSurveys[0].id;
      initSurvey(first);
      setCurrentSurveyId(first);
    }
  }, [clickableSurveys, currentSurveyId, initSurvey]);

  const handleSurveyChange = (surveyId: number) => {
    initSurvey(surveyId);
    setCurrentSurveyId(surveyId);
  };

  const navigateToNextClickable = (direction: -1 | 1) => {
    const currentClickableIndex = clickableSurveys.findIndex((s) => s.id === currentSurveyId);
    const nextIndex = currentClickableIndex + direction;
    if (nextIndex >= 0 && nextIndex < clickableSurveys.length) {
      handleSurveyChange(clickableSurveys[nextIndex].id);
    }
  };

  const handlePrevSurvey = () => navigateToNextClickable(-1);
  const handleNextSurvey = () => navigateToNextClickable(1);

  const handleSave = async (values: Record<string, unknown>) => {
    await saveSurveyMutation.mutateAsync({
      surveyId: currentSurveyId!,
      values,
      force: false,
    });
  };

  const handleForceSave = async (values: Record<string, unknown>) => {
    await saveSurveyMutation.mutateAsync({
      surveyId: currentSurveyId!,
      values,
      force: true,
    });
  };

  const handleUnverify = async () => {
    if (currentSurveyId === null) return;
    await unverifyMutation.mutateAsync(currentSurveyId);
  };

  const currentPage = surveyUI?.selectedPage ?? 0;

  if (currentSurveyId === null) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50 text-gray-400">
        Brak gotowych ankiet do weryfikacji
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full w-full">
      <SurveyHeader
        currentSurveyId={currentSurveyId}
        surveys={allSurveys}
        totalSurveys={allSurveys.length}
        currentIndex={currentIndex}
        onPrev={handlePrevSurvey}
        onNext={handleNextSurvey}
        onSave={() => formRef.current?.save()}
        onUnverify={handleUnverify}
        onSurveyChange={handleSurveyChange}
      />

      <div className="flex-1 flex overflow-hidden">
        <div className="w-[680px] shrink-0 flex flex-col border-r border-gray-200 bg-white">
          <PageTabs surveyId={currentSurveyId} currentPage={currentPage} />
          <div className="flex-1 min-h-0">
            <ImageViewer imageUrl={imageUrls?.[currentPage] ?? null} page={currentPage} isLoading={imagesLoading || imagesRefetching} />
          </div>
        </div>

        <div className="flex-1 min-w-0 flex flex-col overflow-y-auto relative">
          {formLoading && (
            <div className="absolute inset-0 z-10 flex items-center justify-center bg-white/70">
              <div className="flex flex-col items-center gap-3">
                <Spinner className="w-8 h-8" />
                <span className="text-sm text-gray-500">Ładowanie ankiety...</span>
              </div>
            </div>
          )}
          <DynamicForm
            ref={formRef}
            surveyId={currentSurveyId}
            fieldSpecs={fieldSpecs ?? []}
            aiResult={aiResult}
            onSave={handleSave}
            onForceSave={handleForceSave}
            onNextSurvey={handleNextSurvey}
            disabled={saveSurveyMutation.isPending}
            readOnly={currentSurvey?.status === 'verified'}
          />
        </div>
      </div>
    </div>
  );
}
