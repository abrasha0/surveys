import { useCallback, useMemo, useState } from 'react';
import type { FieldSpec } from '../../api/hooks';
import { useVerificationStore } from '../../store/verificationStore';
import { useSpaceShortcut } from '../../hooks/useSpaceShortcut';
import FieldRenderer from './FieldRenderer';

interface DynamicFormProps {
  surveyId: number;
  fieldSpecs: FieldSpec[];
  aiResult: Record<string, unknown> | null;
  onSave: (values: Record<string, unknown>) => Promise<void>;
  onNextSurvey: () => void;
  disabled?: boolean;
}

const TOTAL_PAGES = 5;

function validateField(field: FieldSpec, value: unknown): string | undefined {
  const strVal = String(value ?? '').trim();
  if (strVal === '') return undefined;

  switch (field.kind) {
    case 'select': {
      if (!field.choices || field.choices.length === 0) return undefined;
      const match = field.choices.some((c) => c.toLowerCase() === strVal.toLowerCase());
      if (!match) return `Wybierz poprawną wartość z listy`;
      return undefined;
    }
    case 'number': {
      const num = Number(strVal);
      if (isNaN(num)) return 'Wprowadź liczbę całkowitą';
      if (!Number.isInteger(num)) return 'Wprowadź liczbę całkowitą';
      if (field.min != null && num < field.min) return `Minimalna wartość: ${field.min}`;
      if (field.max != null && num > field.max) return `Maksymalna wartość: ${field.max}`;
      return undefined;
    }
    case 'text':
      return undefined;
    default:
      return undefined;
  }
}

function validateFields(
  fieldSpecs: FieldSpec[],
  values: Record<string, unknown>
): Record<string, string> {
  const errors: Record<string, string> = {};
  for (const field of fieldSpecs) {
    const error = validateField(field, values[field.name]);
    if (error) errors[field.name] = error;
  }
  return errors;
}

export default function DynamicForm({
  surveyId,
  fieldSpecs,
  aiResult,
  onSave,
  onNextSurvey,
  disabled = false,
}: DynamicFormProps) {
  const selectedPage = useVerificationStore((s) => s.getSurveyUI(surveyId).selectedPage);
  const showErrors = useVerificationStore((s) => s.getSurveyUI(surveyId).showErrors);
  const draftValues = useVerificationStore((s) => s.getSurveyUI(surveyId).draftValues);
  const updateDraft = useVerificationStore((s) => s.updateDraft);
  const saveDraft = useVerificationStore((s) => s.saveDraft);
  const clearDraft = useVerificationStore((s) => s.clearDraft);
  const setSelectedPage = useVerificationStore((s) => s.setSelectedPage);
  const setShowErrors = useVerificationStore((s) => s.setShowErrors);

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  const pageFields = useMemo(
    () => fieldSpecs.filter((f) => f.page === selectedPage),
    [fieldSpecs, selectedPage]
  );

  const getValue = useCallback(
    (field: FieldSpec) => draftValues[field.name] ?? aiResult?.[field.name] ?? '',
    [draftValues, aiResult]
  );

  const handleChange = useCallback(
    (name: string, value: unknown) => {
      updateDraft(surveyId, { [name]: value });
      saveDraft(surveyId);
      const field = fieldSpecs.find((f) => f.name === name);
      if (field) {
        const error = validateField(field, value);
        setErrors((prev) => {
          const next = { ...prev };
          if (error) next[name] = error;
          else delete next[name];
          return next;
        });
      }
    },
    [surveyId, fieldSpecs, updateDraft, saveDraft]
  );

  const handleBlur = useCallback(
    (field: FieldSpec) => {
      const error = validateField(field, draftValues[field.name]);
      setErrors((prev) => {
        const next = { ...prev };
        if (error) next[field.name] = error;
        else delete next[field.name];
        return next;
      });
    },
    [draftValues]
  );

  const handleSave = useCallback(async () => {
    const allErrors = validateFields(fieldSpecs, draftValues);
    setErrors(allErrors);
    setShowErrors(surveyId, true);

    if (Object.keys(allErrors).length > 0) return;

    setSaving(true);
    try {
      await onSave({ ...draftValues });
      clearDraft(surveyId);
      setErrors({});
      setShowErrors(surveyId, false);
      onNextSurvey();
    } finally {
      setSaving(false);
    }
  }, [fieldSpecs, draftValues, onSave, clearDraft, surveyId, setShowErrors, onNextSurvey]);

  useSpaceShortcut(!disabled && !saving, handleSave);

  const prevPage = () => setSelectedPage(surveyId, selectedPage - 1);
  const nextPage = () => setSelectedPage(surveyId, selectedPage + 1);

  return (
    <div className="flex flex-col w-full h-full">
      <div className={`flex-1 overflow-y-auto w-full px-3 py-1.5 ${pageFields.length > 8 ? 'grid grid-cols-2 gap-x-3' : 'space-y-0'}`}>
        {pageFields.map((field) => (
          <div key={field.name} onBlur={() => handleBlur(field)}>
            <FieldRenderer
              field={field}
              value={getValue(field)}
              onChange={handleChange}
              error={errors[field.name]}
              showErrors={showErrors}
            />
          </div>
        ))}
        {pageFields.length === 0 && (
          <p className="text-gray-400 text-center py-8">Brak pól na tej stronie</p>
        )}
      </div>

      <div className="flex items-center justify-between border-t border-gray-200 bg-white px-3 py-2">
        <button
          onClick={prevPage}
          disabled={selectedPage === 0}
          className="px-3 py-1.5 text-xs font-medium text-gray-700 bg-white border border-gray-300 rounded hover:bg-gray-50 disabled:text-gray-300 disabled:cursor-not-allowed"
        >
          ◀ Poprzednia strona
        </button>

        <span className="text-xs text-gray-500">
          Strona {selectedPage + 1} z {TOTAL_PAGES}
        </span>

        {selectedPage < TOTAL_PAGES - 1 ? (
          <button
            onClick={nextPage}
            className="px-3 py-1.5 text-xs font-medium text-white bg-[var(--color-info)] rounded hover:opacity-90"
          >
            Następna strona ▶
          </button>
        ) : (
          <button
            onClick={handleSave}
            disabled={disabled || saving}
            className="px-3 py-1.5 text-xs font-medium text-white bg-[var(--color-success)] rounded hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? 'Zapisywanie...' : 'Zatwierdź ankietę'}
          </button>
        )}
      </div>
    </div>
  );
}
