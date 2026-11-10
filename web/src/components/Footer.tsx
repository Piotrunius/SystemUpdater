export function Footer() {
  return (
    <footer className="w-full border-t border-zinc-800/80 bg-zinc-950 py-8 text-xs text-zinc-500">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-4 sm:flex-row sm:px-6">
        <div className="flex flex-col items-center gap-1 sm:items-start">
          <span className="font-mono text-zinc-400">
            SystemUpdater (sysupdate)
          </span>
          <span className="text-zinc-600">
            Unified update engine for Linux and macOS. Pure Python standard
            library.
          </span>
        </div>

        <div className="flex items-center gap-5 text-zinc-400">
          <a
            href="https://github.com/Piotrunius/SystemUpdater"
            target="_blank"
            rel="noopener noreferrer"
            className="transition-colors hover:text-zinc-200"
          >
            Repository
          </a>
          <a
            href="https://github.com/Piotrunius/SystemUpdater/blob/main/LICENSE"
            target="_blank"
            rel="noopener noreferrer"
            className="transition-colors hover:text-zinc-200"
          >
            MIT License
          </a>
          <a
            href="https://github.com/Piotrunius/SystemUpdater/issues"
            target="_blank"
            rel="noopener noreferrer"
            className="transition-colors hover:text-zinc-200"
          >
            Issues
          </a>
        </div>
      </div>
    </footer>
  );
}
