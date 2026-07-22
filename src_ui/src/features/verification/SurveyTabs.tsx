import { useMemo } from 'react';
import { useSurveys, type SurveyListItem } from '../../api/hooks';
import { useVerificationStore } from '../../store/verificationStore';

interface SurveyTabsProps {
  currentSurveyId: number | null;
  onSurveyChange: (surveyId: number) => void;
}

function statusIcon(status: SurveyListItem['status']): string {
  switch (status) {
    case 'verified': return '\u2713';
    case 'ready': return '\u27F3';
    case 'error': return '\u2717';
    default: return '';
  }
}

function statusLabel(status: SurveyListItem['status']): string {
  switch (status) {
    case 'verified': return 'Zweryfikowana';
    case 'ready': return 'Gotowa';
    case 'error': return 'B\u0142\u0105d';
    default: return '';
  }
}

export default function SurveyTabs({ currentSurveyId, onSurveyChange }: SurveyTabsProps) {
  const { data: surveys } = useSurveys();
  const initSurvey = useVerificationStore((s) => s.initSurvey);

  const clickableSurveys = useMemo(
    () => (surveys ?? []).filter((s) => s.status === 'ready' || s.status === 'verified'),
    [surveys]
  );

  const currentIndex = clickableSurveys.findIndex((s) => s.id === currentSurveyId);

  const handleTabClick = (surveyId: number) => {
    initSurvey(surveyId);
    onSurveyChange(surveyId);
  };

  const handlePrev = () => {
    if (currentIndex > 0) {
      handleTabClick(clickableSurveys[currentIndex - 1].id);
    }
  };

  const handleNext = () => {
    if (currentIndex < clickableSurveys.length - 1) {
      handleTabClick(clickableSurveys[currentIndex + 1].id);
    }
  };

  return (
    <div className="flex items-center border-b border-gray-200 bg-white px-2">
      <button
        onClick={handlePrev}
        disabled={currentIndex <= 0}
        className="px-3 py-2 text-sm text-gray-600 hover:text-gray-900 disabled:text-gray-300 disabled:cursor-not-allowed"
        title="Poprzednia ankieta"
      >
        &#x25C0; Poprzednia
      </button>

      <div className="flex-1 flex overflow-x-auto">
        {(surveys ?? []).map((survey) => {
          const isClickable = survey.status === 'ready' || survey.status === 'verified';
          const isActive = survey.id === currentSurveyId;
          return (
            <button
              key={survey.id}
              role="tab"
              aria-selected={isActive}
              disabled={!isClickable}
              onClick={() => isClickable && handleTabClick(survey.id)}
              title={
                isClickable
                  ? `Ankieta ${survey.id} — ${statusLabel(survey.status)}`
                  : `Ankieta ${survey.id} — ${survey.status}`
              }
              className={`flex items-center gap-1 px-3 py-2 text-sm whitespace-nowrap border-b-2 transition-colors ${
                isActive
                  ? 'border-[var(--color-info)] text-[var(--color-info)] font-medium'
                  : 'border-transparent text-gray-500'
              } ${
                !isClickable
                  ? 'opacity-40 cursor-not-allowed'
                  : 'hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <span>{survey.id}</span>
              <span className="text-xs">{statusIcon(survey.status)}</span>
            </button>
          );
        })}
      </div>

      <button
        onClick={handleNext}
        disabled={currentIndex >= clickableSurveys.length - 1}
        className="px-3 py-2 text-sm text-gray-600 hover:text-gray-900 disabled:text-gray-300 disabled:cursor-not-allowed"
        title="Nast\u0119pna ankieta"
      >
        Nast\u0119pna &#x25B6;
      </button>
    </div>
  );
}
