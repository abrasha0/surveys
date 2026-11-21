import { useEffect, useRef, useState } from 'react';
import { useQuery, useMutation, useQueryClient, keepPreviousData } from '@tanstack/react-query';
import { SURVEY_PAGE_COUNT } from '../constants';
import { apiFetch } from './client';

export interface FieldSpec {
  name: string;
  label: string;
  page: number;
  kind: 'radio' | 'text' | 'number';
  choices: string[] | null;
  min: number | null;
  max: number | null;
  csv_header: string;
  conditional: string | null;
}

export interface SurveyListItem {
  id: number;
  files: string[];
  status: 'queued' | 'processing' | 'ready' | 'error' | 'verified';
  can_edit: boolean;
}

export interface ProcessingStatus {
  total: number;
  processed: number;
  errors: number;
  total_pages: number;
  processed_pages: number;
  current_survey_id: number | null;
  current_page: number | null;
  current_stage: string | null;
  eta_seconds: number | null;
  is_running: boolean;
  batch_size: number;
  batch_remaining: number | null;
  batch_processed: number;
  batch_total_pages: number;
  batch_processed_pages: number;
  batch_eta_seconds: number | null;
  current_survey_pages: number;
  current_survey_batch_idx: number | null;
}

export interface SurveyResult {
  id: number;
  status: string;
  result: Record<string, unknown> | null;
  draft: Record<string, unknown> | null;
  error: string | null;
}

export function useFieldSpecs() {
  return useQuery({
    queryKey: ['field-specs'],
    queryFn: () => apiFetch<FieldSpec[]>('/api/field-specs'),
    staleTime: Infinity,
  });
}

export function useSurveys() {
  return useQuery({
    queryKey: ['surveys'],
    queryFn: () => apiFetch<SurveyListItem[]>('/api/surveys'),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 2000;
      const hasActive = data.some((s) => s.status === 'queued' || s.status === 'processing');
      return hasActive ? 2000 : false;
    },
  });
}

export function useProcessingStatus() {
  return useQuery({
    queryKey: ['processing-status'],
    queryFn: () => apiFetch<ProcessingStatus>('/api/processing/status'),
    refetchInterval: (query) => {
      const data = query.state.data as ProcessingStatus | undefined;
      return data?.is_running ? 2000 : false;
    },
  });
}

export function useSurveyImages(surveyId: number | null, surveys?: SurveyListItem[]) {
  const [data, setData] = useState<Record<number, string | null> | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefetching, setIsRefetching] = useState(false);
  const dataRef = useRef<Record<number, string | null> | null>(null);
  const cacheBustRef = useRef(Date.now());
  const imageCache = useRef<Map<number, Record<number, string | null>>>(new Map());
  const lastStatuses = useRef<Map<number, string>>(new Map());
  const MAX_CACHE_SIZE = 5;

  dataRef.current = data;

  useEffect(() => {
    const cache = imageCache.current;
    const current = dataRef;
    return () => {
      cache.forEach((map) => {
        Object.values(map).forEach((url) => {
          if (url) URL.revokeObjectURL(url);
        });
      });
      cache.clear();
      if (current.current) {
        Object.values(current.current).forEach((url) => {
          if (url) URL.revokeObjectURL(url);
        });
      }
    };
  }, []);

  useEffect(() => {
    if (surveyId === null) return;

    if (imageCache.current.has(surveyId)) {
      const cached = imageCache.current.get(surveyId)!;
      setData(cached);
      setIsLoading(false);
      setIsRefetching(false);
      return;
    }

    const wasEmpty = dataRef.current === null;
    if (wasEmpty) setIsLoading(true);
    else setIsRefetching(true);
    let cancelled = false;

    const load = async () => {
      cacheBustRef.current = Date.now();
      const pages = Array.from({ length: SURVEY_PAGE_COUNT }, (_, i) => i);
      const entries = await Promise.all(
        pages.map(async (page) => {
          try {
            const url = `/api/surveys/${surveyId}/pages/${page}/image?_=${cacheBustRef.current}`;
            const res = await fetch(url, { credentials: 'include' });
            if (!res.ok) return { page, url: null as string | null };
            const blob = await res.blob();
            return { page, url: URL.createObjectURL(blob) };
          } catch {
            return { page, url: null as string | null };
          }
        })
      );

      if (cancelled) {
        entries.forEach((e) => { if (e.url) URL.revokeObjectURL(e.url); });
        return;
      }

      const map: Record<number, string | null> = {};
      entries.forEach((e) => { map[e.page] = e.url; });

      const isComplete = Object.values(map).every((v) => v !== null);
      if (isComplete) {
        if (imageCache.current.size >= MAX_CACHE_SIZE) {
          const oldestKey = imageCache.current.keys().next().value;
          if (oldestKey !== undefined) {
            const evicted = imageCache.current.get(oldestKey);
            if (evicted) {
              Object.values(evicted).forEach((url) => { if (url) URL.revokeObjectURL(url); });
            }
            imageCache.current.delete(oldestKey);
          }
        }
        imageCache.current.set(surveyId, map);
      }

      if (wasEmpty) setIsLoading(false);
      setIsRefetching(false);
      setData(map);
    };

    load();

    return () => {
      cancelled = true;
    };
  }, [surveyId]);

  useEffect(() => {
    if (!surveys) return;
    for (const survey of surveys) {
      const prevStatus = lastStatuses.current.get(survey.id);
      if (prevStatus !== undefined && prevStatus !== survey.status) {
        if (survey.id !== surveyId) {
          const cached = imageCache.current.get(survey.id);
          if (cached) {
            Object.values(cached).forEach((url) => { if (url) URL.revokeObjectURL(url); });
            imageCache.current.delete(survey.id);
          }
        }
      }
      lastStatuses.current.set(survey.id, survey.status);
    }
  }, [surveys, surveyId]);

  return { data, isLoading, isRefetching };
}

