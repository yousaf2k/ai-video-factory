'use client';

import { useEffect } from 'react';

interface ImageLightboxProps {
  /** Full image URL to display; null keeps the viewer hidden. */
  src: string | null;
  alt?: string;
  onClose: () => void;
}

/** Fullscreen image viewer — click anywhere (or press Escape) to close. */
export function ImageLightbox({ src, alt = '', onClose }: ImageLightboxProps) {
  useEffect(() => {
    if (!src) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [src, onClose]);

  if (!src) return null;

  return (
    <div
      className="fixed inset-0 z-[100] bg-black/90 flex items-center justify-center p-4 cursor-zoom-out"
      onClick={onClose}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={src}
        alt={alt}
        className="max-w-full max-h-full object-contain rounded shadow-2xl"
      />
    </div>
  );
}
