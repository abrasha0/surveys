import { useEffect, useMemo, useRef, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import {
  useClearSession,
  useExportCsv,
  useProcessingStatus,
  useStartProcessing,
  useSurveys,
} from '../../api/hooks';
import { useVerificationStore } from '../../store/verificationStore';
import { formatEta as sharedFormatEta } from '../../utils/formatEta';

function formatEta(seconds: number | null | undefined): string {
  if (seconds !== null && seconds !== undefined && seconds <= 0) return 'Zakończono';
  return sharedFormatEta(seconds);
}

export default function WelcomePage() {
  const navigate = useNavigate();
  const [error, setError] = useState('');
  const [waitingForRunning, setWaitingForRunning] = useState(false);
  const [batchSize, setBatchSize] = useState<number>(0);
  const waitingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const { data: surveys } = useSurveys();
  const { data: processingStatus } = useProcessingStatus();
  const startProcessing = useStartProcessing();
  const clearSession = useClearSession();
  const exportCsv = useExportCsv();
  const clearCache = useVerificationStore((s) => s.clearAllCache);

  useEffect(() => {
    return () => {
      if (waitingIntervalRef.current) {
        clearInterval(waitingIntervalRef.current);
        waitingIntervalRef.current = null;
      }
    };
  }, []);

  const isRunning = processingStatus?.is_running ?? false;

  const stats = useMemo(() => {
    const list = surveys ?? [];
    const status = processingStatus;
    const done = list.filter(
      (s) => s.status === 'ready' || s.status === 'error' || s.status === 'verified'
    );
    return {
      total: list.length,
      processed: done.length,
      verified: list.filter((s) => s.status === 'verified').length,
      processedPages:
        status?.processed_pages ??
        done.reduce((acc, s) => acc + s.files.length, 0),
      errors: status?.errors ?? 0,
    };
  }, [surveys, processingStatus]);

  const remaining = stats.total - stats.processed;
  const maxBatch = remaining > 0 ? remaining : 1;

  useEffect(() => {
    if (maxBatch > 0 && batchSize === 0) {
      setBatchSize(maxBatch);
    }
  }, [maxBatch]);

  const isCovered = stats.total > 0 && stats.processed === stats.total;
  const batchDone = useMemo(() => {
    const ps = processingStatus;
    if (!ps) return false;
    return (
      ps.batch_size > 0 &&
      !ps.is_running &&
      ps.batch_remaining !== null &&
      ps.batch_remaining <= 0 &&
      !isCovered
    );
  }, [processingStatus, isCovered]);

  useEffect(() => {
    if (batchDone && remaining > 0) {
      setBatchSize(remaining);
    }
  }, [batchDone, remaining]);

  if (processingStatus === undefined || surveys === undefined) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--color-info)]" />
      </div>
    );
  }

  if (isRunning) {
    return <Navigate to="/app" replace />;
  }

  const readyCount = surveys.filter((s) => s.status === 'ready').length;
  const allVerified = isCovered && stats.verified === stats.total;
  const showEta = processingStatus?.eta_seconds != null;
  const etaText = formatEta(processingStatus?.eta_seconds);
  const etaLabel = 'Czas przetwarzania';
  const remainingPages = (processingStatus?.total_pages ?? stats.processedPages) - stats.processedPages;
  const perSurveyEtaSeconds =
    showEta && remaining > 0 ? (processingStatus?.eta_seconds ?? 0) / remaining : null;
  const batchEtaSeconds =
    perSurveyEtaSeconds !== null ? perSurveyEtaSeconds * (batchSize || maxBatch) : null;
  const batchEtaText = formatEta(batchEtaSeconds);

  const handleStart = (batchSize?: number) => {
    setError('');
    setWaitingForRunning(true);
    startProcessing.mutate(batchSize, {
      onSuccess: () => {
        waitingIntervalRef.current = setInterval(async () => {
          try {
            const res = await fetch('/api/processing/status');
            const data = await res.json();
            if (data.is_running) {
              if (waitingIntervalRef.current) {
                clearInterval(waitingIntervalRef.current);
                waitingIntervalRef.current = null;
              }
              navigate('/app');
            }
          } catch {
            /* keep polling */
          }
        }, 500);
      },
      onError: (err) => {
        setWaitingForRunning(false);
        if (err instanceof Error) setError(err.message);
      },
    });
  };

  const handleRestart = () => {
    setError('');
    setWaitingForRunning(true);
    setBatchSize(0);
    clearCache();
    clearSession.mutate(undefined, {
      onSuccess: () => {
        startProcessing.mutate(undefined, {
          onSuccess: () => {
            waitingIntervalRef.current = setInterval(async () => {
              try {
                const res = await fetch('/api/processing/status');
                const data = await res.json();
                if (data.is_running) {
                  if (waitingIntervalRef.current) {
                    clearInterval(waitingIntervalRef.current);
                    waitingIntervalRef.current = null;
                  }
                  navigate('/app');
                }
              } catch {
                /* keep polling */
              }
            }, 500);
          },
          onError: (err) => {
            setWaitingForRunning(false);
            if (err instanceof Error) setError(err.message);
          },
        });
      },
      onError: (err) => {
        setWaitingForRunning(false);
        if (err instanceof Error) setError(err.message);
      },
    });
  };

  const handleCsv = () => {
    setError('');
    exportCsv.mutate(undefined, {
      onError: (err) => {
        if (err instanceof Error) setError(err.message);
      },
    });
  };

  const busy = startProcessing.isPending || clearSession.isPending;

  const statsBlock = (
    <div className="space-y-2 text-sm mb-2">
      <div className="flex justify-between">
        <span className="text-gray-500">Wszystkie ankiety</span>
        <span className="font-medium">{stats.total}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-gray-500">Przeprocesowane</span>
        <span className="font-medium">
          {stats.processed} ({stats.processedPages} zdjęć)
        </span>
      </div>
      {remainingPages > 0 && (
        <div className="flex justify-between">
          <span className="text-gray-500">Pozostało do przeprocesowania</span>
          <span className="font-medium">{remainingPages} zdjęć</span>
        </div>
      )}
      <div className="flex justify-between">
        <span className="text-gray-500">Zweryfikowane</span>
        <span className="font-medium">{stats.verified}</span>
      </div>
      <div className="flex justify-between">
        <span className="text-gray-500">Błędy</span>
        <span className="font-medium">{stats.errors}</span>
      </div>
    </div>
  );

  const etaBlock = showEta && (
    <div className="flex justify-between text-sm mb-2">
      <span className="text-gray-500">{etaLabel}</span>
      <span className="font-medium">{etaText}</span>
    </div>
  );

  const primaryButtonClass =
    'w-full py-3 px-6 text-base bg-[var(--color-info)] text-white ' +
    'rounded-md hover:opacity-90 disabled:opacity-50 font-medium transition-opacity mt-6';

  return (
    <div className="flex items-center justify-center h-screen bg-gray-50">
      <div className="w-full max-w-sm bg-white rounded-lg shadow-md p-8">
        <h1 className="text-2xl font-bold text-center mb-1">AnkieterAI</h1>
        <p className="text-gray-500 text-center text-sm mb-6">
          System wprowadzania ankiet papierowych
        </p>

        {!waitingForRunning && stats.total === 0 && (
          <p className="text-center text-gray-500">Brak ankiet w katalogu.</p>
        )}

        {!waitingForRunning && !isCovered && !batchDone && remaining > 0 && (
          <>
            {stats.processed === 0 && (
              <p className="text-center text-gray-600 mb-6">
                Znaleziono {stats.total} ankiet. Rozpocznij analizę, aby wygenerować wyniki.
              </p>
            )}
            {statsBlock}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Liczba ankiet do przetworzenia
              </label>
              <input
                type="range"
                min={1}
                max={maxBatch}
                value={batchSize}
                onChange={(e) => setBatchSize(Number(e.target.value))}
                className="w-full accent-[var(--color-info)]"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>1</span>
                <span className="font-semibold text-gray-700">{batchSize}</span>
                <span>{maxBatch}</span>
              </div>
            </div>

            {showEta && (
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-500">Szacowany czas dla wybranej grupy ({batchSize} ankiet)</span>
                <span className="font-medium">{batchEtaText}</span>
              </div>
            )}
            {!showEta && (
              <div className="flex justify-between text-sm mb-2">
                <span className="text-gray-500">Szacowany czas</span>
                <span className="font-medium text-gray-400 italic">pojawi się po pierwszej ankiecie</span>
              </div>
            )}

            <button onClick={() => handleStart(batchSize)} disabled={busy} className={primaryButtonClass}>
              {startProcessing.isPending
                ? 'Rozpoczynanie...'
                : stats.processed > 0
                  ? 'Kontynuuj analizę'
                  : 'Rozpocznij analizę'}
            </button>
            {stats.processed > 0 && (
            <button
              onClick={() => navigate('/app')}
              className="w-full py-2 px-4 text-sm text-gray-700 bg-white border border-gray-300
                         rounded-md hover:bg-gray-50 font-medium transition-colors mt-3"
            >
              Przejdź do weryfikacji
            </button>
            )}
          </>
        )}

        {batchDone && (
          <>
            <h2 className="text-lg font-semibold text-center mb-2">
              Wybrana grupa przetworzona
            </h2>
            <p className="text-center text-gray-600 mb-4">
              Przetworzono {processingStatus?.batch_size ?? 0} ankiet.
              Pozostało {remaining} do przetworzenia.
            </p>
            {statsBlock}
            <div className="flex flex-col gap-3 mt-6">
              <div className="mb-2">
                <input
                  type="range"
                  min={1}
                  max={remaining}
                  value={batchSize}
                  onChange={(e) => setBatchSize(Number(e.target.value))}
                  className="w-full accent-[var(--color-info)]"
                />
                <div className="flex justify-between text-xs text-gray-400 mt-1">
                  <span>1</span>
                  <span className="font-semibold text-gray-700">{batchSize}</span>
                  <span>{remaining}</span>
                </div>
              </div>
              {showEta && (
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-500">Szacowany czas dla wybranej grupy ({batchSize} ankiet)</span>
                  <span className="font-medium">{batchEtaText}</span>
                </div>
              )}
              {!showEta && (
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-gray-500">Szacowany czas</span>
                  <span className="font-medium text-gray-400 italic">pojawi się po pierwszej ankiecie</span>
                </div>
              )}
              <button
                onClick={() => handleStart(batchSize)}
                disabled={busy}
                className="w-full py-3 px-6 text-base bg-[var(--color-info)] text-white
                           rounded-md hover:opacity-90 disabled:opacity-50 font-medium transition-opacity"
              >
                {busy ? 'Uruchamianie...' : 'Następna grupa'}
              </button>
              <button
                onClick={() => navigate('/app')}
                className="w-full py-2 px-4 text-sm text-gray-700 bg-white border border-gray-300
                           rounded-md hover:bg-gray-50 font-medium transition-colors"
              >
                Przejdź do weryfikacji
              </button>
            </div>
          </>
        )}

        {!waitingForRunning && isCovered && (
          <>
            <h2 className="text-lg font-semibold text-center mb-4">
              Wszystkie ankiety przeprocesowane
            </h2>
            {statsBlock}
            {etaBlock}
            <div className="flex flex-col gap-3 mt-6">
              {allVerified || readyCount === 0 ? (
                <button
                  onClick={() => navigate('/complete')}
                  className="w-full py-3 px-6 text-base bg-[var(--color-info)] text-white
                             rounded-md hover:opacity-90 font-medium transition-opacity"
                >
                  Pobierz wyniki
                </button>
              ) : (
                <button
                  onClick={() => navigate('/app')}
                  className="w-full py-3 px-6 text-base bg-[var(--color-info)] text-white
                             rounded-md hover:opacity-90 font-medium transition-opacity"
                >
                  Przejdź do weryfikacji
                </button>
              )}
              <div className="flex gap-3">
                <button
                  onClick={handleCsv}
                  disabled={exportCsv.isPending}
                  className="flex-1 py-2 px-4 text-sm text-gray-700 bg-white border border-gray-300
                             rounded-md hover:bg-gray-50 font-medium transition-colors
                             disabled:opacity-50"
                >
                  {exportCsv.isPending ? 'Pobieranie...' : 'Pobierz CSV'}
                </button>
                <button
                  onClick={handleRestart}
                  disabled={busy}
                  className="flex-1 py-2 px-4 text-sm text-gray-700 bg-white border border-gray-300
                             rounded-md hover:bg-gray-50 font-medium transition-colors
                             disabled:opacity-50"
                >
                  {busy ? 'Uruchamianie...' : 'Rozpocznij od nowa'}
                </button>
              </div>
            </div>
          </>
        )}

        {waitingForRunning && (
          <div className="text-center py-6">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[var(--color-info)] mx-auto mb-4" />
            <p className="text-gray-600 font-medium">Uruchamianie procesowania w tle...</p>
            <p className="text-gray-400 text-sm mt-1">Przygotowywanie ankiet do analizy</p>
          </div>
        )}

        {error && (
          <div className="mt-4 text-sm text-[var(--color-error)] bg-red-50 p-2 rounded">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
