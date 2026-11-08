"""Private command-line worker and hardware-independent portable checks."""
import sys


def self_test():
    import subprocess
    from portable_runtime import tool_path, subprocess_options
    from native_tx import iq_chunks
    hardware_detected = False
    for name in ("hackrf_info", "hackrf_transfer"):
        result = subprocess.run([tool_path(name), "-h"], capture_output=True,
                                timeout=10, **subprocess_options())
        output = (result.stdout + result.stderr).decode("utf-8", errors="replace")
        text = output.lower()
        # hackrf_info ignores -h on some releases and probes USB instead.
        no_device = (name == "hackrf_info" and result.returncode == 1
                     and "no hackrf boards found" in text and "libhackrf version" in text)
        usage = result.returncode == 1 and "usage" in text
        if result.returncode != 0 and not (no_device or usage):
            raise RuntimeError(f"{name} failed ({result.returncode}): {output}")
        if name == "hackrf_info":
            hardware_detected = "serial number" in text
    assert b"".join(iq_chunks([1, -1], 2400))
    return {"portable": True, "web_ui": True, "hackrf_tools": True, "hardware_detected": hardware_detected}


if __name__ == "__main__":
    if sys.argv[1:2] == ["--self-test"]:
        import json
        print(json.dumps(self_test()))
        sys.exit(0)
    from pocsag_sender import main
    main()
