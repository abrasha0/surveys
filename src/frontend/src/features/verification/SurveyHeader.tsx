import type { SurveyListItem } from '../../api/hooks';

interface SurveyHeaderProps {
  currentSurveyId: number | null;
  surveys: SurveyListItem[];
  totalSurveys: number;
  currentIndex: number;
  onPrev: () => void;
  onNext: () => void;
  onSave: () => void;
  onUnverify: () => void;
  onSurveyChange: (surveyId: number) => void;
}

function statusIcon(status: SurveyListItem['status']): React.ReactNode {
  switch (status) {
    case 'verified': return <span className="text-xs">✓</span>;
    case 'ready': return <span className="text-xs">↻</span>;
    case 'processing': return (
      <svg className="animate-spin h-3 w-3" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
    );
    case 'queued': return <span className="text-xs">⏸</span>;
    case 'error': return <span className="text-xs">✗</span>;
    default: return null;
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
  return status === 'ready' || status === 'verified' || status === 'error';
}

function tabStyle(status: SurveyListItem['status'], isActive: boolean): string {
  if (isActive) {
    switch (status) {
      case 'ready':
        return 'bg-amber-500 text-white';
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
      return `${base} bg-amber-100 text-amber-800 hover:bg-amber-200`;
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
  onUnverify,
  onSurveyChange,
}: SurveyHeaderProps) {
  const queuedCount = surveys.filter((s) => s.status === 'queued').length;
  const processingCount = surveys.filter((s) => s.status === 'processing').length;
  const readyCount = surveys.filter((s) => s.status === 'ready').length;
  const verifiedCount = surveys.filter((s) => s.status === 'verified').length;

  return (
    <div className="flex items-center justify-between px-2 py-2 border-b border-gray-200 bg-white">
      <div className="flex items-center gap-3 min-w-fit">
        <span className="font-medium text-sm">
          Ankieta {currentIndex + 1} z {totalSurveys}
        </span>
        {(queuedCount > 0 || processingCount > 0 || readyCount > 0 || verifiedCount > 0) && (
          <div className="flex items-center gap-1.5 text-xs">
            {queuedCount > 0 && (
              <span className="px-1.5 py-0.5 rounded bg-gray-200 text-gray-500 font-medium">
                kolejka: {queuedCount}
              </span>
            )}
            {processingCount > 0 && (
              <span className="px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 font-medium">
                przetwarzanie: {processingCount}
              </span>
            )}
            {readyCount > 0 && (
              <span className="px-1.5 py-0.5 rounded bg-amber-100 text-amber-700 font-medium">
                do weryfikacji: {readyCount}
              </span>
            )}
            {verifiedCount > 0 && (
              <span className="px-1.5 py-0.5 rounded bg-green-100 text-green-700 font-medium">
                zatwierdzone: {verifiedCount}
              </span>
            )}
          </div>
        )}
      </div>

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
        {(() => {
          const currentSurvey = surveys.find(s => s.id === currentSurveyId);
          switch (currentSurvey?.status) {
            case 'ready':
            case 'error':
              return (
                <button onClick={onSave}
                  className="px-3 py-1.5 text-sm font-medium text-white bg-[var(--color-success)] rounded hover:opacity-90">
                  Zatwierdź ankietę
                </button>
              );
            case 'verified':
              return (
                <button onClick={onUnverify}
                  className="px-3 py-1.5 text-sm font-medium text-white bg-[var(--color-warning)] rounded hover:opacity-90">
                  Cofnij zatwierdzenie
                </button>
              );
            default:
              return (
                <button disabled
                  className="px-3 py-1.5 text-sm font-medium text-gray-300 bg-gray-100 rounded cursor-not-allowed">
                  {currentSurvey?.status === 'queued' ? 'W kolejce' : 'Przetwarzanie...'}
                </button>
              );
          }
        })()}
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
