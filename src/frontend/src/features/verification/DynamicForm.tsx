import { forwardRef, useCallback, useImperativeHandle, useMemo, useState } from 'react';
import { ApiError } from '../../api/client';
import type { FieldSpec } from '../../api/hooks';
import { DEFAULT_SURVEY_UI, useVerificationStore } from '../../store/verificationStore';
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

/** Server-side validation errors from a 422 response of the save endpoint. */
function serverValidationErrors(err: unknown): Record<string, string> | null {
  if (!(err instanceof ApiError) || err.status !== 422) return null;
  const detail = err.detail;
  if (!detail || typeof detail !== 'object' || !('errors' in detail)) return null;
  const errors = detail.errors;
  if (!errors || typeof errors !== 'object') return null;
  return Object.fromEntries(Object.entries(errors).map(([name, msg]) => [name, String(msg)]));
}

/** Splits a field condition such as "p5_forma=Inne" into the controlling field and the expected answer. */
function parseCondition(condition: string): { field: string; value: string } {
  const sep = condition.indexOf('=');
  return { field: condition.slice(0, sep), value: condition.slice(sep + 1) };
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
  const surveyUI = useVerificationStore((s) => s.surveysUI[surveyId] ?? DEFAULT_SURVEY_UI);
  const { selectedPage, showErrors, draftValues } = surveyUI;
  const updateDraft = useVerificationStore((s) => s.updateDraft);
  const persistDraft = useVerificationStore((s) => s.persistDraft);
  const setShowErrors = useVerificationStore((s) => s.setShowErrors);

  const [errors, setErrors] = useState<Record<string, string>>({});
  const [saveError, setSaveError] = useState('');
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

  const specByName = useMemo(() => new Map(fieldSpecs.map((f) => [f.name, f])), [fieldSpecs]);

  const conditionMet = useCallback(
    (field: FieldSpec) => {
      if (!field.conditional) return true;
      const { field: controlling, value } = parseCondition(field.conditional);
      const current = String(allValues[controlling] ?? '').trim().toLowerCase();
      return current === value.trim().toLowerCase();
    },
    [allValues]
  );

  // A conditional field is hidden while its condition is not met, unless it already holds
  // a value: hiding it would silently keep text the verifier cannot see.
  const isVisible = useCallback(
    (field: FieldSpec) => conditionMet(field) || String(getValue(field)).trim() !== '',
    [conditionMet, getValue]
  );

  const conditionHint = useCallback(
    (field: FieldSpec): string | undefined => {
      if (!field.conditional || conditionMet(field)) return undefined;
      const { field: controlling, value } = parseCondition(field.conditional);
      const label = specByName.get(controlling)?.label ?? controlling;
      return `Pole wypełnione, choć w pytaniu „${label}” nie zaznaczono „${value}”.`;
    },
    [conditionMet, specByName]
  );

  const handleChange = useCallback(
    (name: string, value: unknown) => {
      if (readOnly) return;
      setSaveError('');
      updateDraft(surveyId, { [name]: value });
      persistDraft(surveyId);
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
    [surveyId, fieldSpecs, updateDraft, persistDraft, readOnly]
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

    setSaveError('');

    if (Object.keys(allErrors).length > 0) return;

    setSaving(true);
    try {
      await onSave({ ...allValues });
      setErrors({});
      setShowErrors(surveyId, false);
      onNextSurvey();
    } catch (err) {
      const serverErrors = serverValidationErrors(err);
      if (serverErrors) setErrors(serverErrors);
      else setSaveError(err instanceof Error ? err.message : 'Nie udało się zapisać ankiety');
    } finally {
      setSaving(false);
    }
  }, [fieldSpecs, allValues, onSave, surveyId, setShowErrors, onNextSurvey]);

  const handleForceSave = useCallback(async () => {
    setSaving(true);
    setSaveError('');
    try {
      await onForceSave({ ...allValues });
      setErrors({});
      setShowErrors(surveyId, false);
      onNextSurvey();
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : 'Nie udało się zapisać ankiety');
    } finally {
      setSaving(false);
    }
  }, [allValues, onForceSave, surveyId, setShowErrors, onNextSurvey]);

  const errorCount = showErrors ? Object.keys(errors).length : 0;
  const errorPages = useMemo(() => {
    const pages = new Set<number>();
    for (const name of Object.keys(errors)) {
      const page = specByName.get(name)?.page;
      if (page !== undefined) pages.add(page + 1);
    }
    return [...pages].sort((a, b) => a - b);
  }, [errors, specByName]);

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
        hint={conditionHint(field)}
      />
    </div>
  );

  return (
    <div className="flex flex-col w-full h-full">
      {!readOnly && (errorCount > 0 || saveError) && (
        <div className="flex items-center justify-between gap-3 px-3 py-2 text-xs bg-red-50 border-b border-red-200 text-red-800">
          <span>
            {errorCount > 0
              ? `Formularz zawiera błędy (${errorCount})` +
                (errorPages.length > 0 ? ` na stronach: ${errorPages.join(', ')}` : '') +
                '. Popraw je albo zatwierdź ankietę mimo błędów.'
              : saveError}
          </span>
          {errorCount > 0 && (
            <button
              type="button"
              onClick={handleForceSave}
              disabled={disabled || saving}
              className="shrink-0 px-3 py-1.5 font-medium text-white bg-[var(--color-warning)] rounded hover:opacity-90 disabled:opacity-50"
            >
              Zatwierdź mimo błędów
            </button>
          )}
        </div>
      )}
      <div className="flex-1 overflow-y-auto w-full px-3 py-1.5">
        {layout === 'columns-3' && (
          <div className="columns-3 gap-x-5">
            {pageFields.filter(isVisible).map((field) => (
              <div key={field.name} className="break-inside-avoid mb-2.5" onBlur={() => handleBlur(field)}>
                <FieldRenderer
                  field={field}
                  value={getValue(field)}
                  onChange={handleChange}
                  error={errors[field.name]}
                  showErrors={showErrors}
                  disabled={readOnly}
                  hint={conditionHint(field)}
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
            disabled={readOnly}
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
              disabled={readOnly}
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
                    <div>{jakie && isVisible(jakie) && renderField(jakie)}</div>
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
