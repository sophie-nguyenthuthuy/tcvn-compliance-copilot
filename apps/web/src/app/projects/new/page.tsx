'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { projectsApi } from '../../../lib/api';

const BUILDING_TYPES = [
  { value: 'residential', label: 'Nhà ở' },
  { value: 'apartment', label: 'Chung cư' },
  { value: 'office', label: 'Văn phòng' },
  { value: 'commercial', label: 'Thương mại' },
  { value: 'industrial', label: 'Công nghiệp' },
  { value: 'educational', label: 'Giáo dục' },
  { value: 'healthcare', label: 'Y tế' },
  { value: 'mixed_use', label: 'Hỗn hợp' },
  { value: 'other', label: 'Khác' },
] as const;

export default function NewProjectPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [buildingType, setBuildingType] = useState<string>('office');
  const [description, setDescription] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await projectsApi.create({
        name: name.trim(),
        building_type: buildingType,
        description: description.trim() || undefined,
      });
      router.push('/projects');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Không tạo được dự án.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="text-3xl font-semibold">Dự án mới</h1>
      <p className="mt-2 text-gray-600">Khai báo thông tin cơ bản để bắt đầu soát chiếu.</p>

      <form onSubmit={onSubmit} className="mt-8 space-y-5 rounded-lg border bg-white p-6 shadow-sm">
        <div>
          <label htmlFor="name" className="block text-sm font-medium">
            Tên dự án
          </label>
          <input
            id="name"
            type="text"
            required
            minLength={1}
            maxLength={255}
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
          />
        </div>

        <div>
          <label htmlFor="building_type" className="block text-sm font-medium">
            Loại công trình
          </label>
          <select
            id="building_type"
            value={buildingType}
            onChange={(e) => setBuildingType(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
          >
            {BUILDING_TYPES.map((b) => (
              <option key={b.value} value={b.value}>
                {b.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label htmlFor="description" className="block text-sm font-medium">
            Mô tả
          </label>
          <textarea
            id="description"
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-brand focus:outline-none focus:ring-1 focus:ring-brand"
          />
        </div>

        {error && <p className="text-sm text-severity-high">{error}</p>}

        <div className="flex items-center justify-end gap-3">
          <Link href="/projects" className="text-sm text-gray-600 hover:underline">
            Huỷ
          </Link>
          <button
            type="submit"
            disabled={submitting || !name.trim()}
            className="rounded-md bg-brand px-4 py-2 text-white shadow-sm hover:bg-brand-700 disabled:cursor-not-allowed disabled:bg-gray-300"
          >
            {submitting ? 'Đang tạo…' : 'Tạo dự án'}
          </button>
        </div>
      </form>
    </main>
  );
}
