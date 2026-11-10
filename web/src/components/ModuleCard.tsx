import { ModuleMeta } from "@/types/metadata";
import { Laptop, Layers } from "lucide-react";

export function ModuleCard({ module }: { module: ModuleMeta }) {
  const getPlatformBadge = (platform: ModuleMeta["platform"]) => {
    switch (platform) {
      case "linux":
        return {
          label: "Linux",
          border: "border-cyan-800/40 text-cyan-300 bg-cyan-950/30",
        };
      case "macos":
        return {
          label: "macOS",
          border: "border-purple-800/40 text-purple-300 bg-purple-950/30",
        };
      default:
        return {
          label: "Universal",
          border: "border-zinc-700/50 text-zinc-300 bg-zinc-800/40",
        };
    }
  };

  const badge = getPlatformBadge(module.platform);

  return (
    <div className="flex flex-col justify-between rounded border border-zinc-800 bg-[#0e0e11] p-3.5 transition-colors hover:border-zinc-700 hover:bg-[#121216]">
      <div>
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 overflow-hidden">
            <span className="font-semibold text-xs text-zinc-100 truncate">
              {module.name}
            </span>
            <code className="rounded bg-zinc-800/80 px-1.5 py-0.2 font-mono text-[10px] text-zinc-300 shrink-0">
              {module.key}
            </code>
          </div>

          <span
            className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.2 text-[10px] font-mono shrink-0 ${badge.border}`}
          >
            <Laptop className="h-2.5 w-2.5" />
            {badge.label}
          </span>
        </div>

        <p className="mt-1.5 text-[11px] leading-relaxed text-zinc-400 line-clamp-2">
          {module.description || "Package and tool update manager."}
        </p>

        {module.aliases && module.aliases.length > 0 && (
          <div className="mt-2 flex flex-wrap items-center gap-1 text-[10px] text-zinc-500 font-mono">
            <span className="text-zinc-600">alias:</span>
            {module.aliases.map((alias) => (
              <span
                key={alias}
                className="rounded bg-zinc-900 border border-zinc-800 px-1 py-0.1 text-zinc-400"
              >
                {alias}
              </span>
            ))}
          </div>
        )}
      </div>

      <div className="mt-3 flex items-center justify-between border-t border-zinc-850 pt-2 text-[10px] text-zinc-500 font-mono">
        <span className="flex items-center gap-1">
          <Layers className="h-2.5 w-2.5 text-zinc-600" />
          {module.category}
        </span>

        {module.requires_sudo ? (
          <span className="text-amber-400 font-medium">sudo</span>
        ) : (
          <span className="text-zinc-500">user</span>
        )}
      </div>
    </div>
  );
}
