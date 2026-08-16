import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "WORLDOS",
  description: "Autonomous persistent world simulation",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
