import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Football Predictor 2026",
  description: "Demo dashboard for a World Cup 2026 football prediction system.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}

