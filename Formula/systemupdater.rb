class Systemupdater < Formula
  desc "Modular Linux system updater"
  homepage "https://github.com/Piotrunius/SystemUpdater"
  url "https://github.com/Piotrunius/SystemUpdater/archive/84204a14553a5f1d9cf2f7a93e6b97b2cb3df0b9.tar.gz"
  sha256 "f28e8775714ff7d15077e4667415091e0bed95f7db29b315e7e069d4d568b368"
  version "0.1.10"
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