export function useSurveyResult(surveyId: number | null) {
  return useQuery({
    queryKey: ['survey-result', surveyId],
    queryFn: () => apiFetch<SurveyResult>(`/api/surveys/${surveyId}/result`),
    enabled: surveyId !== null,
    placeholderData: keepPreviousData,
  });
}

export function useLogin() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (password: string) =>
      apiFetch<{ status: string }>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ password }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['surveys'] });
    },
  });
}

export function useStartProcessing() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (batchSize?: number) =>
      apiFetch<{ status: string; total: number; batch_size: number }>(
        '/api/processing/start',
        {
          method: 'POST',
          body: JSON.stringify({ batch_size: batchSize ?? 0 }),
        }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['surveys'] });
      queryClient.invalidateQueries({ queryKey: ['processing-status'] });
    },
  });
}

export function useUnverifySurvey() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (surveyId: number) =>
      apiFetch<{ status: string; survey_id: number }>(
        `/api/surveys/${surveyId}/unverify`,
        { method: 'POST' }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['surveys'] });
    },
  });
}

export function useFinalizeSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<{ status: string; csv_path: string; total_verified: number; total_errors: number }>(
        '/api/session/finalize',
        { method: 'POST' }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['surveys'] });
    },
  });
}

export function useSaveDraft() {
  return useMutation({
    mutationFn: ({ surveyId, values }: { surveyId: number; values: Record<string, unknown> }) =>
      apiFetch<{ status: string }>(
        `/api/surveys/${surveyId}/draft`,
        {
          method: 'POST',
          body: JSON.stringify({ values }),
        }
      ),
  });
}

export function useSaveSurvey() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      surveyId,
      values,
      force = false,
    }: {
      surveyId: number;
      values: Record<string, unknown>;
      force?: boolean;
    }) =>
      apiFetch<{ status: string; survey_id: number }>(
        `/api/surveys/${surveyId}/save`,
        {
          method: 'POST',
          body: JSON.stringify({ values, force }),
        }
      ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['surveys'] });
    },
  });
}

export function useClearSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      apiFetch<{ status: string }>('/api/session/clear', { method: 'POST' }),
    onSettled: () => {
      queryClient.clear();
    },
  });
}

export function useExportCsv() {
  return useMutation({
    mutationFn: async () => {
      const res = await fetch('/api/surveys/export/csv', { credentials: 'include' });
      if (!res.ok) throw new Error('Nie udało się pobrać pliku CSV');
      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'ankiety_wyniki.csv';
      a.click();
      window.URL.revokeObjectURL(url);
    },
  });
}
