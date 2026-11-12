import Link from "next/link";
import Image from "next/image";
import metadata from "@/data/generated-metadata.json";
import { CodeBlock } from "@/components/CodeBlock";
import { ArrowRight, Sliders, Shield, Zap, Package } from "lucide-react";

export default function Home() {
  const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
  const brewInstallCmd = `brew tap Piotrunius/tap
brew trust Piotrunius/tap
brew install systemupdater`;

  const commonCommands = [
    {
      cmd: "sysupdate",
      desc: "Run complete system update with auto-detected tools",
    },
    {
      cmd: "sysupdate --only dnf,brew",
      desc: "Update only specific package managers",
    },
    {
      cmd: "sysupdate --no-sudo",
      desc: "Run only unprivileged modules without root prompt",
    },
    { cmd: "sysupdate --skip docker", desc: "Skip container updates" },
    {
      cmd: "sysupdate --history",
      desc: "Show recent update logs and upgraded counts",
    },
  ];

  return (
    <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 space-y-20">
      {/* 1. Hero Section (Centered, Clean, Focused) */}
      <section className="text-center space-y-6">
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight text-white">
          Unified system update engine
        </h1>

        <p className="mx-auto max-w-2xl text-sm sm:text-base leading-relaxed text-zinc-400">
          A fast, modular CLI updater that automatically detects your installed
          package managers, desktop applications, containers, and developer
          toolchains.
        </p>

        {/* Install Code Block: Homebrew (Recommended) */}
        <div className="mx-auto max-w-lg text-left pt-2">
          <CodeBlock code={brewInstallCmd} title="Install (Homebrew)" />
          <p className="mt-1.5 text-center text-[11px] text-zinc-500 font-mono">
            Also available via{" "}
            <Link
              href="/docs#installation"
              className="text-zinc-400 underline underline-offset-2 hover:text-zinc-200"
            >
              Git checkout
            </Link>
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
          <Link
            href="/config"
            className="inline-flex items-center gap-2 rounded-md bg-zinc-100 px-4 py-2 text-xs font-semibold text-zinc-950 transition-colors hover:bg-white"
          >
            <Sliders className="h-3.5 w-3.5" />
            <span>Config Generator</span>
          </Link>

          <Link
            href="/docs"
            className="inline-flex items-center gap-2 rounded-md border border-zinc-800 bg-zinc-900 px-4 py-2 text-xs font-medium text-zinc-300 transition-colors hover:border-zinc-700 hover:text-white"
          >
            <span>Documentation & Modules ({metadata.modules.length})</span>
            <ArrowRight className="h-3.5 w-3.5 text-zinc-500" />
          </Link>
        </div>
      </section>

      {/* 2. Terminal Demo (Clean window frame, centered, max-w-2xl) */}
      <section className="mx-auto max-w-2xl">
        <div className="overflow-hidden rounded-lg border border-zinc-800 bg-[#0c0c0e] shadow-2xl">
          <div className="flex items-center justify-between border-b border-zinc-800/80 bg-zinc-900/60 px-4 py-2.5">
            <div className="flex items-center gap-1.5 opacity-60">
              <span className="h-2.5 w-2.5 rounded-full bg-zinc-600" />
              <span className="h-2.5 w-2.5 rounded-full bg-zinc-600" />
              <span className="h-2.5 w-2.5 rounded-full bg-zinc-600" />
            </div>
            <span className="font-mono text-xs text-zinc-400">
              sysupdate demo
            </span>
            <div className="w-8" />
          </div>

          <div className="relative bg-black" style={{ position: "relative" }}>
            <Image
              src={`${basePath}/assets/gifs/demo_full_update.gif`}
              alt="SystemUpdater execution demo"
              width={860}
              height={760}
              unoptimized
              className="w-full h-auto block select-none"
              priority
            />
          </div>
        </div>
      </section>

      {/* 3. Core Pillars (3 balanced vertical cards) */}
      <section className="space-y-6">
        <div className="text-center">
          <h2 className="text-xl font-bold tracking-tight text-white">
            Designed for stability and simplicity
          </h2>
          <p className="mt-1 text-xs text-zinc-400">
            No bloated runtimes or fragile dependencies. Just clean, resilient
            updates.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <div className="rounded-lg border border-zinc-800/80 bg-zinc-900/30 p-5 space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-zinc-200">
              <Zap className="h-4 w-4 text-emerald-400" />
              <h3>Zero Dependencies</h3>
            </div>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Written purely with the Python 3.11+ standard library. No pip
              packages, no virtualenvs, and no background daemons needed to run.
            </p>
          </div>

          <div className="rounded-lg border border-zinc-800/80 bg-zinc-900/30 p-5 space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-zinc-200">
              <Shield className="h-4 w-4 text-cyan-400" />
              <h3>Btrfs Snapshot Safety</h3>
            </div>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Automatically creates protective Snapper root snapshots before
              system package upgrades, with configurable cooldown safeguards.
            </p>
          </div>

          <div className="rounded-lg border border-zinc-800/80 bg-zinc-900/30 p-5 space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-zinc-200">
              <Package className="h-4 w-4 text-purple-400" />
              <h3>50+ Unified Sources</h3>
            </div>
            <p className="text-xs text-zinc-400 leading-relaxed">
              Updates system packages (DNF, APT, Pacman), containers (Docker,
              Podman), desktop apps (Flatpak), and dev tools (Rust, uv, Mise,
              Neovim).
            </p>
          </div>
        </div>
      </section>

      {/* 4. Common CLI Usage */}
      <section className="rounded-lg border border-zinc-800 bg-[#0c0c0e] p-5 space-y-4">
        <div className="flex items-center justify-between border-b border-zinc-850 pb-3">
          <div>
            <h3 className="text-sm font-semibold text-white">
              Common CLI Commands
            </h3>
            <p className="text-xs text-zinc-400">
              Fine-tune your update routine with intuitive command-line flags.
            </p>
          </div>
          <Link
            href="/docs"
            className="text-xs text-zinc-400 hover:text-white underline underline-offset-2 font-mono"
          >
            All flags &rarr;
          </Link>
        </div>

        <div className="divide-y divide-zinc-850">
          {commonCommands.map((item, idx) => (
            <div
              key={idx}
              className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5 py-2.5 text-xs"
            >
              <code className="font-mono text-emerald-400 font-medium">
                {item.cmd}
              </code>
              <span className="text-zinc-400 text-[11px] sm:text-xs">
                {item.desc}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
