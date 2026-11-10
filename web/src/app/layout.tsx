import type { Metadata } from "next";
import { Inter, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
});

const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";

export const metadata: Metadata = {
  title: "SystemUpdater | Unified CLI Update Engine for Linux & macOS",
  description:
    "Runs updates for Linux and macOS package managers, desktop apps, containers, and development tools from a single command.",
  icons: {
    icon: `${basePath}/assets/icon.svg`,
  },
  other: {
    "darkreader-lock": "",
    "color-scheme": "dark",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${inter.variable} ${jetbrainsMono.variable}`}
    >
      <head>
        <meta name="darkreader-lock" content="" />
        <meta name="color-scheme" content="dark" />
      </head>
      <body
        suppressHydrationWarning
        className="flex min-h-screen flex-col bg-zinc-950 text-zinc-100 antialiased selection:bg-zinc-800 selection:text-zinc-100"
      >
        <Navbar />
        <main className="flex-1">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
