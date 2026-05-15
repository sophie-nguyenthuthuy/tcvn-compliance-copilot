'use client';

import { useQuery } from '@tanstack/react-query';

import { standardsApi, type Standard } from '../../lib/api';

export default function StandardsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['standards'],
    queryFn: standardsApi.list,
  });

  return (
    <main className="mx-auto max-w-5xl px-6 py-12">
      <h1 className="text-3xl font-semibold">Tiêu chuẩn được hỗ trợ</h1>
      <p className="mt-2 text-gray-600">
        Danh sách TCVN/QCVN đã được số hoá và sẵn sàng cho soát chiếu tự động.
      </p>

      <div className="mt-8 overflow-hidden rounded-lg border bg-white shadow-sm">
        {isLoading && <div className="p-6 text-gray-500">Đang tải…</div>}
        {error && (
          <div className="p-6 text-severity-high">Không tải được danh sách tiêu chuẩn.</div>
        )}
        {data && (
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50 text-left">
              <tr>
                <th className="px-4 py-3 font-medium">Mã</th>
                <th className="px-4 py-3 font-medium">Tên</th>
                <th className="px-4 py-3 font-medium">Phiên bản</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {data.map((s: Standard) => (
                <tr key={s.id}>
                  <td className="px-4 py-3 font-mono">{s.code}</td>
                  <td className="px-4 py-3">{s.title_vi}</td>
                  <td className="px-4 py-3">{s.version}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </main>
  );
}
