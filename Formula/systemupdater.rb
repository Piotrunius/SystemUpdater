class Systemupdater < Formula
  desc "Modular Linux system updater"
  homepage "https://github.com/Piotrunius/SystemUpdater"
  url "https://github.com/Piotrunius/SystemUpdater/archive/9bdd7f3f272ee83c89b465e4c75e4577fd64e7eb.tar.gz"
  sha256 "3ae39975fbcdd6271cd5ecaeeb35670f74c423c6ced4562f7f93449e0dd154d5"
  version "0.2.0"
  license "MIT"

  depends_on "python@3.14"

  def install
    libexec.install Dir["*.py"]
    libexec.install "modules"
    (libexec/".homebrew-install").write("homebrew\n")
    (libexec/"VERSION").write("#{version}\n")

    python = Formula["python@3.14"].opt_bin/"python3.14"
    (bin/"sysupdate").write <<~EOS
      #!/bin/bash
      exec "#{python}" "#{libexec}/main.py" "$@"
    EOS
  end

  test do
    output = shell_output("#{bin}/sysupdate --version")
    assert_match "Installed version: #{version}", output
  end
end
