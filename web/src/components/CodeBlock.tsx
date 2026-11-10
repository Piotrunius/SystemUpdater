"use client";

import { useState } from "react";
import { Check, Copy } from "lucide-react";

interface CodeBlockProps {
  code: string;
  language?: string;
  title?: string;
}

export function CodeBlock({ code, language = "bash", title }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  return (
    <div className="group relative overflow-hidden rounded-md border border-zinc-800 bg-[#0c0c0e] font-mono text-[13px] shadow-sm">
      <div className="flex h-9 items-center justify-between border-b border-zinc-850 bg-zinc-900/40 px-3.5">
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 opacity-60">
            <span className="h-2 w-2 rounded-full bg-zinc-600" />
            <span className="h-2 w-2 rounded-full bg-zinc-600" />
            <span className="h-2 w-2 rounded-full bg-zinc-600" />
          </div>
          <span className="text-[11px] text-zinc-400 font-sans pl-1">
            {title || language}
          </span>
        </div>

        <button
          type="button"
          onClick={handleCopy}
          aria-label="Copy code"
          className="flex items-center gap-1.5 rounded border border-zinc-750 bg-zinc-800/80 px-2 py-0.5 text-[11px] text-zinc-300 transition-colors hover:border-zinc-600 hover:bg-zinc-700 hover:text-white"
        >
          {copied ? (
            <>
              <Check className="h-3 w-3 text-emerald-400" />
              <span className="font-sans text-emerald-400">Copied</span>
            </>
          ) : (
            <>
              <Copy className="h-3 w-3 text-zinc-400" />
              <span className="font-sans">Copy</span>
            </>
          )}
        </button>
      </div>

      <div className="overflow-x-auto p-3.5 text-zinc-200 leading-relaxed">
        <pre className="selection:bg-zinc-800">
          <code>{code}</code>
        </pre>
      </div>
    </div>
  );
}
