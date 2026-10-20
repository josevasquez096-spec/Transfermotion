"""Punto de entrada de IcePilot (también se usa para crear IcePilot.exe con PyInstaller)."""

from suite.selftest import maybe_run

if __name__ == "__main__":
    maybe_run("icepilot")  # IcePilot.exe --selftest
    from suite.icepilot.app import main

    main()
