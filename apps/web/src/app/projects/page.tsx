'use client';

import { useQuery } from '@tanstack/react-query';
import Link from 'next/link';

import { projectsApi, type Project } from '@/lib/api';

export default function ProjectsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  });

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-semibold">Dự án</h1>
        <Link
          href="/projects/new"
          className="rounded-md bg-brand px-4 py-2 text-white shadow-sm hover:bg-brand-700"
        >
          Dự án mới
        </Link>
      </div>

      <div className="mt-8 space-y-3">
        {isLoading && <p className="text-gray-500">Đang tải…</p>}
        {error && <p className="text-severity-high">Không tải được danh sách dự án.</p>}
        {data?.length === 0 && (
          <p className="rounded-lg border border-dashed bg-white p-8 text-center text-gray-500">
            Chưa có dự án nào. Bấm "Dự án mới" để bắt đầu.
          </p>
        )}
        {data?.map((p: Project) => (
          <Link
            key={p.id}
            href={`/projects/${p.id}`}
            className="block rounded-lg border bg-white p-5 shadow-sm transition hover:border-brand"
          >
            <div className="font-medium">{p.name}</div>
            <div className="mt-1 text-sm text-gray-500">
              {p.building_type} · {new Date(p.created_at).toLocaleDateString('vi-VN')}
            </div>
          </Link>
        ))}
      </div>
    </main>
  );
}
