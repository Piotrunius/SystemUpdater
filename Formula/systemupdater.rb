class Systemupdater < Formula
  desc "Modular Linux system updater"
  homepage "https://github.com/Piotrunius/SystemUpdater"
  url "https://github.com/Piotrunius/SystemUpdater/archive/0c74b64bf7d095d2c7291a57cc7112bda6ed1712.tar.gz"
  sha256 "b8dee30ea9eb0a829e956b17f7240bb2c79b31d4413dafc25c9fe295f8a8196e"
  version "0.1.14"
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
