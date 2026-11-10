"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

function GithubIcon({ className }: { className?: string }) {
  return (
    <svg
      role="img"
      viewBox="0 0 24 24"
      fill="currentColor"
      className={className || "h-3.5 w-3.5"}
    >
      <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
    </svg>
  );
}

export function Navbar() {
  const pathname = usePathname();

  const navLinks = [
    { href: "/", label: "Overview" },
    { href: "/config", label: "Config Generator" },
    { href: "/docs", label: "Documentation" },
  ];

  return (
    <header className="sticky top-0 z-50 w-full border-b border-zinc-800/80 bg-zinc-950/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-6">
          <Link
            href="/"
            className="flex items-center gap-2.5 font-mono text-sm font-semibold tracking-tight text-zinc-100 transition-opacity hover:opacity-90"
          >
            <svg
              viewBox="0 0 256 256"
              className="h-6 w-6 shrink-0 rounded"
              aria-hidden="true"
            >
              <rect width="256" height="256" rx="48" fill="#161b22" />
              <path
                d="M128 54 L192 91 L192 165 L128 202 L64 165 L64 91 Z M128 54 L128 202 M64 91 L128 128 L192 91"
                fill="none"
                stroke="#58a6ff"
                strokeWidth="14"
                strokeLinejoin="round"
                strokeLinecap="round"
              />
            </svg>
            <span>sysupdate</span>
          </Link>

          <nav className="hidden sm:flex items-center gap-1">
            {navLinks.map((link) => {
              const isActive =
                link.href === "/"
                  ? pathname === "/"
                  : pathname?.startsWith(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`rounded-md px-3 py-1.5 text-xs font-medium transition-colors ${
                    isActive
                      ? "bg-zinc-800 text-zinc-100"
                      : "text-zinc-400 hover:bg-zinc-900 hover:text-zinc-200"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <div className="sm:hidden flex items-center gap-1">
            {navLinks.map((link) => {
              const isActive =
                link.href === "/"
                  ? pathname === "/"
                  : pathname?.startsWith(link.href);
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={`rounded px-2 py-1 text-xs font-medium ${
                    isActive ? "text-zinc-100 font-semibold" : "text-zinc-400"
                  }`}
                >
                  {link.label}
                </Link>
              );
            })}
          </div>

          <a
            href="https://github.com/Piotrunius/SystemUpdater"
            target="_blank"
            rel="noopener noreferrer"
            aria-label="GitHub Repository"
            className="flex items-center gap-1.5 rounded-md border border-zinc-800 bg-zinc-900 px-2.5 py-1.5 text-xs text-zinc-300 transition-colors hover:border-zinc-700 hover:text-white"
          >
            <GithubIcon className="h-3.5 w-3.5" />
            <span className="hidden sm:inline">GitHub</span>
          </a>
        </div>
      </div>
    </header>
  );
}
