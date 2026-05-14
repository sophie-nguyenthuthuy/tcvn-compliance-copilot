import Link from 'next/link';

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-4xl flex-col items-center justify-center px-6 py-16">
      <h1 className="text-4xl font-bold tracking-tight">TCVN Compliance Copilot</h1>
      <p className="mt-4 max-w-2xl text-center text-lg text-gray-600">
        Soát chiếu tự động bản vẽ AEC với tiêu chuẩn Việt Nam — QCVN 06 (PCCC), QCVN 10 (tiếp
        cận), TCVN 2737 (tải trọng) và hơn thế. Tải bản vẽ, chọn tiêu chuẩn, nhận báo cáo
        non-compliance với trích dẫn điều khoản.
      </p>
      <div className="mt-10 flex gap-4">
        <Link
          href="/projects"
          className="rounded-md bg-brand px-5 py-2.5 text-white shadow-sm transition hover:bg-brand-700"
        >
          Vào ứng dụng
        </Link>
        <Link
          href="/standards"
          className="rounded-md border border-gray-300 bg-white px-5 py-2.5 text-gray-800 shadow-sm transition hover:border-gray-400"
        >
          Tiêu chuẩn hỗ trợ
        </Link>
      </div>
    </main>
  );
}
