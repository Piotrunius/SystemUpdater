class Systemupdater < Formula
  desc "Modular Linux system updater"
  homepage "https://github.com/Piotrunius/SystemUpdater"
  url "https://github.com/Piotrunius/SystemUpdater/archive/65d1c7852b1fd200af227640c71ae6a66239e94a.tar.gz"
  sha256 "80468c78aa326b37a1c392b7136ea0d6f70687ab2c2f069902602a1dbe2b63bd"
  version "1.2.1"
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
