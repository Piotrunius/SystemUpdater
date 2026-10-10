class Systemupdater < Formula
  desc "Modular Linux system updater"
  homepage "https://github.com/Piotrunius/SystemUpdater"
  url "https://github.com/Piotrunius/SystemUpdater/archive/adaf2a9af8ff31f82b03a9f925d58a71dfefbba0.tar.gz"
  sha256 "2609eb6e0b77e1fe0b6ff8076b0ae19582e8473fd1192346d508f9b3819aa4f9"
  version "0.1.11"
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
