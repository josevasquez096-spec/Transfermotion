"""Punto de entrada de BIPilot (también se usa para crear BIPilot.exe con PyInstaller)."""

from suite.selftest import maybe_run

if __name__ == "__main__":
    maybe_run("bipilot")  # BIPilot.exe --selftest
    from suite.bipilot.app import main

    main()
