import type { Metadata } from "next";
import siteMetadata from "@/data/generated-metadata.json";
import { ModuleCatalog } from "@/components/ModuleCatalog";
import { CodeBlock } from "@/components/CodeBlock";
import { ModuleMeta } from "@/types/metadata";
import { Terminal, Download, Settings, Layers, Sparkles } from "lucide-react";

export const metadata: Metadata = {
  title: "Documentation & Modules | SystemUpdater",
  description:
    "Complete documentation, CLI flag reference, installation guides, and full module catalog for SystemUpdater.",
};

export default function DocsPage() {
  const gitInstall = `git clone https://github.com/Piotrunius/SystemUpdater.git ~/.local/share/sysupdate
cd ~/.local/share/sysupdate
./install.sh`;

  const brewInstall = `brew tap Piotrunius/tap
brew install systemupdater`;

  const completionsCmd = `# Auto-detect installed shells and register completions
sysupdate --generate-completion

# Or specify your shell directly
sysupdate --generate-completion zsh`;

  return (
    <div className="mx-auto max-w-6xl px-4 py-10 sm:px-6 space-y-14">
      {/* Page Title */}
      <div className="border-b border-zinc-850 pb-5">
        <h1 className="mt-1 text-2xl sm:text-3xl font-bold tracking-tight text-white">
          Documentation & Modules
        </h1>
        <p className="mt-1.5 max-w-2xl text-xs sm:text-sm text-zinc-400">
          CLI usage, shell completion setup, configuration directives, and the
          complete registry of {siteMetadata.modules.length} supported update
          sources.
        </p>
      </div>

      {/* 1. Installation */}
      <section id="installation" className="space-y-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-zinc-200">
          <Download className="h-4 w-4 text-emerald-400" />
          <h2>Installation Methods</h2>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {/* Homebrew */}
          <div className="rounded border border-zinc-800 bg-[#0c0c0e] p-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-zinc-200">
                1. Homebrew (Recommended)
              </span>
              <span className="rounded bg-emerald-950/40 border border-emerald-800/40 px-1.5 py-0.2 font-mono text-[10px] text-emerald-400">
                recommended
              </span>
            </div>
            <p className="text-[11px] text-zinc-400 leading-relaxed">
              Install via official Homebrew tap. SystemUpdater and its formulae
              are updated automatically by Homebrew.
            </p>
            <CodeBlock code={brewInstall} title="bash" />
          </div>

          {/* Git checkout */}
          <div className="rounded border border-zinc-800 bg-[#0c0c0e] p-4 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-zinc-200">
                2. Git Checkout
              </span>
              <span className="rounded bg-zinc-850 px-1.5 py-0.2 font-mono text-[10px] text-zinc-400">
                standalone
              </span>
            </div>
            <p className="text-[11px] text-zinc-400 leading-relaxed">
              Links{" "}
              <code className="text-zinc-300">~/.local/bin/sysupdate</code> and
              auto-creates default config. The checkout auto-updates itself when
              run.
            </p>
            <CodeBlock code={gitInstall} title="bash" />
          </div>
        </div>

        {/* Completions */}
        <div className="rounded border border-zinc-800 bg-[#0c0c0e] p-4 space-y-2">
          <div className="flex items-center gap-2 text-xs font-semibold text-zinc-200">
            <Sparkles className="h-3.5 w-3.5 text-purple-400" />
            <span>Native Shell Completions</span>
          </div>
          <p className="text-[11px] text-zinc-400">
            Generates tab completions for flags, categories, and module keys:
          </p>
          <CodeBlock code={completionsCmd} title="bash / zsh / fish" />
        </div>
      </section>

      {/* 2. CLI Flags & Options */}
      <section id="cli-reference" className="space-y-4">
        <div className="flex items-center justify-between border-b border-zinc-850 pb-2">
          <div className="flex items-center gap-2 text-sm font-semibold text-zinc-200">
            <Terminal className="h-4 w-4 text-cyan-400" />
            <h2>Command-Line Options</h2>
          </div>
          <code className="text-[11px] text-zinc-500 font-mono">
            sysupdate [flags]
          </code>
        </div>

        <div className="overflow-hidden rounded border border-zinc-800 bg-[#0c0c0e]">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-zinc-800 bg-zinc-900/60 font-mono text-[10px] text-zinc-400 uppercase tracking-wider">
                <tr>
                  <th className="px-3.5 py-2 font-semibold">Flag</th>
                  <th className="px-3.5 py-2 font-semibold">Category</th>
                  <th className="px-3.5 py-2 font-semibold">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-850 font-mono text-[11px]">
                {siteMetadata.cli_flags.map((item, idx) => (
                  <tr
                    key={idx}
                    className="hover:bg-zinc-900/40 transition-colors"
                  >
                    <td className="px-3.5 py-2 text-emerald-400 font-medium whitespace-nowrap">
                      {item.flags.join(", ")}
                    </td>
                    <td className="px-3.5 py-2 text-zinc-400 whitespace-nowrap font-sans text-xs">
                      {item.category}
                    </td>
                    <td className="px-3.5 py-2 text-zinc-300 font-sans text-xs">
                      {item.description}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>

      {/* 3. Configuration Sections */}
      <section id="config-schema" className="space-y-4">
        <div className="flex items-center gap-2 text-sm font-semibold text-zinc-200">
          <Settings className="h-4 w-4 text-amber-400" />
          <h2>Configuration Directives</h2>
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3 text-xs">
          <div className="rounded border border-zinc-800 bg-[#0c0c0e] p-3 space-y-1">
            <code className="font-mono text-zinc-200 font-semibold">
              [misc]
            </code>
            <p className="text-[11px] text-zinc-400">
              Snapper root snapshot cooldown hours and maximum command execution
              timeout.
            </p>
          </div>
          <div className="rounded border border-zinc-800 bg-[#0c0c0e] p-3 space-y-1">
            <code className="font-mono text-zinc-200 font-semibold">
              [behavior]
            </code>
            <p className="text-[11px] text-zinc-400">
              Quiet mode, verbose streaming, no-sudo, and reboot automation.
            </p>
          </div>
          <div className="rounded border border-zinc-800 bg-[#0c0c0e] p-3 space-y-1">
            <code className="font-mono text-zinc-200 font-semibold">
              [notifications]
            </code>
            <p className="text-[11px] text-zinc-400">
              Desktop notification triggers (Linux notify-send, macOS
              osascript).
            </p>
          </div>
          <div className="rounded border border-zinc-800 bg-[#0c0c0e] p-3 space-y-1">
            <code className="font-mono text-zinc-200 font-semibold">
              [modules]
            </code>
            <p className="text-[11px] text-zinc-400">
              Permanently disabled modules, default skipped keys, or strict
              inclusion lists.
            </p>
          </div>
          <div className="rounded border border-zinc-800 bg-[#0c0c0e] p-3 space-y-1">
            <code className="font-mono text-zinc-200 font-semibold">[git]</code>
            <p className="text-[11px] text-zinc-400">
              Local git repositories to pull and update during the run.
            </p>
          </div>
          <div className="rounded border border-zinc-800 bg-[#0c0c0e] p-3 space-y-1">
            <code className="font-mono text-zinc-200 font-semibold">
              [pre/post_commands]
            </code>
            <p className="text-[11px] text-zinc-400">
              Arbitrary shell commands executed before or after update passes.
            </p>
          </div>
        </div>
      </section>

      {/* 4. Complete Module Catalog */}
      <section id="modules" className="space-y-4">
        <div className="flex items-center justify-between border-b border-zinc-850 pb-2">
          <div className="flex items-center gap-2 text-sm font-semibold text-zinc-200">
            <Layers className="h-4 w-4 text-purple-400" />
            <h2>Supported Update Modules</h2>
          </div>
        </div>

        <p className="text-xs text-zinc-400">
          Tools are automatically detected at runtime. Run{" "}
          <code className="text-zinc-200">sysupdate --list</code> to inspect
          which modules are active on your current machine.
        </p>

        <ModuleCatalog
          modules={siteMetadata.modules as unknown as ModuleMeta[]}
          categories={siteMetadata.categories}
        />
      </section>
    </div>
  );
}
