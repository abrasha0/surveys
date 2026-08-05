import { useEffect, useMemo, useRef, useState } from 'react';
import { useSurveys, useFieldSpecs, useSurveyResult, useSaveSurvey, useSurveyImages, useUnverifySurvey } from '../../api/hooks';
import { useVerificationStore } from '../../store/verificationStore';
import { useDraftSync } from '../../hooks/useDraftSync';
import ImageViewer from '../../components/ImageViewer';
import PageTabs from '../../components/PageTabs';
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
  const surveyUI = useVerificationStore((s) =>
    currentSurveyId !== null ? s.surveysUI[currentSurveyId] : undefined
  );

  const allSurveys = useMemo(() => surveys ?? [], [surveys]);
  const currentSurvey = useMemo(
    () => allSurveys.find((s) => s.id === currentSurveyId),
    [allSurveys, currentSurveyId]
  );

  const clickableSurveys = useMemo(
    () => allSurveys.filter((s) => s.status === 'ready' || s.status === 'verified'),
    [allSurveys]
  );

  const currentIndex = useMemo(
    () => allSurveys.findIndex((s) => s.id === currentSurveyId),
    [allSurveys, currentSurveyId]
  );

  const { data: surveyResult } = useSurveyResult(currentSurveyId);
  const { data: imageUrls } = useSurveyImages(currentSurveyId);

  useDraftSync(currentSurveyId);

  useEffect(() => {
    if (currentSurveyId === null && clickableSurveys.length > 0) {
      const first = clickableSurveys[0].id;
      initSurvey(first);
      setCurrentSurveyId(first);
    }
  }, [clickableSurveys, currentSurveyId, initSurvey]);

  useEffect(() => {
    return () => {
      if (imageUrls) {
        Object.values(imageUrls).forEach((url) => {
          if (url) URL.revokeObjectURL(url);
        });
      }
    };
  }, [imageUrls]);

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

  const handleUnverify = async () => {
    if (currentSurveyId === null) return;
    await unverifyMutation.mutateAsync(currentSurveyId);
  };

  const handleForceSave = async () => {
    if (currentSurveyId === null) return;
    formRef.current?.forceSave();
  };

  const currentPage = surveyUI?.selectedPage ?? 0;

  const handlePageChange = () => {};

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
        onForceSave={handleForceSave}
        onSurveyChange={handleSurveyChange}
      />

      <div className="flex-1 flex overflow-hidden">
        <div className="w-[680px] shrink-0 flex flex-col border-r border-gray-200 bg-white">
          <PageTabs
            surveyId={currentSurveyId}
            currentPage={currentPage}
            onChange={handlePageChange}
          />
          <div className="flex-1 min-h-0">
            <ImageViewer imageUrl={imageUrls?.[currentPage] ?? null} page={currentPage} />
          </div>
        </div>

<div className="flex-1 min-w-0 flex flex-col overflow-y-auto">
          <DynamicForm
            ref={formRef}
            surveyId={currentSurveyId}
            fieldSpecs={fieldSpecs ?? []}
            aiResult={surveyResult?.result ?? null}
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
