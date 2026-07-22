import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSurveys, useFieldSpecs, useSurveyResult, useSaveSurvey, useProcessingStatus } from '../../api/hooks';
import { useVerificationStore } from '../../store/verificationStore';
import ImageViewer from '../../components/ImageViewer';
import PageTabs from '../../components/PageTabs';
import SurveyHeader from './SurveyHeader';
import DynamicForm from './DynamicForm';

export default function VerificationPanel() {
  const navigate = useNavigate();
  const { data: surveys } = useSurveys();
  const { data: fieldSpecs } = useFieldSpecs();
  const saveSurveyMutation = useSaveSurvey();
  const initSurvey = useVerificationStore((s) => s.initSurvey);
  const getSurveyUI = useVerificationStore((s) => s.getSurveyUI);

  const { data: processingStatus } = useProcessingStatus();
  const isRunning = processingStatus?.is_running ?? false;

  const [currentSurveyId, setCurrentSurveyId] = useState<number | null>(null);

  const allSurveys = useMemo(() => surveys ?? [], [surveys]);
  const allDone = useMemo(
    () => allSurveys.length > 0 && allSurveys.every((s) => s.status === 'verified' || s.status === 'error'),
    [allSurveys]
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

  useEffect(() => {
    if (currentSurveyId === null && clickableSurveys.length > 0) {
      const first = clickableSurveys[0].id;
      initSurvey(first);
      setCurrentSurveyId(first);
    }
  }, [clickableSurveys, currentSurveyId, initSurvey]);

  useEffect(() => {
    if (allDone && !isRunning) {
      navigate('/complete', { replace: true });
    }
  }, [allDone, isRunning, navigate]);

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

  const currentPage = currentSurveyId !== null
    ? getSurveyUI(currentSurveyId).selectedPage
    : 0;

  const handlePageChange = () => {};

  if (currentSurveyId === null) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50 text-gray-400">
        Brak gotowych ankiet do weryfikacji
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <SurveyHeader
        currentSurveyId={currentSurveyId}
        surveys={allSurveys}
        totalSurveys={allSurveys.length}
        currentIndex={currentIndex}
        onPrev={handlePrevSurvey}
        onNext={handleNextSurvey}
        onSave={() => {}}
        onSurveyChange={handleSurveyChange}
      />

      <div className="flex-1 flex overflow-hidden">
        <div className="w-[40%] flex flex-col border-r border-gray-200 bg-white">
          <div className="flex-1 min-h-0">
            <ImageViewer surveyId={currentSurveyId} page={currentPage} />
          </div>
          <PageTabs
            surveyId={currentSurveyId}
            currentPage={currentPage}
            onChange={handlePageChange}
          />
        </div>

        <div className="flex-1 flex flex-col overflow-y-auto bg-gray-50 p-4">
          <DynamicForm
            surveyId={currentSurveyId}
            fieldSpecs={fieldSpecs ?? []}
            aiResult={surveyResult?.result ?? null}
            onSave={handleSave}
            onNextSurvey={handleNextSurvey}
            disabled={saveSurveyMutation.isPending}
          />
        </div>
      </div>
    </div>
  );
}
