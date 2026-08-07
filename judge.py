"""
judge.py
--------
Minimal multi-language code runner used to power the HackerRank-style
"Run" / "Submit" buttons on the problem solving page.

NOT a hardened container sandbox - it relies on OS resource limits
(CPU time, memory, process count) and subprocess timeouts. Good enough
for a trusted-participant hackathon judge running on a single host;
if you need untrusted-code-safe isolation, run this inside a locked
down container / firejail / gVisor per submission instead.
"""

import os
import shutil
import subprocess
import tempfile
from functools import partial

COMPILE_TIMEOUT_SEC = 15
RUN_MEMORY_LIMIT_MB = 256
MAX_OUTPUT_CHARS = 10000

SUPPORTED_LANGUAGES = ("python3", "c", "cpp", "java")

LANGUAGE_ALIASES = {
    "python": "python3", "py": "python3", "python3": "python3",
    "c": "c",
    "cpp": "cpp", "c++": "cpp",
    "java": "java",
}


def normalize_language(language):
    return LANGUAGE_ALIASES.get((language or "").lower().strip())


def _limit_resources(cpu_seconds):
    """preexec_fn applied to compiled-native / python child processes only."""
    try:
        import resource
        mem_bytes = RUN_MEMORY_LIMIT_MB * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
        resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
        resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
        resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))
    except Exception:
        pass


def run_code(language, source_code, stdin_text="", time_limit_sec=2):
    """
    Compiles (if needed) and executes `source_code` with `stdin_text` fed to stdin.
    Single-shot convenience wrapper (compile + run once + cleanup) - used by
    the "Run" button which only ever executes one input at a time.

    Returns dict:
        stdout, stderr (str)
        timed_out (bool)
        compile_error (str or None)
        returncode (int or None)
    """
    prepared = prepare(language, source_code)
    if prepared.get("compile_error"):
        return {"stdout": "", "stderr": "", "timed_out": False,
                "compile_error": prepared["compile_error"], "returncode": None}
    try:
        return run_prepared(prepared, stdin_text, time_limit_sec)
    finally:
        cleanup(prepared)


def prepare(language, source_code):
    """
    Writes and compiles (if needed) `source_code` ONCE into a fresh work_dir.
    Use this + run_prepared() in a loop when running many test cases against
    the same submission (e.g. Submit), instead of calling run_code() per
    test case, which would otherwise recompile C/C++/Java from scratch for
    every single test case.

    Returns dict:
        work_dir (str)
        run_cmd (list[str] or None)
        limit_cpu (bool)
        compile_error (str or None)
    """
    lang = normalize_language(language)
    result = {"work_dir": None, "run_cmd": None, "limit_cpu": True, "compile_error": None}

    if not lang:
        result["compile_error"] = f"Unsupported language: {language!r}"
        return result

    work_dir = tempfile.mkdtemp(prefix="judge_")
    result["work_dir"] = work_dir

    if lang == "python3":
        _write(os.path.join(work_dir, "main.py"), source_code)
        result["run_cmd"] = ["python3", "main.py"]

    elif lang == "c":
        _write(os.path.join(work_dir, "main.c"), source_code)
        ok, err = _compile(["gcc", "-O2", "-o", "main.out", "main.c"], work_dir)
        if not ok:
            result["compile_error"] = err
            return result
        result["run_cmd"] = ["./main.out"]

    elif lang == "cpp":
        _write(os.path.join(work_dir, "main.cpp"), source_code)
        ok, err = _compile(["g++", "-O2", "-std=c++17", "-o", "main.out", "main.cpp"], work_dir)
        if not ok:
            result["compile_error"] = err
            return result
        result["run_cmd"] = ["./main.out"]

    elif lang == "java":
        # Starter code must declare: public class Main
        _write(os.path.join(work_dir, "Main.java"), source_code)
        ok, err = _compile(["javac", "Main.java"], work_dir)
        if not ok:
            result["compile_error"] = err
            return result
        # JVM reserves a lot of virtual address space at boot, so we do NOT
        # apply RLIMIT_AS here - -Xmx enforces the heap cap instead.
        result["run_cmd"] = ["java", "-Xmx256m", "-cp", ".", "Main"]
        result["limit_cpu"] = False

    return result


def run_prepared(prepared, stdin_text="", time_limit_sec=2):
    """Executes an already-compiled `prepared` result (from prepare()) against
    one input. Call this once per test case, reusing the same `prepared`."""
    time_limit_sec = max(1, min(float(time_limit_sec or 2), 15))
    return _execute(
        prepared["run_cmd"], stdin_text, time_limit_sec,
        prepared["work_dir"], limit_cpu=prepared.get("limit_cpu", True)
    )


def cleanup(prepared):
    """Removes the work_dir created by prepare(). Always call this once
    you're done running all test cases for a submission."""
    work_dir = prepared.get("work_dir")
    if work_dir:
        shutil.rmtree(work_dir, ignore_errors=True)


def _write(path, content):
    with open(path, "w") as f:
        f.write(content or "")


def _compile(cmd, cwd):
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                               timeout=COMPILE_TIMEOUT_SEC)
        if proc.returncode != 0:
            return False, (proc.stderr or "Compilation failed")[-4000:]
        return True, None
    except subprocess.TimeoutExpired:
        return False, "Compilation timed out"
    except FileNotFoundError as e:
        return False, f"Compiler not available on server ({e})"


def _execute(cmd, stdin_text, time_limit_sec, cwd, limit_cpu=True):
    preexec = None
    if os.name == "posix" and limit_cpu:
        preexec = partial(_limit_resources, int(time_limit_sec) + 2)

    try:
        proc = subprocess.run(
            cmd,
            input=stdin_text or "",
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=time_limit_sec,
            preexec_fn=preexec,
        )
        return {
            "stdout": (proc.stdout or "")[-MAX_OUTPUT_CHARS:],
            "stderr": (proc.stderr or "")[-MAX_OUTPUT_CHARS:],
            "returncode": proc.returncode,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Time Limit Exceeded", "returncode": None, "timed_out": True}
    except Exception as e:
        return {"stdout": "", "stderr": f"Runtime error: {e}", "returncode": None, "timed_out": False}
