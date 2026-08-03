import { useEffect, useRef, useState } from "react";
import type { ProcessingStatus } from "../../api/hooks";

interface ProcessingProgressBarProps {
  status: ProcessingStatus | undefined;
  isLoading: boolean;
  onStart?: () => void;
  isStarting?: boolean;
}

function formatEta(seconds: number | null): string {
  if (seconds === null || seconds === undefined) return "-";
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  if (m > 0) return `zostało ~${m}min ${s}s`;
  return `zostało ~${s}s`;
}

function stageLabel(
  stage: string | null,
  page: number | null,
  surveyId: number | null,
): string {
  if (!stage) return "";
  const stageName = stage === "vlm" ? "VLM" : "Formatowanie";
  const pageStr = page !== null ? `strona ${page + 1}/5` : "";
  const surveyStr = surveyId !== null ? `ankieta ${surveyId}` : "";
  return [stageName, pageStr, surveyStr].filter(Boolean).join(" — ");
}

export default function ProcessingProgressBar({
  status,
  isLoading,
  onStart,
  isStarting,
}: ProcessingProgressBarProps) {
  const [localEtaSeconds, setLocalEtaSeconds] = useState<number | null>(null);
  const [showCompletion, setShowCompletion] = useState(false);
  const lastBackendEta = useRef<number | null>(null);

  const total = status?.total ?? 0;
  const processed = status?.processed ?? 0;
  const errors = status?.errors ?? 0;
  const total_pages = status?.total_pages ?? 0;
  const processed_pages = status?.processed_pages ?? 0;
  const is_running = status?.is_running ?? false;
  const current_stage = status?.current_stage ?? null;
  const current_page = status?.current_page ?? null;
  const current_survey_id = status?.current_survey_id ?? null;

  useEffect(() => {
    const newEta = status?.eta_seconds ?? null;
    if (newEta !== null && newEta !== lastBackendEta.current) {
      lastBackendEta.current = newEta;
      setLocalEtaSeconds(newEta);
    }
  }, [status?.eta_seconds]);

  useEffect(() => {
    if (!is_running) return;
    const timer = setInterval(() => {
      setLocalEtaSeconds((prev) => {
        if (prev === null || prev <= 0) return prev;
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(timer);
  }, [is_running]);

  useEffect(() => {
    const isFinished = !is_running && total > 0 && processed + errors >= total;
    if (isFinished) {
      setShowCompletion(true);
      const timer = setTimeout(() => {
        setShowCompletion(false);
      }, 3000);
      return () => clearTimeout(timer);
    } else {
      setShowCompletion(false);
    }
  }, [is_running, total, processed, errors]);

  if (isLoading || !status) {
    return (
      <div className="flex items-center h-16 px-4 bg-gray-100 border-b border-gray-200 text-sm text-gray-400">
        Ładowanie statusu...
      </div>
    );
  }

  const pagesComplete =
    total_pages > 0 ? Math.min((processed_pages + errors) / total_pages, 1) : 0;
  const activity = stageLabel(current_stage, current_page, current_survey_id);
  const unprocessed = total - processed - errors;

  if (total === 0) {
    return (
      <div className="flex items-center h-16 px-4 bg-gray-100 border-b border-gray-200 text-sm text-gray-400">
        Brak ankiet do przetworzenia
      </div>
    );
  }

  return (
    <div className={`flex items-center h-16 px-4 border-b border-gray-200 text-sm gap-4 ${is_running ? 'bg-blue-50 border-l-4 border-l-[var(--color-info)]' : 'bg-gray-100'}`}>
      <div className="flex-1 flex items-center gap-3 min-w-0">
        <div className="w-40 h-3 bg-gray-300 rounded-full overflow-hidden shrink-0">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{
              width: `${pagesComplete * 100}%`,
              backgroundColor:
                errors > 0 && pagesComplete >= 1
                  ? "var(--color-error)"
                  : "var(--color-info)",
            }}
          />
        </div>

        <span className="text-gray-700 whitespace-nowrap shrink-0 text-sm">
          przetworzono: {processed_pages} z {total_pages} stron
          {errors > 0 && <> · Błędy: {errors}</>}
          {is_running && localEtaSeconds === null
            ? " · obliczanie..."
            : localEtaSeconds !== null && is_running
              ? ` · ${formatEta(localEtaSeconds)}`
              : ""}
        </span>
      </div>

      <div className="flex items-center gap-3 shrink-0">
        {activity && (
          <span className="text-gray-700 truncate max-w-72 text-sm font-medium">{activity}</span>
        )}

        {is_running ? (
          <span className="flex items-center gap-1.5 text-[var(--color-info)] font-semibold text-sm">
            <span className="inline-block w-2.5 h-2.5 rounded-full bg-[var(--color-info)] animate-pulse" />
            przetwarzanie w tle...
          </span>
        ) : unprocessed > 0 && onStart ? (
          <button
            onClick={onStart}
            disabled={isStarting}
            className="px-3 py-1.5 text-sm font-medium text-white bg-[var(--color-info)] rounded hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isStarting ? "uruchamianie..." : "rozpocznij analizę"}
          </button>
        ) : pagesComplete >= 1 && showCompletion ? (
          <span
            className="text-[var(--color-success)] font-medium transition-opacity duration-1000 text-sm"
            style={{ opacity: showCompletion ? 1 : 0 }}
          >
            wszystkie ankiety przetworzone ✓
          </span>
        ) : null}
      </div>
    </div>
  );
}
