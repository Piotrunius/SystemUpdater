"use client";

import { useState, useMemo } from "react";
import { ModuleMeta } from "@/types/metadata";
import {
  Copy,
  Download,
  Check,
  Settings2,
  Sliders,
  Shield,
  Bell,
  Box,
  Terminal,
  Layers,
  FolderGit2,
  Plus,
  Trash2,
} from "lucide-react";

type CommandPhase = "pre_commands" | "commands" | "post_commands";

interface CustomCommandEntry {
  id: string;
  phase: CommandPhase;
  name: string;
  command: string;
}

const CANONICAL_CATEGORIES = [
  "system",
  "protection",
  "applications",
  "gaming",
  "containers",
  "dev",
  "editors",
  "dotfiles",
] as const;

function escapeTomlString(value: string): string {
  return value
    .replace(/\\/g, "\\\\")
    .replace(/"/g, '\\"')
    .replace(/\r?\n/g, " ");
}

interface ConfigBuilderProps {
  modules: ModuleMeta[];
  categories: string[];
}

export function ConfigBuilder({ modules, categories }: ConfigBuilderProps) {
  // General options
  const [cooldownHours, setCooldownHours] = useState(12);
  const [commandTimeout, setCommandTimeout] = useState(180);
  const [reboot, setReboot] = useState(false);
  const [quiet, setQuiet] = useState(false);
  const [verbose, setVerbose] = useState(false);
  const [noSudo, setNoSudo] = useState(false);
  const [noSnapshot, setNoSnapshot] = useState(false);
  const [noHistory, setNoHistory] = useState(false);
  const [selfUpdate, setSelfUpdate] = useState(true);
  const [skipOnBattery, setSkipOnBattery] = useState(false);
  const [checkNetwork, setCheckNetwork] = useState(false);

  // Notifications
  const [notifyEnabled, setNotifyEnabled] = useState(false);
  const [notifyOnlyOnError, setNotifyOnlyOnError] = useState(false);

  // Category filters
  const [categoryOnly, setCategoryOnly] = useState<Set<string>>(new Set());
  const [categorySkip, setCategorySkip] = useState<Set<string>>(new Set());

  // Git repositories
  const [gitRepoInput, setGitRepoInput] = useState("");
  const [gitRepos, setGitRepos] = useState<string[]>([]);

  // Custom commands
  const [cmdPhase, setCmdPhase] = useState<CommandPhase>("commands");
  const [cmdName, setCmdName] = useState("");
  const [cmdExec, setCmdExec] = useState("");
  const [customCommands, setCustomCommands] = useState<CustomCommandEntry[]>(
    [],
  );

  // Module exclusions
  const [disabledModules, setDisabledModules] = useState<Set<string>>(
    new Set(),
  );
  const [searchModule, setSearchModule] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");

  const [previewMode, setPreviewMode] = useState<"command" | "toml">("command");
  const [copied, setCopied] = useState(false);

  const toggleDisableModule = (key: string) => {
    setDisabledModules((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  };

  const toggleCategoryFilter = (cat: string, mode: "only" | "skip") => {
    if (mode === "only") {
      setCategoryOnly((prev) => {
        const next = new Set(prev);
        if (next.has(cat)) {
          next.delete(cat);
        } else {
          next.add(cat);
        }
        return next;
      });
      setCategorySkip((prev) => {
        if (!prev.has(cat)) return prev;
        const next = new Set(prev);
        next.delete(cat);
        return next;
      });
    } else {
      setCategorySkip((prev) => {
        const next = new Set(prev);
        if (next.has(cat)) {
          next.delete(cat);
        } else {
          next.add(cat);
        }
        return next;
      });
      setCategoryOnly((prev) => {
        if (!prev.has(cat)) return prev;
        const next = new Set(prev);
        next.delete(cat);
        return next;
      });
    }
  };

  const handleAddGitRepo = () => {
    const trimmed = gitRepoInput.trim();
    if (!trimmed || gitRepos.includes(trimmed)) return;
    setGitRepos((prev) => [...prev, trimmed]);
    setGitRepoInput("");
  };

  const handleAddCustomCommand = () => {
    const name = cmdName.trim();
    const command = cmdExec.trim();
    if (!name || !command) return;
    setCustomCommands((prev) => [
      ...prev,
      {
        id: `${cmdPhase}-${name}-${Date.now()}`,
        phase: cmdPhase,
        name,
        command,
      },
    ]);
    setCmdName("");
    setCmdExec("");
  };

  const filteredModules = useMemo(() => {
    return modules.filter((m) => {
      const matchSearch =
        !searchModule ||
        m.name.toLowerCase().includes(searchModule.toLowerCase()) ||
        m.key.toLowerCase().includes(searchModule.toLowerCase());
      const matchCategory =
        selectedCategory === "All" || m.category === selectedCategory;
      return matchSearch && matchCategory;
    });
  }, [modules, searchModule, selectedCategory]);

  const generatedToml = useMemo(() => {
    const lines: string[] = [
      "# SystemUpdater Configuration File",
      "# Location: ~/.config/sysupdate/config.toml",
      "",
      "[misc]",
      `cooldown_hours = ${cooldownHours}`,
      `command_timeout = ${commandTimeout}`,
      "",
      "[behavior]",
      `reboot = ${reboot}`,
      `quiet = ${quiet}`,
      `verbose = ${verbose}`,
      `no_sudo = ${noSudo}`,
      `no_snapshot = ${noSnapshot}`,
      `no_history = ${noHistory}`,
      `self_update = ${selfUpdate}`,
      `skip_on_battery = ${skipOnBattery}`,
      `check_network = ${checkNetwork}`,
      "",
      "[notifications]",
      `enabled = ${notifyEnabled}`,
      `only_on_error_or_reboot = ${notifyOnlyOnError}`,
      "",
      "[modules]",
    ];

    if (disabledModules.size > 0) {
      const formatted = Array.from(disabledModules)
        .sort()
        .map((k) => `"${escapeTomlString(k)}"`)
        .join(", ");
      lines.push(`disable = [${formatted}]`);
    } else {
      lines.push('# disable = ["snap", "docker"]');
    }

    lines.push("# skip = []");
    lines.push("# only = []");
    lines.push("");
    lines.push("[categories]");
    if (categoryOnly.size > 0) {
      const formatted = Array.from(categoryOnly)
        .sort()
        .map((c) => `"${escapeTomlString(c)}"`)
        .join(", ");
      lines.push(`only = [${formatted}]`);
    } else {
      lines.push("# only = []");
    }
    if (categorySkip.size > 0) {
      const formatted = Array.from(categorySkip)
        .sort()
        .map((c) => `"${escapeTomlString(c)}"`)
        .join(", ");
      lines.push(`skip = [${formatted}]`);
    } else {
      lines.push("# skip = []");
    }
    lines.push("");
    lines.push("[git]");
    if (gitRepos.length > 0) {
      lines.push("repos = [");
      gitRepos.forEach((repo) => {
        lines.push(`  "${escapeTomlString(repo)}",`);
      });
      lines.push("]");
    } else {
      lines.push("# repos = [");
      lines.push('#   "~/dotfiles",');
      lines.push('#   "~/.config/nvim"');
      lines.push("# ]");
    }

    const preCmds = customCommands.filter((c) => c.phase === "pre_commands");
    const mainCmds = customCommands.filter((c) => c.phase === "commands");
    const postCmds = customCommands.filter((c) => c.phase === "post_commands");

    lines.push("");
    lines.push("[pre_commands]");
    if (preCmds.length > 0) {
      preCmds.forEach((c) => {
        lines.push(
          `"${escapeTomlString(c.name)}" = "${escapeTomlString(c.command)}"`,
        );
      });
    } else {
      lines.push('# "Clean temp files" = "rm -rf /tmp/build-cache-*"');
    }

    lines.push("");
    lines.push("[commands]");
    if (mainCmds.length > 0) {
      mainCmds.forEach((c) => {
        lines.push(
          `"${escapeTomlString(c.name)}" = "${escapeTomlString(c.command)}"`,
        );
      });
    } else {
      lines.push('# "Custom tool" = "my-tool update"');
    }

    lines.push("");
    lines.push("[post_commands]");
    if (postCmds.length > 0) {
      postCmds.forEach((c) => {
        lines.push(
          `"${escapeTomlString(c.name)}" = "${escapeTomlString(c.command)}"`,
        );
      });
    } else {
      lines.push(
        '# "Update desktop DB" = "update-desktop-database ~/.local/share/applications"',
      );
    }

    return lines.join("\n");
  }, [
    cooldownHours,
    commandTimeout,
    reboot,
    quiet,
    verbose,
    noSudo,
    noSnapshot,
    noHistory,
    selfUpdate,
    skipOnBattery,
    checkNetwork,
    notifyEnabled,
    notifyOnlyOnError,
    disabledModules,
    categoryOnly,
    categorySkip,
    gitRepos,
    customCommands,
  ]);

  const generatedBashCommand = useMemo(() => {
    return `mkdir -p "\${XDG_CONFIG_HOME:-\$HOME/.config}/sysupdate" && cat << 'EOF' > "\${XDG_CONFIG_HOME:-\$HOME/.config}/sysupdate/config.toml"
${generatedToml}
EOF
echo "Saved configuration to \${XDG_CONFIG_HOME:-\$HOME/.config}/sysupdate/config.toml"`;
  }, [generatedToml]);

  const handleCopy = async () => {
    try {
      const textToCopy =
        previewMode === "command" ? generatedBashCommand : generatedToml;
      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  const handleDownload = () => {
    const blob = new Blob([generatedToml], {
      type: "text/plain;charset=utf-8",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "config.toml";
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 items-start">
      {/* Controls Column */}
      <div className="space-y-4 lg:col-span-6">
        {/* Behavior & Execution Section */}
        <div className="rounded border border-zinc-800 bg-[#0c0c0e] p-4 space-y-3">
          <div className="flex items-center gap-2 border-b border-zinc-850 pb-2 text-xs font-semibold text-zinc-200">
            <Sliders className="h-3.5 w-3.5 text-emerald-400" />
            <span>Behavior & Runtime</span>
          </div>

          <div className="space-y-2 text-xs">
            <label className="flex items-center justify-between cursor-pointer py-1">
              <div>
                <span className="font-medium text-zinc-300">Quiet mode</span>
                <p className="text-[11px] text-zinc-500">
                  Hide step progress, show only summary
                </p>
              </div>
              <input
                type="checkbox"
                checked={quiet}
                onChange={(e) => {
                  const checked = e.target.checked;
                  setQuiet(checked);
                  if (checked) setVerbose(false);
                }}
                className="h-3.5 w-3.5 rounded border-zinc-700 bg-zinc-900 accent-emerald-500"
              />
            </label>

            <label className="flex items-center justify-between cursor-pointer py-1 border-t border-zinc-850/60">
              <div>
                <span className="font-medium text-zinc-300">
                  Verbose streaming
                </span>
                <p className="text-[11px] text-zinc-500">
                  Stream sub-command output in real time
                </p>
              </div>
              <input
                type="checkbox"
                checked={verbose}
                onChange={(e) => {
                  const checked = e.target.checked;
                  setVerbose(checked);
                  if (checked) setQuiet(false);
                }}
                className="h-3.5 w-3.5 rounded border-zinc-700 bg-zinc-900 accent-emerald-500"
              />
            </label>

            <label className="flex items-center justify-between cursor-pointer py-1 border-t border-zinc-850/60">
              <div>
                <span className="font-medium text-zinc-300">Skip sudo</span>
                <p className="text-[11px] text-zinc-500">
                  Run only unprivileged update routines
                </p>
              </div>
              <input
                type="checkbox"
                checked={noSudo}
                onChange={(e) => setNoSudo(e.target.checked)}
                className="h-3.5 w-3.5 rounded border-zinc-700 bg-zinc-900 accent-emerald-500"
              />
            </label>

            <label className="flex items-center justify-between cursor-pointer py-1 border-t border-zinc-850/60">
              <div>
                <span className="font-medium text-zinc-300">
                  Automatic reboot
                </span>
                <p className="text-[11px] text-zinc-500">
                  Reboot if kernel or firmware requires it
                </p>
              </div>
              <input
                type="checkbox"
                checked={reboot}
                onChange={(e) => setReboot(e.target.checked)}
                className="h-3.5 w-3.5 rounded border-zinc-700 bg-zinc-900 accent-emerald-500"
              />
            </label>

            <label className="flex items-center justify-between cursor-pointer py-1 border-t border-zinc-850/60">
              <div>
                <span className="font-medium text-zinc-300">
                  Disable history
                </span>
                <p className="text-[11px] text-zinc-500">
                  Do not record runs in local JSON logs
                </p>
              </div>
              <input
                type="checkbox"
                checked={noHistory}
                onChange={(e) => setNoHistory(e.target.checked)}
                className="h-3.5 w-3.5 rounded border-zinc-700 bg-zinc-900 accent-emerald-500"
              />
            </label>

            <label className="flex items-center justify-between cursor-pointer py-1 border-t border-zinc-850/60">
              <div>
                <span className="font-medium text-zinc-300">
                  Self-update checkout
                </span>
                <p className="text-[11px] text-zinc-500">
                  Fast-forward clean Git install before updates
                </p>
              </div>
              <input
                type="checkbox"
                checked={selfUpdate}
                onChange={(e) => setSelfUpdate(e.target.checked)}
                className="h-3.5 w-3.5 rounded border-zinc-700 bg-zinc-900 accent-emerald-500"
              />
            </label>

            <label className="flex items-center justify-between cursor-pointer py-1 border-t border-zinc-850/60">
              <div>
                <span className="font-medium text-zinc-300">
                  Skip on battery
                </span>
                <p className="text-[11px] text-zinc-500">
                  Abort run when laptop is on battery power
                </p>
              </div>
              <input
                type="checkbox"
                checked={skipOnBattery}
                onChange={(e) => setSkipOnBattery(e.target.checked)}
                className="h-3.5 w-3.5 rounded border-zinc-700 bg-zinc-900 accent-emerald-500"
              />
            </label>

            <label className="flex items-center justify-between cursor-pointer py-1 border-t border-zinc-850/60">
              <div>
                <span className="font-medium text-zinc-300">Check network</span>
                <p className="text-[11px] text-zinc-500">
                  Verify network connectivity before updates
                </p>
              </div>
              <input
                type="checkbox"
                checked={checkNetwork}
                onChange={(e) => setCheckNetwork(e.target.checked)}
                className="h-3.5 w-3.5 rounded border-zinc-700 bg-zinc-900 accent-emerald-500"
              />
            </label>
          </div>
        </div>

        {/* Protection & Timeouts */}
        <div className="rounded border border-zinc-800 bg-[#0c0c0e] p-4 space-y-3">
          <div className="flex items-center gap-2 border-b border-zinc-850 pb-2 text-xs font-semibold text-zinc-200">
            <Shield className="h-3.5 w-3.5 text-cyan-400" />
            <span>Protection & Timeouts</span>
          </div>

          <div className="space-y-3 text-xs">
            <label className="flex items-center justify-between cursor-pointer">
              <div>
                <span className="font-medium text-zinc-300">
                  Skip protective snapshots
                </span>
                <p className="text-[11px] text-zinc-500">
                  Disable automatic Snapper or Timeshift snapshot
                </p>
              </div>
              <input
                type="checkbox"
                checked={noSnapshot}
                onChange={(e) => setNoSnapshot(e.target.checked)}
                className="h-3.5 w-3.5 rounded border-zinc-700 bg-zinc-900 accent-emerald-500"
              />
            </label>

            <div className="grid grid-cols-2 gap-3 pt-1">
              <div>
                <label className="block text-[11px] text-zinc-400 font-mono">
                  cooldown_hours
                </label>
                <input
                  type="number"
                  min={0}
                  max={72}
                  value={cooldownHours}
                  onChange={(e) => {
                    const parsed = parseInt(e.target.value, 10);
                    setCooldownHours(
                      Number.isNaN(parsed)
                        ? 0
                        : Math.max(0, Math.min(72, parsed)),
                    );
                  }}
                  className="mt-1 w-full rounded border border-zinc-750 bg-zinc-950 px-2 py-1 font-mono text-xs text-zinc-200 outline-none focus:border-zinc-500"
                />
              </div>

              <div>
                <label className="block text-[11px] text-zinc-400 font-mono">
                  command_timeout (s)
                </label>
                <input
                  type="number"
                  min={30}
                  max={1800}
                  step={30}
                  value={commandTimeout}
                  onChange={(e) =>
                    setCommandTimeout(Number(e.target.value) || 180)
                  }
                  className="mt-1 w-full rounded border border-zinc-750 bg-zinc-950 px-2 py-1 font-mono text-xs text-zinc-200 outline-none focus:border-zinc-500"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Desktop Notifications */}
        <div className="rounded border border-zinc-800 bg-[#0c0c0e] p-4 space-y-3">
          <div className="flex items-center gap-2 border-b border-zinc-850 pb-2 text-xs font-semibold text-zinc-200">
            <Bell className="h-3.5 w-3.5 text-purple-400" />
            <span>Desktop Notifications</span>
          </div>

          <div className="space-y-2 text-xs">
            <label className="flex items-center justify-between cursor-pointer py-1">
              <div>
                <span className="font-medium text-zinc-300">
                  Enable notifications
                </span>
                <p className="text-[11px] text-zinc-500">
                  notify-send or osascript
                </p>
              </div>
              <input
                type="checkbox"
                checked={notifyEnabled}
                onChange={(e) => setNotifyEnabled(e.target.checked)}
                className="h-3.5 w-3.5 rounded border-zinc-700 bg-zinc-900 accent-emerald-500"
              />
            </label>

            {notifyEnabled && (
              <label className="flex items-center justify-between cursor-pointer py-1 border-t border-zinc-850/60">
                <div>
                  <span className="font-medium text-zinc-300">
                    Only on error or reboot
                  </span>
                  <p className="text-[11px] text-zinc-500">
                    Quiet when all updates succeed
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={notifyOnlyOnError}
                  onChange={(e) => setNotifyOnlyOnError(e.target.checked)}
                  className="h-3.5 w-3.5 rounded border-zinc-700 bg-zinc-900 accent-emerald-500"
                />
              </label>
            )}
          </div>
        </div>

        {/* Module Exclusion Manager */}
        <div className="rounded border border-zinc-800 bg-[#0c0c0e] p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-zinc-850 pb-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-zinc-200">
              <Box className="h-3.5 w-3.5 text-emerald-400" />
              <span>Exclude Modules</span>
            </div>
            <span className="font-mono text-[11px] text-zinc-500">
              {disabledModules.size} disabled
            </span>
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Filter module..."
              value={searchModule}
              onChange={(e) => setSearchModule(e.target.value)}
              className="w-full rounded border border-zinc-750 bg-zinc-950 px-2.5 py-1 text-xs text-zinc-200 placeholder-zinc-500 outline-none focus:border-zinc-500 font-mono"
            />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="rounded border border-zinc-800 bg-zinc-900 px-2 py-1 text-[11px] text-zinc-300 outline-none"
            >
              <option value="All">All Categories</option>
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          <div className="max-h-48 overflow-y-auto divide-y divide-zinc-850/60 rounded border border-zinc-800 bg-zinc-950/60 p-1 font-mono text-[11px]">
            {filteredModules.map((m) => {
              const isDisabled = disabledModules.has(m.key);
              return (
                <label
                  key={m.key}
                  className="flex items-center justify-between px-2.5 py-1.5 hover:bg-zinc-900/60 cursor-pointer"
                >
                  <div className="flex items-center gap-2">
                    <span className="text-zinc-200 font-sans">{m.name}</span>
                    <span className="text-zinc-500 text-[10px]">({m.key})</span>
                  </div>
                  <div className="flex items-center gap-2">
                    {isDisabled && (
                      <span className="text-[10px] text-red-400">disabled</span>
                    )}
                    <input
                      type="checkbox"
                      checked={isDisabled}
                      onChange={() => toggleDisableModule(m.key)}
                      className="h-3.5 w-3.5 rounded border-zinc-700 bg-zinc-900 accent-red-500"
                    />
                  </div>
                </label>
              );
            })}
          </div>
        </div>

        {/* Category Filters */}
        <div className="rounded border border-zinc-800 bg-[#0c0c0e] p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-zinc-850 pb-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-zinc-200">
              <Layers className="h-3.5 w-3.5 text-cyan-400" />
              <span>Category Filters</span>
            </div>
            <span className="font-mono text-[11px] text-zinc-500">
              {categoryOnly.size} only / {categorySkip.size} skip
            </span>
          </div>

          <div className="space-y-2 text-[11px]">
            <div>
              <span className="block font-mono text-zinc-400 mb-1.5">only</span>
              <div className="flex flex-wrap gap-1.5">
                {CANONICAL_CATEGORIES.map((cat) => {
                  const active = categoryOnly.has(cat);
                  return (
                    <button
                      key={`only-${cat}`}
                      type="button"
                      onClick={() => toggleCategoryFilter(cat, "only")}
                      className={`rounded border px-2 py-0.5 font-mono transition-colors ${
                        active
                          ? "border-emerald-500/60 bg-emerald-950/50 text-emerald-300"
                          : "border-zinc-800 bg-zinc-950 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
                      }`}
                    >
                      {cat}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="pt-1 border-t border-zinc-850/60">
              <span className="block font-mono text-zinc-400 mb-1.5">skip</span>
              <div className="flex flex-wrap gap-1.5">
                {CANONICAL_CATEGORIES.map((cat) => {
                  const active = categorySkip.has(cat);
                  return (
                    <button
                      key={`skip-${cat}`}
                      type="button"
                      onClick={() => toggleCategoryFilter(cat, "skip")}
                      className={`rounded border px-2 py-0.5 font-mono transition-colors ${
                        active
                          ? "border-red-500/60 bg-red-950/40 text-red-300"
                          : "border-zinc-800 bg-zinc-950 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"
                      }`}
                    >
                      {cat}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* Git Repositories */}
        <div className="rounded border border-zinc-800 bg-[#0c0c0e] p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-zinc-850 pb-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-zinc-200">
              <FolderGit2 className="h-3.5 w-3.5 text-emerald-400" />
              <span>Git Repositories</span>
            </div>
            <span className="font-mono text-[11px] text-zinc-500">
              {gitRepos.length} configured
            </span>
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              placeholder="~/dotfiles or /path/to/repo"
              value={gitRepoInput}
              onChange={(e) => setGitRepoInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleAddGitRepo();
                }
              }}
              className="w-full rounded border border-zinc-750 bg-zinc-950 px-2.5 py-1 text-xs text-zinc-200 placeholder-zinc-500 outline-none focus:border-zinc-500 font-mono"
            />
            <button
              type="button"
              onClick={handleAddGitRepo}
              className="flex items-center gap-1 rounded border border-zinc-750 bg-zinc-800 px-2.5 py-1 text-xs text-zinc-200 hover:bg-zinc-700 transition-colors shrink-0"
            >
              <Plus className="h-3 w-3" />
              <span>Add</span>
            </button>
          </div>

          {gitRepos.length > 0 && (
            <div className="divide-y divide-zinc-850/60 rounded border border-zinc-800 bg-zinc-950/60 font-mono text-[11px]">
              {gitRepos.map((repo) => (
                <div
                  key={repo}
                  className="flex items-center justify-between px-2.5 py-1.5"
                >
                  <span className="text-zinc-300 truncate">{repo}</span>
                  <button
                    type="button"
                    onClick={() =>
                      setGitRepos((prev) => prev.filter((r) => r !== repo))
                    }
                    aria-label={`Remove ${repo}`}
                    className="text-zinc-500 hover:text-red-400 transition-colors ml-2"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Custom Commands */}
        <div className="rounded border border-zinc-800 bg-[#0c0c0e] p-4 space-y-3">
          <div className="flex items-center justify-between border-b border-zinc-850 pb-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-zinc-200">
              <Terminal className="h-3.5 w-3.5 text-purple-400" />
              <span>Custom Commands</span>
            </div>
            <span className="font-mono text-[11px] text-zinc-500">
              {customCommands.length} configured
            </span>
          </div>

          <div className="grid grid-cols-1 gap-2 sm:grid-cols-12">
            <select
              value={cmdPhase}
              onChange={(e) => setCmdPhase(e.target.value as CommandPhase)}
              className="sm:col-span-4 rounded border border-zinc-800 bg-zinc-900 px-2 py-1 text-[11px] font-mono text-zinc-300 outline-none"
            >
              <option value="pre_commands">pre_commands</option>
              <option value="commands">commands</option>
              <option value="post_commands">post_commands</option>
            </select>
            <input
              type="text"
              placeholder="Label (e.g. Refresh cache)"
              value={cmdName}
              onChange={(e) => setCmdName(e.target.value)}
              className="sm:col-span-8 rounded border border-zinc-750 bg-zinc-950 px-2.5 py-1 text-xs text-zinc-200 placeholder-zinc-500 outline-none focus:border-zinc-500"
            />
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              placeholder="Shell command to execute"
              value={cmdExec}
              onChange={(e) => setCmdExec(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  handleAddCustomCommand();
                }
              }}
              className="w-full rounded border border-zinc-750 bg-zinc-950 px-2.5 py-1 text-xs text-zinc-200 placeholder-zinc-500 outline-none focus:border-zinc-500 font-mono"
            />
            <button
              type="button"
              onClick={handleAddCustomCommand}
              className="flex items-center gap-1 rounded border border-zinc-750 bg-zinc-800 px-2.5 py-1 text-xs text-zinc-200 hover:bg-zinc-700 transition-colors shrink-0"
            >
              <Plus className="h-3 w-3" />
              <span>Add</span>
            </button>
          </div>

          {customCommands.length > 0 && (
            <div className="divide-y divide-zinc-850/60 rounded border border-zinc-800 bg-zinc-950/60 font-mono text-[11px]">
              {customCommands.map((entry) => (
                <div
                  key={entry.id}
                  className="flex items-center justify-between gap-2 px-2.5 py-1.5"
                >
                  <div className="min-w-0">
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] text-purple-400">
                        [{entry.phase}]
                      </span>
                      <span className="text-zinc-200 font-sans truncate">
                        {entry.name}
                      </span>
                    </div>
                    <div className="text-[10px] text-zinc-500 truncate">
                      {entry.command}
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={() =>
                      setCustomCommands((prev) =>
                        prev.filter((item) => item.id !== entry.id),
                      )
                    }
                    aria-label={`Remove ${entry.name}`}
                    className="text-zinc-500 hover:text-red-400 transition-colors shrink-0"
                  >
                    <Trash2 className="h-3 w-3" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Live Preview Column */}
      <div className="lg:col-span-6 lg:sticky lg:top-20">
        <div className="overflow-hidden rounded border border-zinc-800 bg-[#0c0c0e] shadow-md">
          <div className="flex items-center justify-between border-b border-zinc-800/80 bg-zinc-900/60 px-3.5 py-2">
            <div className="flex items-center gap-1 rounded bg-zinc-950 p-0.5 border border-zinc-800 font-mono text-[11px]">
              <button
                type="button"
                onClick={() => setPreviewMode("command")}
                className={`flex items-center gap-1 rounded px-2 py-0.5 transition-colors ${
                  previewMode === "command"
                    ? "bg-zinc-850 text-emerald-400 font-medium"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                <Terminal className="h-3 w-3" />
                <span>1-Line Setup</span>
              </button>
              <button
                type="button"
                onClick={() => setPreviewMode("toml")}
                className={`flex items-center gap-1 rounded px-2 py-0.5 transition-colors ${
                  previewMode === "toml"
                    ? "bg-zinc-850 text-white font-medium"
                    : "text-zinc-500 hover:text-zinc-300"
                }`}
              >
                <Settings2 className="h-3 w-3" />
                <span>config.toml</span>
              </button>
            </div>

            <div className="flex items-center gap-1.5">
              <button
                type="button"
                onClick={handleCopy}
                className="flex items-center gap-1 rounded border border-zinc-750 bg-zinc-800 px-2 py-0.5 text-[11px] text-zinc-200 hover:bg-zinc-700 transition-colors"
              >
                {copied ? (
                  <>
                    <Check className="h-3 w-3 text-emerald-400" />
                    <span className="text-emerald-400">Copied</span>
                  </>
                ) : (
                  <>
                    <Copy className="h-3 w-3 text-zinc-400" />
                    <span>
                      {previewMode === "command" ? "Copy Command" : "Copy TOML"}
                    </span>
                  </>
                )}
              </button>

              <button
                type="button"
                onClick={handleDownload}
                className="flex items-center gap-1 rounded border border-emerald-800/60 bg-emerald-950/40 px-2 py-0.5 text-[11px] text-emerald-300 hover:bg-emerald-900/60 transition-colors"
              >
                <Download className="h-3 w-3" />
                <span>Download</span>
              </button>
            </div>
          </div>

          <div className="border-b border-zinc-850 px-3.5 py-1 text-[11px] font-mono text-zinc-500 bg-zinc-950">
            {previewMode === "command"
              ? "Run in terminal to create and write ~/.config/sysupdate/config.toml"
              : "Target: ~/.config/sysupdate/config.toml"}
          </div>

          <pre className="max-h-[580px] overflow-y-auto overflow-x-auto p-3.5 font-mono text-xs leading-relaxed text-zinc-300">
            <code>
              {previewMode === "command" ? generatedBashCommand : generatedToml}
            </code>
          </pre>
        </div>
      </div>
    </div>
  );
}
