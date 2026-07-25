import { useCallback, useMemo, useState } from 'react';
import type { FieldSpec } from '../../api/hooks';
import { useVerificationStore } from '../../store/verificationStore';
import { useSpaceShortcut } from '../../hooks/useSpaceShortcut';
import FieldRenderer from './FieldRenderer';
import ScaleTableGrid from './ScaleTableGrid';

interface DynamicFormProps {
  surveyId: number;
  fieldSpecs: FieldSpec[];
  aiResult: Record<string, unknown> | null;
  onSave: (values: Record<string, unknown>) => Promise<void>;
  onNextSurvey: () => void;
  disabled?: boolean;
}

function validateField(field: FieldSpec, value: unknown): string | undefined {
  const strVal = String(value ?? '').trim();
  if (strVal === '') return undefined;

  switch (field.kind) {
    case 'radio': {
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
  const setShowErrors = useVerificationStore((s) => s.setShowErrors);

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  const pageFields = useMemo(
    () => fieldSpecs.filter((f) => f.page === selectedPage),
    [fieldSpecs, selectedPage]
  );

  const isScalePage = useMemo(() => {
    if (pageFields.length === 0) return false;
    const firstChoices = pageFields[0].choices;
    if (!firstChoices || pageFields[0].kind !== 'radio') return false;
    return pageFields.every(
      (f) => f.kind === 'radio' &&
      f.choices?.length === firstChoices.length &&
      f.choices?.every((c, i) => c === firstChoices[i])
    );
  }, [pageFields]);

  const { mfisFields, healthFields } = useMemo(() => {
    if (selectedPage !== 4) return { mfisFields: [], healthFields: [] };
    const mfis = pageFields.filter((f) => f.name.startsWith('mfis_'));
    const health = pageFields.filter((f) => !f.name.startsWith('mfis_'));
    return { mfisFields: mfis, healthFields: health };
  }, [pageFields, selectedPage]);

  const mixedHealthSection = selectedPage === 4 && mfisFields.length > 0 && healthFields.length > 0;

  const allValues = useMemo(
    () => ({ ...(aiResult ?? {}), ...draftValues }),
    [aiResult, draftValues]
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

  const renderField = (field: FieldSpec) => (
    <div key={field.name} onBlur={() => handleBlur(field)}>
      <FieldRenderer
        field={field}
        value={getValue(field)}
        onChange={handleChange}
        error={errors[field.name]}
        showErrors={showErrors}
        allValues={allValues}
      />
    </div>
  );

  return (
    <div className="flex flex-col w-full h-full">
      <div className="flex-1 overflow-y-auto w-full px-3 py-1.5">
        {isScalePage && !mixedHealthSection && (
          <ScaleTableGrid
            fields={pageFields}
            values={allValues}
            onChange={handleChange}
          />
        )}

        {mixedHealthSection && (
          <div className="space-y-3">
            <ScaleTableGrid
              fields={mfisFields}
              values={allValues}
              onChange={handleChange}
            />
            <hr className="border-gray-200" />
            <div className={healthFields.length > 4 ? 'grid grid-cols-2 gap-x-3' : 'space-y-0'}>
              {healthFields.map(renderField)}
            </div>
          </div>
        )}

        {!isScalePage && !mixedHealthSection && (
          <div className={pageFields.length > 8 ? 'grid grid-cols-2 gap-x-3' : 'space-y-0'}>
            {pageFields.map(renderField)}
            {pageFields.length === 0 && (
              <p className="text-gray-400 text-center py-8">Brak pól na tej stronie</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
