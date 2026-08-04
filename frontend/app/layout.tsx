import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "EconomyMate",
  description: "경제금융용어 설명 챗봇 PoC",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}

