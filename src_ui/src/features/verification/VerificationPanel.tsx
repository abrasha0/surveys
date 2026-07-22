import { useEffect, useMemo, useState } from 'react';
import { useSurveys, useFieldSpecs, useSurveyResult, useSaveSurvey } from '../../api/hooks';
import { useVerificationStore } from '../../store/verificationStore';
import ImageViewer from '../../components/ImageViewer';
import PageTabs from '../../components/PageTabs';
import SurveyHeader from './SurveyHeader';
import DynamicForm from './DynamicForm';

export default function VerificationPanel() {
  const { data: surveys } = useSurveys();
  const { data: fieldSpecs } = useFieldSpecs();
  const saveSurveyMutation = useSaveSurvey();
  const initSurvey = useVerificationStore((s) => s.initSurvey);
  const getSurveyUI = useVerificationStore((s) => s.getSurveyUI);

  const [currentSurveyId, setCurrentSurveyId] = useState<number | null>(null);

  const clickableSurveys = useMemo(
    () => (surveys ?? []).filter((s) => s.status === 'ready' || s.status === 'verified'),
    [surveys]
  );

  const currentIndex = useMemo(
    () => clickableSurveys.findIndex((s) => s.id === currentSurveyId),
    [clickableSurveys, currentSurveyId]
  );

  const { data: surveyResult } = useSurveyResult(currentSurveyId);

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

  const handlePrevSurvey = () => {
    if (currentIndex > 0) {
      handleSurveyChange(clickableSurveys[currentIndex - 1].id);
    }
  };

  const handleNextSurvey = () => {
    if (currentIndex < clickableSurveys.length - 1) {
      handleSurveyChange(clickableSurveys[currentIndex + 1].id);
    }
  };

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
        clickableSurveys={clickableSurveys}
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
