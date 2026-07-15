import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  weight: ["400", "600", "800"],
});

export const metadata: Metadata = {
  title: "Network Anomaly Root-Cause Assistant // NOC Dashboard",
  description: "High-density diagnostics engine for real-time network topology anomaly mapping, causal inference tracking, and evidence ledgers.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`dark ${inter.variable}`} suppressHydrationWarning>
      <body
        className="bg-background text-foreground font-sans antialiased"
        suppressHydrationWarning
      >
        {children}
      </body>
    </html>
  );
}


