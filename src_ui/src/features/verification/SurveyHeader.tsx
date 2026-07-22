import type { SurveyListItem } from '../../api/hooks';

interface SurveyHeaderProps {
  currentSurveyId: number | null;
  clickableSurveys: SurveyListItem[];
  currentIndex: number;
  onPrev: () => void;
  onNext: () => void;
  onSave: () => void;
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

export default function SurveyHeader({
  currentSurveyId,
  clickableSurveys,
  currentIndex,
  onPrev,
  onNext,
  onSave,
  onSurveyChange,
}: SurveyHeaderProps) {
  return (
    <div className="flex items-center justify-between px-2 py-2 border-b border-gray-200 bg-white">
      <span className="font-medium text-sm min-w-fit">
        Ankieta {currentIndex + 1} z {clickableSurveys.length}
      </span>

      <div className="flex-1 flex overflow-x-auto mx-4 gap-1">
        {clickableSurveys.map((survey) => {
          const isActive = survey.id === currentSurveyId;
          const isClickable = survey.status === 'ready' || survey.status === 'verified';
          return (
            <button
              key={survey.id}
              role="tab"
              aria-selected={isActive}
              disabled={!isClickable}
              onClick={() => onSurveyChange(survey.id)}
              className={`flex items-center gap-1 px-3 py-1.5 text-sm whitespace-nowrap rounded transition-colors ${
                isActive
                  ? 'bg-[var(--color-info)] text-white'
                  : 'text-gray-600 hover:bg-gray-100'
              } ${!isClickable ? 'opacity-40 cursor-not-allowed' : ''}`}
            >
              <span>{survey.id}</span>
              <span className="text-xs">{statusIcon(survey.status)}</span>
            </button>
          );
        })}
      </div>

      <div className="flex items-center gap-2">
        <button
          onClick={onPrev}
          disabled={currentIndex === 0}
          className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:text-gray-300 disabled:cursor-not-allowed"
        >
          Poprzednia ankieta
        </button>
        <button
          onClick={onSave}
          className="px-3 py-1.5 text-sm font-medium text-white bg-[var(--color-success)] rounded hover:opacity-90"
        >
          Zatwierdź ankietę
        </button>
        <button
          onClick={onNext}
          disabled={currentIndex === clickableSurveys.length - 1}
          className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:text-gray-300 disabled:cursor-not-allowed"
        >
          Następna ankieta
        </button>
      </div>
    </div>
  );
}
