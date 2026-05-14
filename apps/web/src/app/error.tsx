'use client';

import { useEffect } from 'react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col items-center justify-center px-6 text-center">
      <h1 className="text-2xl font-semibold">Đã xảy ra lỗi</h1>
      <p className="mt-2 text-gray-600">
        {error.message || 'Lỗi không xác định.'}
      </p>
      {error.digest && (
        <p className="mt-1 font-mono text-xs text-gray-400">id: {error.digest}</p>
      )}
      <button
        type="button"
        onClick={reset}
        className="mt-6 rounded-md bg-brand px-4 py-2 text-white hover:bg-brand-700"
      >
        Thử lại
      </button>
    </main>
  );
}
