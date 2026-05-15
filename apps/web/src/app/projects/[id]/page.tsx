'use client';

import Link from 'next/link';

export default function ProjectDetailPage({ params }: { params: { id: string } }) {
  return (
    <main className="mx-auto max-w-4xl px-6 py-12">
      <Link href="/projects" className="text-sm text-gray-600 hover:underline">
        ← Quay lại danh sách dự án
      </Link>
      <h1 className="mt-4 text-3xl font-semibold">Chi tiết dự án</h1>
      <p className="mt-2 text-sm text-gray-500 font-mono">{params.id}</p>

      <div className="mt-8 rounded-lg border border-dashed bg-white p-8 text-center text-gray-500">
        Trang chi tiết dự án đang được phát triển. Sử dụng API trực tiếp:
        <pre className="mt-3 text-left text-xs font-mono text-gray-700">
          GET /projects/{params.id}
          {'\n'}POST /uploads
          {'\n'}POST /compliance/runs
        </pre>
      </div>
    </main>
  );
}
