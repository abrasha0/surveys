import type { SurveyListItem } from '../../api/hooks';

interface SurveyHeaderProps {
  currentSurveyId: number | null;
  surveys: SurveyListItem[];
  totalSurveys: number;
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
    case 'processing': return '\u23F3';
    case 'queued': return '\u23F8';
    case 'error': return '\u2717';
    default: return '';
  }
}

function statusTooltip(status: SurveyListItem['status']): string | undefined {
  switch (status) {
    case 'processing': return 'W trakcie przetwarzania...';
    case 'queued': return 'W kolejce';
    case 'error': return 'Błąd przetwarzania';
    default: return undefined;
  }
}

function isClickable(status: SurveyListItem['status']): boolean {
  return status === 'ready' || status === 'verified';
}

function tabStyle(status: SurveyListItem['status'], isActive: boolean): string {
  if (isActive) {
    switch (status) {
      case 'ready':
      case 'verified':
        return 'bg-[var(--color-success)] text-white';
      case 'processing':
        return 'bg-[var(--color-info)] text-white';
      case 'error':
        return 'bg-[var(--color-error)] text-white';
      default:
        return 'bg-[var(--color-info)] text-white';
    }
  }

  const base = 'transition-colors';
  switch (status) {
    case 'ready':
    case 'verified':
      return `${base} bg-green-100 text-green-800 hover:bg-green-200`;
    case 'processing':
      return `${base} bg-blue-100 text-blue-800`;
    case 'queued':
      return `${base} bg-gray-200 text-gray-400`;
    case 'error':
      return `${base} bg-red-100 text-red-800`;
    default:
      return `${base} text-gray-600 hover:bg-gray-100`;
  }
}

export default function SurveyHeader({
  currentSurveyId,
  surveys,
  totalSurveys,
  currentIndex,
  onPrev,
  onNext,
  onSave,
  onSurveyChange,
}: SurveyHeaderProps) {
  return (
    <div className="flex items-center justify-between px-2 py-2 border-b border-gray-200 bg-white">
      <span className="font-medium text-sm min-w-fit">
        Ankieta {currentIndex + 1} z {totalSurveys}
      </span>

      <div className="flex-1 flex overflow-x-auto mx-4 gap-1">
        {surveys.map((survey) => {
          const isActive = survey.id === currentSurveyId;
          const clickable = isClickable(survey.status);
          const tooltip = statusTooltip(survey.status);
          return (
            <button
              key={survey.id}
              role="tab"
              aria-selected={isActive}
              disabled={!clickable}
              onClick={() => clickable && onSurveyChange(survey.id)}
              title={tooltip}
              className={`flex items-center gap-1 px-3 py-1.5 text-sm whitespace-nowrap rounded ${tabStyle(survey.status, isActive)} ${!clickable ? 'cursor-not-allowed' : ''} ${survey.status === 'processing' ? 'animate-pulse' : ''}`}
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
          disabled={currentIndex === surveys.length - 1}
          className="px-3 py-1.5 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:text-gray-300 disabled:cursor-not-allowed"
        >
          Następna ankieta
        </button>
      </div>
    </div>
  );
}
