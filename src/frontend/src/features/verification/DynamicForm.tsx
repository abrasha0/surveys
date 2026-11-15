import { forwardRef, useCallback, useImperativeHandle, useMemo, useState } from 'react';
import type { FieldSpec } from '../../api/hooks';
import { useVerificationStore } from '../../store/verificationStore';
import { useSpaceShortcut } from '../../hooks/useSpaceShortcut';
import FieldRenderer from './FieldRenderer';
import ScaleTableGrid from './ScaleTableGrid';

type LayoutType = 'columns-3' | 'table' | 'grid-2' | 'table+health';

const PAGE_LAYOUT: Record<number, LayoutType> = {
  0: 'columns-3',
  1: 'grid-2',
  2: 'table',
  3: 'table+health',
  4: 'table',
};

interface DynamicFormProps {
  surveyId: number;
  fieldSpecs: FieldSpec[];
  aiResult: Record<string, unknown> | null;
  onSave: (values: Record<string, unknown>) => Promise<void>;
  onForceSave: (values: Record<string, unknown>) => Promise<void>;
  onNextSurvey: () => void;
  disabled?: boolean;
  readOnly?: boolean;
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

const DynamicForm = forwardRef<{ save: () => void; forceSave: () => void }, DynamicFormProps>(function DynamicForm({
  surveyId,
  fieldSpecs,
  aiResult,
  onSave,
  onForceSave,
  onNextSurvey,
  disabled = false,
  readOnly = false,
}, ref) {
  const selectedPage = useVerificationStore((s) => s.getSurveyUI(surveyId).selectedPage);
  const showErrors = useVerificationStore((s) => s.getSurveyUI(surveyId).showErrors);
  const draftValues = useVerificationStore((s) => s.getSurveyUI(surveyId).draftValues);
  const updateDraft = useVerificationStore((s) => s.updateDraft);
  const saveDraft = useVerificationStore((s) => s.saveDraft);
  const setShowErrors = useVerificationStore((s) => s.setShowErrors);

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);

  const pageFields = useMemo(
    () => fieldSpecs.filter((f) => f.page === selectedPage),
    [fieldSpecs, selectedPage]
  );

  const { mfisFields, healthFields } = useMemo(() => {
    if (selectedPage !== 3) return { mfisFields: [], healthFields: [] };
    const mfis = pageFields.filter((f) => f.name.startsWith('mfis_'));
    const health = pageFields.filter((f) => !f.name.startsWith('mfis_'));
    return { mfisFields: mfis, healthFields: health };
  }, [pageFields, selectedPage]);

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
      if (readOnly) return;
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
    [surveyId, fieldSpecs, updateDraft, saveDraft, readOnly]
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
    const allErrors = validateFields(fieldSpecs, allValues);
    setErrors(allErrors);
    setShowErrors(surveyId, true);

    if (Object.keys(allErrors).length > 0) return;

    setSaving(true);
    try {
      await onSave({ ...allValues });
      setErrors({});
      setShowErrors(surveyId, false);
      onNextSurvey();
    } finally {
      setSaving(false);
    }
  }, [fieldSpecs, allValues, onSave, surveyId, setShowErrors, onNextSurvey]);

  const handleForceSave = useCallback(async () => {
    setSaving(true);
    setShowErrors(surveyId, false);
    try {
      await onForceSave({ ...allValues, ...draftValues });
      setErrors({});
      setShowErrors(surveyId, false);
      onNextSurvey();
    } finally {
      setSaving(false);
    }
  }, [allValues, draftValues, onForceSave, surveyId, setShowErrors, onNextSurvey]);

  useImperativeHandle(ref, () => ({ save: handleSave, forceSave: handleForceSave }), [handleSave, handleForceSave]);

  useSpaceShortcut(!disabled && !saving && !readOnly, handleSave);

  const layout = PAGE_LAYOUT[selectedPage] ?? 'grid-2';

  const renderField = (field: FieldSpec) => (
    <div key={field.name} onBlur={() => handleBlur(field)}>
      <FieldRenderer
        field={field}
        value={getValue(field)}
        onChange={handleChange}
        error={errors[field.name]}
        showErrors={showErrors}
        disabled={readOnly}
      />
    </div>
  );

  return (
    <div className="flex flex-col w-full h-full">
      <div className="flex-1 overflow-y-auto w-full px-3 py-1.5">
        {layout === 'columns-3' && (
          <div className="columns-3 gap-x-5">
            {pageFields.map((field) => (
              <div key={field.name} className="break-inside-avoid mb-2.5" onBlur={() => handleBlur(field)}>
                <FieldRenderer
                  field={field}
                  value={getValue(field)}
                  onChange={handleChange}
                  error={errors[field.name]}
                  showErrors={showErrors}
                />
              </div>
            ))}
          </div>
        )}

        {layout === 'table' && (
          <ScaleTableGrid
            fields={pageFields}
            values={allValues}
            onChange={handleChange}
          />
        )}

        {layout === 'grid-2' && (
          <div className="grid grid-cols-2 gap-x-8">
            <div className="space-y-2">
              {pageFields.slice(0, 4).map(renderField)}
            </div>
            <div className="space-y-2">
              {pageFields.slice(4, 8).map(renderField)}
            </div>
          </div>
        )}

        {layout === 'table+health' && (
          <div>
            <ScaleTableGrid
              fields={mfisFields}
              values={allValues}
              onChange={handleChange}
            />
            <hr className="border-gray-200 mb-6" />
            {(() => {
              const anemia = healthFields.find((f) => f.name === 'choroba_anemia');
              const tarczyca = healthFields.find((f) => f.name === 'choroba_tarczyca');
              const jakie = healthFields.find((f) => f.name === 'tarczyca_jakie');
              const inne = healthFields.find((f) => f.name === 'choroba_inne');
              return (
                <div className="space-y-2.5">
                  <div className="grid grid-cols-2 gap-x-8">
                    <div>{anemia && renderField(anemia)}</div>
                    <div />
                  </div>
                  <div className="grid grid-cols-2 gap-x-8">
                    <div>{tarczyca && renderField(tarczyca)}</div>
                    <div>{jakie && renderField(jakie)}</div>
                  </div>
                  {inne && renderField(inne)}
                </div>
              );
            })()}
          </div>
        )}

        {pageFields.length === 0 && (
          <p className="text-gray-400 text-center py-8">Brak pól na tej stronie</p>
        )}
      </div>
    </div>
  );
});

export default DynamicForm;
