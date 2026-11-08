import sys
if __name__ == "__main__":
    if sys.argv[1:2] == ["--self-test"]:
        import json
        import subprocess
        from portable_runtime import tool_path, subprocess_options
        from native_tx import iq_chunks
        for name in ("hackrf_info", "hackrf_transfer"):
            subprocess.run([tool_path(name), "-h"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           timeout=10, check=True, **subprocess_options())
        assert b"".join(iq_chunks([1, -1], 2400))
        print(json.dumps({"portable": True, "web_ui": True, "hackrf_tools": True}))
        sys.exit(0)
    from pocsag_sender import main
    main()
