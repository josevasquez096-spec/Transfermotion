"""Punto de entrada de SlidePilot (también se usa para crear SlidePilot.exe con PyInstaller)."""

from suite.selftest import maybe_run

if __name__ == "__main__":
    maybe_run("slidepilot")  # SlidePilot.exe --selftest
    from suite.slidepilot.app import main

    main()
