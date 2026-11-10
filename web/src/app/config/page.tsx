import type { Metadata } from "next";
import siteMetadata from "@/data/generated-metadata.json";
import { ConfigBuilder } from "@/components/ConfigBuilder";
import { ModuleMeta } from "@/types/metadata";

export const metadata: Metadata = {
  title: "Configuration Generator | SystemUpdater",
  description:
    "Interactive configuration builder for SystemUpdater config.toml. Customize behavior, timeouts, notifications, and module exclusions.",
};

export default function ConfigPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6">
      <div className="mb-8 border-b border-zinc-800 pb-6">
        <h1 className="mt-2 text-2xl sm:text-3xl font-bold tracking-tight text-white">
          Configuration Builder
        </h1>
        <p className="mt-2 max-w-3xl text-xs sm:text-sm text-zinc-400">
          Configure update preferences, timeout safeguards, desktop
          notifications, and module inclusions. The generated{" "}
          <code className="text-zinc-200">config.toml</code> updates in real
          time and can be copied or downloaded directly into your configuration
          directory.
        </p>
      </div>

      <ConfigBuilder
        modules={siteMetadata.modules as unknown as ModuleMeta[]}
        categories={siteMetadata.categories}
      />
    </div>
  );
}
