"""Punto de entrada de MoreInfo Pilot (también se usa para crear MoreInfoPilot.exe con PyInstaller)."""

from suite.selftest import maybe_run

if __name__ == "__main__":
    maybe_run("moreinfo")  # MoreInfoPilot.exe --selftest
    from suite.moreinfo.app import main

    main()
