export type Platform = "linux" | "macos" | "universal";

export interface ModuleMeta {
  key: string;
  name: string;
  aliases: string[];
  category: string;
  description: string;
  requires_sudo: boolean;
  unit_name: string;
  unit_name_plural: string;
  platform: Platform;
}

export interface CliFlag {
  flags: string[];
  description: string;
  category: string;
}

export interface Metadata {
  generated_at_comment: string;
  modules: ModuleMeta[];
  categories: string[];
  cli_flags: CliFlag[];
}
