"""Punto de entrada de MailPilot (también se usa para crear MailPilot.exe con PyInstaller)."""

from suite.selftest import maybe_run

if __name__ == "__main__":
    maybe_run("mailpilot")  # MailPilot.exe --selftest
    from suite.mailpilot.app import main

    main()
