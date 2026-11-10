"use client";

import { useState, useMemo } from "react";
import { ModuleMeta } from "@/types/metadata";
import { ModuleCard } from "./ModuleCard";
import { Search, X, LayoutGrid, List } from "lucide-react";

interface ModuleCatalogProps {
  modules: ModuleMeta[];
  categories: string[];
}

export function ModuleCatalog({ modules, categories }: ModuleCatalogProps) {
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("All");
  const [selectedPlatform, setSelectedPlatform] = useState<string>("All");
  const [sudoFilter, setSudoFilter] = useState<string>("All");
  const [viewMode, setViewMode] = useState<"table" | "grid">("table");

  const filteredModules = useMemo(() => {
    return modules.filter((m) => {
      const q = search.toLowerCase();
      const matchesSearch =
        !search ||
        m.name.toLowerCase().includes(q) ||
        m.key.toLowerCase().includes(q) ||
        m.description.toLowerCase().includes(q) ||
        m.aliases.some((a) => a.toLowerCase().includes(q));

      const matchesCategory =
        selectedCategory === "All" || m.category === selectedCategory;

      const matchesPlatform =
        selectedPlatform === "All" ||
        m.platform === selectedPlatform.toLowerCase() ||
        (selectedPlatform !== "All" && m.platform === "universal");

      const matchesSudo =
        sudoFilter === "All" ||
        (sudoFilter === "Requires Sudo" && m.requires_sudo) ||
        (sudoFilter === "Unprivileged" && !m.requires_sudo);

      return matchesSearch && matchesCategory && matchesPlatform && matchesSudo;
    });
  }, [modules, search, selectedCategory, selectedPlatform, sudoFilter]);

  const clearFilters = () => {
    setSearch("");
    setSelectedCategory("All");
    setSelectedPlatform("All");
    setSudoFilter("All");
  };

  const hasActiveFilters =
    search !== "" ||
    selectedCategory !== "All" ||
    selectedPlatform !== "All" ||
    sudoFilter !== "All";

  return (
    <div className="space-y-4">
      {/* Search & Filter Bar */}
      <div className="flex flex-col gap-3 rounded border border-zinc-800 bg-[#0c0c0e] p-3">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-zinc-500" />
            <input
              type="text"
              placeholder="Search by name, key, command (e.g. pacman, docker, rustup)..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full rounded border border-zinc-750 bg-zinc-950 py-1.5 pl-8 pr-8 text-xs text-zinc-200 placeholder-zinc-500 outline-none focus:border-zinc-500 font-mono"
            />
            {search && (
              <button
                type="button"
                onClick={() => setSearch("")}
                className="absolute right-2.5 top-2 text-zinc-500 hover:text-zinc-300"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            )}
          </div>

          <div className="flex items-center gap-1 rounded border border-zinc-800 bg-zinc-900 p-0.5">
            <button
              type="button"
              onClick={() => setViewMode("table")}
              aria-label="Table view"
              className={`rounded p-1 transition-colors ${
                viewMode === "table"
                  ? "bg-zinc-800 text-white"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              <List className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={() => setViewMode("grid")}
              aria-label="Grid view"
              className={`rounded p-1 transition-colors ${
                viewMode === "grid"
                  ? "bg-zinc-800 text-white"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              <LayoutGrid className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="rounded border border-zinc-800 bg-zinc-900 px-2 py-1 text-[11px] text-zinc-300 outline-none"
            >
              <option value="All">All Categories ({modules.length})</option>
              {categories.map((cat) => (
                <option key={cat} value={cat}>
                  {cat}
                </option>
              ))}
            </select>

            <select
              value={selectedPlatform}
              onChange={(e) => setSelectedPlatform(e.target.value)}
              className="rounded border border-zinc-800 bg-zinc-900 px-2 py-1 text-[11px] text-zinc-300 outline-none"
            >
              <option value="All">All Platforms</option>
              <option value="Linux">Linux</option>
              <option value="macOS">macOS</option>
              <option value="Universal">Universal</option>
            </select>

            <select
              value={sudoFilter}
              onChange={(e) => setSudoFilter(e.target.value)}
              className="rounded border border-zinc-800 bg-zinc-900 px-2 py-1 text-[11px] text-zinc-300 outline-none"
            >
              <option value="All">All Privileges</option>
              <option value="Requires Sudo">Requires Sudo</option>
              <option value="Unprivileged">Unprivileged (No sudo)</option>
            </select>

            {hasActiveFilters && (
              <button
                type="button"
                onClick={clearFilters}
                className="text-[11px] text-zinc-400 hover:text-zinc-200 underline underline-offset-2 ml-1"
              >
                Reset
              </button>
            )}
          </div>

          <span className="font-mono text-[11px] text-zinc-500">
            {filteredModules.length} of {modules.length} modules
          </span>
        </div>
      </div>

      {/* Content Rendering: Table or Grid */}
      {filteredModules.length > 0 ? (
        viewMode === "table" ? (
          <div className="overflow-hidden rounded border border-zinc-800 bg-[#0c0c0e]">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="border-b border-zinc-800 bg-zinc-900/60 font-mono text-[10px] text-zinc-400 uppercase tracking-wider">
                  <tr>
                    <th className="px-3.5 py-2.5 font-semibold">Tool</th>
                    <th className="px-3.5 py-2.5 font-semibold">Key</th>
                    <th className="px-3.5 py-2.5 font-semibold">Category</th>
                    <th className="px-3.5 py-2.5 font-semibold">Privileges</th>
                    <th className="px-3.5 py-2.5 font-semibold">Platform</th>
                    <th className="px-3.5 py-2.5 font-semibold">Description</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-850">
                  {filteredModules.map((m) => (
                    <tr
                      key={m.key}
                      className="hover:bg-zinc-900/40 transition-colors font-mono text-[11px]"
                    >
                      <td className="px-3.5 py-2 text-zinc-100 font-sans font-medium whitespace-nowrap">
                        {m.name}
                      </td>
                      <td className="px-3.5 py-2 text-emerald-400 whitespace-nowrap">
                        {m.key}
                      </td>
                      <td className="px-3.5 py-2 text-zinc-400 font-sans text-xs whitespace-nowrap">
                        {m.category}
                      </td>
                      <td className="px-3.5 py-2 whitespace-nowrap">
                        {m.requires_sudo ? (
                          <span className="text-amber-400 font-medium">
                            sudo
                          </span>
                        ) : (
                          <span className="text-zinc-500">user</span>
                        )}
                      </td>
                      <td className="px-3.5 py-2 whitespace-nowrap text-zinc-400">
                        {m.platform}
                      </td>
                      <td className="px-3.5 py-2 text-zinc-400 font-sans text-xs max-w-md truncate">
                        {m.description || "Package and tool update routine"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {filteredModules.map((module) => (
              <ModuleCard key={module.key} module={module} />
            ))}
          </div>
        )
      ) : (
        <div className="rounded border border-dashed border-zinc-800 py-10 text-center text-xs text-zinc-500">
          No modules match your filter.
        </div>
      )}
    </div>
  );
}
