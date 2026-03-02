import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Convert internal filesystem paths to API-accessible URLs.
 * Handles both relative (output/sessions/...) and absolute (C:/output/sessions/...) paths.
 */
export function getMediaUrl(path: string | null): string {
  if (!path) return '';

  // Normalize slashes to forward slashes
  let normalizedPath = path.replace(/\\/g, '/');

  // If it's an absolute path, find the 'output/sessions/' part
  const outputIndex = normalizedPath.indexOf('output/sessions/');
  if (outputIndex !== -1) {
    normalizedPath = normalizedPath.substring(outputIndex);
  }

  // Replace output/sessions/ prefix with /api/sessions/ for API routing
  return normalizedPath.replace(/^output\/sessions\//, '/api/sessions/').replace(/\\/g, '/');
}
