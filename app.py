"""Portable entry point: web UI by default, CLI when requested."""
import sys
if __name__ == "__main__":
    if sys.argv[1:2] == ["--cli"]:
        del sys.argv[1]
        from pocsag_sender import main
    else:
        from web_app import main
    main()
