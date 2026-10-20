"""Punto de entrada de FraudPilot (también se usa para crear FraudPilot.exe con PyInstaller)."""

from suite.selftest import maybe_run

if __name__ == "__main__":
    maybe_run("fraudpilot")  # FraudPilot.exe --selftest
    from suite.fraudpilot.app import main

    main()
