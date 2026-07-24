import type { Metadata, Viewport } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import TopBar from "../components/TopBar";
import Footer from "../components/Footer";
import { BRAND } from "../lib/brand";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  weight: ["400", "600", "800"],
});

export const metadata: Metadata = {
  title: {
    default: `${BRAND.name} · ${BRAND.full}`,
    template: `%s · ${BRAND.name}`,
  },
  description:
    "Topology-constrained causal analysis that names the component which caused an outage, not the loudest victim. Deterministic ranking, cited evidence, and agentic-RAG remediation grounded in NOC runbooks.",
  applicationName: BRAND.name,
};

export const viewport: Viewport = {
  themeColor: "#0B0B0D",
  width: "device-width",
  initialScale: 1,
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
        <a
          href="#main"
          className="sr-only focus:not-sr-only focus:absolute focus:top-2 focus:left-2 focus:z-50 focus:px-3 focus:py-2 focus:rounded-md focus:bg-[var(--accent-red)] focus:text-white focus:text-xs focus:font-bold"
        >
          Skip to content
        </a>
        <div className="min-h-screen flex flex-col">
          <TopBar />
          <main id="main" className="flex-1 flex flex-col">
            {children}
          </main>
          <Footer />
        </div>
      </body>
    </html>
  );
}


