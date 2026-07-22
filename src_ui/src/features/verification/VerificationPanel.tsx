import { useEffect, useMemo, useState } from 'react';
import { useSurveys } from '../../api/hooks';
import { useVerificationStore } from '../../store/verificationStore';
import ImageViewer from '../../components/ImageViewer';
import PageTabs from '../../components/PageTabs';
import SurveyTabs from './SurveyTabs';

export default function VerificationPanel() {
  const { data: surveys } = useSurveys();
  const initSurvey = useVerificationStore((s) => s.initSurvey);
  const getSurveyUI = useVerificationStore((s) => s.getSurveyUI);

  const clickableSurveys = useMemo(
    () => (surveys ?? []).filter((s) => s.status === 'ready' || s.status === 'verified'),
    [surveys]
  );

  const [currentSurveyId, setCurrentSurveyId] = useState<number | null>(null);

  useEffect(() => {
    if (currentSurveyId === null && clickableSurveys.length > 0) {
      const first = clickableSurveys[0].id;
      initSurvey(first);
      setCurrentSurveyId(first);
    }
  }, [clickableSurveys, currentSurveyId, initSurvey]);

  const handleSurveyChange = (surveyId: number) => {
    setCurrentSurveyId(surveyId);
  };

  const currentPage = currentSurveyId !== null
    ? getSurveyUI(currentSurveyId).selectedPage
    : 0;

  const handlePageChange = (_page: number) => {
  };

  if (currentSurveyId === null) {
    return (
      <div className="flex-1 flex items-center justify-center bg-gray-50 text-gray-400">
        Brak gotowych ankiet do weryfikacji
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <SurveyTabs
        currentSurveyId={currentSurveyId}
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
          <div className="text-gray-400 text-center py-8">
            Formularz dynamiczny — Etap 7
          </div>
        </div>
      </div>
    </div>
  );
}
