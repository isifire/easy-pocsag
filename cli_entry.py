import sys
if __name__ == "__main__":
    if sys.argv[1:2] == ["--self-test"]:
        import json
        import subprocess
        from portable_runtime import tool_path, subprocess_options
        from native_tx import iq_chunks
        for name in ("hackrf_info", "hackrf_transfer"):
            result = subprocess.run([tool_path(name), "-h"], capture_output=True,
                                    timeout=10, **subprocess_options())
            output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
            # Some HackRF releases return 1 for their usage screen.
            if result.returncode != 0 and not (result.returncode == 1 and "usage" in output.lower()):
                raise RuntimeError(f"{name} failed ({result.returncode}): {output}")
        assert b"".join(iq_chunks([1, -1], 2400))
        print(json.dumps({"portable": True, "web_ui": True, "hackrf_tools": True}))
        sys.exit(0)
    from pocsag_sender import main
    main()
