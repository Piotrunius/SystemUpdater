"use client";

import { useEffect } from "react";
import Link from "next/link";

export default function ErrorPage({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-[65vh] flex-col items-center justify-center text-center px-4">
      <span className="font-mono text-xs font-medium uppercase tracking-widest text-zinc-500">
        Error
      </span>
      <h1 className="mt-2 text-2xl sm:text-3xl font-semibold tracking-tight text-white">
        Something went wrong
      </h1>
      <p className="mt-2 max-w-sm text-xs sm:text-sm text-zinc-400">
        An unexpected error occurred while loading this page.
      </p>

      <div className="mt-6 flex items-center gap-2.5">
        <button
          type="button"
          onClick={() => reset()}
          className="rounded border border-zinc-700 bg-zinc-100 px-3.5 py-1.5 text-xs font-medium text-zinc-950 transition-colors hover:bg-white"
        >
          Try again
        </button>
        <Link
          href="/"
          className="rounded border border-zinc-800 bg-zinc-900 px-3.5 py-1.5 text-xs font-medium text-zinc-300 transition-colors hover:border-zinc-700 hover:text-white"
        >
          Back to home
        </Link>
      </div>
    </div>
  );
}
