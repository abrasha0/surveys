import type { ProcessingStatus } from '../../api/hooks';

interface ProcessingProgressBarProps {
  status: ProcessingStatus | undefined;
  isLoading: boolean;
  onStart?: () => void;
  isStarting?: boolean;
}

function formatEta(seconds: number | null): string {
  if (seconds === null || seconds === undefined) return 'Obliczanie...';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `~${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
}

function stageLabel(stage: string | null, page: number | null, surveyId: number | null): string {
  if (!stage) return '';
  const stageName = stage === 'vlm' ? 'VLM' : 'Formatowanie';
  const pageStr = page !== null ? `strona ${page + 1}/5` : '';
  const surveyStr = surveyId !== null ? `ankieta ${surveyId}` : '';
  return [stageName, pageStr, surveyStr].filter(Boolean).join(' — ');
}

export default function ProcessingProgressBar({
  status,
  isLoading,
  onStart,
  isStarting,
}: ProcessingProgressBarProps) {
  if (isLoading || !status) {
    return (
      <div className="flex items-center h-12 px-4 bg-gray-100 border-b border-gray-200 text-sm text-gray-400">
        Ładowanie statusu...
      </div>
    );
  }

  const { total, processed, errors, current_stage, current_page, current_survey_id, eta_seconds, is_running } = status;
  const progress = total > 0 ? Math.min((processed + errors) / total, 1) : 0;
  const activity = stageLabel(current_stage, current_page, current_survey_id);
  const unprocessed = total - processed - errors;

  if (total === 0) {
    return (
      <div className="flex items-center h-12 px-4 bg-gray-100 border-b border-gray-200 text-sm text-gray-400">
        Brak ankiet do przetworzenia
      </div>
    );
  }

  return (
    <div className="flex items-center h-12 px-4 bg-gray-100 border-b border-gray-200 text-sm gap-4">
      <div className="flex-1 flex items-center gap-3 min-w-0">
        <div className="w-32 h-2.5 bg-gray-300 rounded-full overflow-hidden shrink-0">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${progress * 100}%`,
              backgroundColor: errors > 0 && progress >= 1 ? 'var(--color-error)' : 'var(--color-info)',
            }}
          />
        </div>

        <span className="text-gray-700 whitespace-nowrap shrink-0">
          Przetworzono: {processed} z {total}
          {errors > 0 && <> · Błędy: {errors}</>}
          {!is_running && progress >= 1
            ? ' · Wszystkie ankiety przetworzone ✓'
            : ` · ETA: ${formatEta(eta_seconds)}`
          }
        </span>
      </div>

      <div className="flex items-center gap-3 shrink-0">
        {activity && (
          <span className="text-gray-500 truncate max-w-64">{activity}</span>
        )}

        {is_running ? (
          <span className="flex items-center gap-1.5 text-[var(--color-info)] font-medium">
            <span className="inline-block w-2 h-2 rounded-full bg-[var(--color-info)] animate-pulse" />
            Przetwarzanie w tle...
          </span>
        ) : unprocessed > 0 && onStart ? (
          <button
            onClick={onStart}
            disabled={isStarting}
            className="px-3 py-1 text-sm font-medium text-white bg-[var(--color-info)] rounded hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isStarting ? 'Uruchamianie...' : 'Rozpocznij analizę'}
          </button>
        ) : progress >= 1 ? (
          <span className="text-[var(--color-success)] font-medium">
            Wszystkie ankiety przetworzone ✓
          </span>
        ) : null}
      </div>
    </div>
  );
}
