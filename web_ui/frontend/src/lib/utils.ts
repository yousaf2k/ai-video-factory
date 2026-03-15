import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Convert internal filesystem paths to API-accessible URLs.
 * Handles both relative (output/projects/...) and absolute (C:/output/projects/...) paths.
 */
export function getMediaUrl(path: string | null, cacheBuster?: string | number): string {
  if (!path) return '';

  // If path already starts with /api/ or http, return it directly
  if (path.startsWith('/api/') || path.startsWith('http://') || path.startsWith('https://')) {
    if (cacheBuster) {
      const separator = path.includes('?') ? '&' : '?';
      return `${path}${separator}t=${cacheBuster}`;
    }
    return path;
  }

  // Normalize slashes to forward slashes
  let normalizedPath = path.replace(/\\/g, '/');

  // If it's an absolute path, find the 'output/projects/' part
  const outputIndex = normalizedPath.indexOf('output/projects/');
  if (outputIndex !== -1) {
    normalizedPath = normalizedPath.substring(outputIndex);
  }

  // Replace output/projects/ prefix with /api/projects/ for API routing
  let finalUrl = normalizedPath.replace(/^output\/projects\//, '/api/projects/').replace(/\\/g, '/');
  
  if (cacheBuster) {
    finalUrl += `?t=${cacheBuster}`;
  }
  
  return finalUrl;
}
