import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiFetch } from './client';

export interface FieldSpec {
  name: string;
  label: string;
  page: number;
  kind: 'select' | 'text' | 'number';
  choices: string[] | null;
  min: number | null;
  max: number | null;
  csv_header: string;
}

export interface SurveyListItem {
  id: number;
  files: string[];
  status: 'queued' | 'processing' | 'ready' | 'error' | 'verified';
}

export interface ProcessingStatus {
  total: number;
  processed: number;
  errors: number;
  current_survey_id: number | null;
  current_page: number | null;
  current_stage: string | null;
  eta_seconds: number | null;
  is_running: boolean;
}

export interface SurveyResult {
  id: number;
  status: string;
  result: Record<string, unknown> | null;
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
    refetchInterval: 2000,
  });
}

export function useProcessingStatus() {
  return useQuery({
    queryKey: ['processing-status'],
    queryFn: () => apiFetch<ProcessingStatus>('/api/processing/status'),
    refetchInterval: 2000,
  });
}

export function useSurveyResult(surveyId: number | null) {
  return useQuery({
    queryKey: ['survey-result', surveyId],
    queryFn: () => apiFetch<SurveyResult>(`/api/surveys/${surveyId}/result`),
    enabled: surveyId !== null,
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
    mutationFn: () =>
      apiFetch<{ status: string; total: number }>('/api/processing/start', {
        method: 'POST',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['processing-status'] });
    },
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

export function surveyImageUrl(surveyId: number, page: number): string {
  return `/api/surveys/${surveyId}/pages/${page}/image`;
}
