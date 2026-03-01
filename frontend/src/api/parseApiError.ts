import type { AxiosError } from 'axios';

/**
 * Parse DRF validation errors into a user-friendly string.
 * Handles three patterns:
 *   1. field-level: { field_name: ["error1", "error2"] }
 *   2. non_field_errors: { non_field_errors: ["..."] }
 *   3. detail string: { detail: "..." }
 */
export function parseApiError(error: unknown): string {
  const axiosErr = error as AxiosError<Record<string, unknown>>;
  const data = axiosErr?.response?.data;

  if (!data || typeof data !== 'object') {
    return (error as Error)?.message || 'An unexpected error occurred';
  }

  // { detail: "string" }
  if (typeof data.detail === 'string') {
    return data.detail;
  }

  const messages: string[] = [];

  for (const [key, value] of Object.entries(data)) {
    if (Array.isArray(value)) {
      const joined = value.join(', ');
      if (key === 'non_field_errors') {
        messages.push(joined);
      } else {
        messages.push(`${key}: ${joined}`);
      }
    } else if (typeof value === 'string') {
      messages.push(key === 'detail' ? value : `${key}: ${value}`);
    }
  }

  return messages.length > 0 ? messages.join('\n') : 'An unexpected error occurred';
}
