import Link from 'next/link';

export default function NotFound() {
  return (
    <main className="mx-auto flex min-h-screen max-w-xl flex-col items-center justify-center px-6 text-center">
      <h1 className="text-3xl font-semibold">404</h1>
      <p className="mt-2 text-gray-600">Trang bạn tìm không tồn tại.</p>
      <Link href="/" className="mt-6 text-brand hover:underline">
        ← Về trang chủ
      </Link>
    </main>
  );
}
