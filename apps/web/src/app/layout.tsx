import type { Metadata } from 'next';
import type { ReactNode } from 'react';

import '../styles/globals.css';
import { Providers } from '../components/providers';

export const metadata: Metadata = {
  title: 'TCVN Compliance Copilot',
  description:
    'RAG-based compliance review of AEC drawings against Vietnamese TCVN/QCVN standards.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="vi">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
