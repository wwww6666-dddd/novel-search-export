"""
Post-processing cleanup: organize output files and isolate temp files.

Usage:
    python cleanup.py <work_dir>
    python cleanup.py D:\灏忚
"""

import os, shutil, sys

def organize_output(work_dir):
    """Organize output files into 灏忚/ and 宸ュ叿/ directories."""
    output_dir = os.path.join(work_dir, "灏忚")
    tool_dir = os.path.join(work_dir, "宸ュ叿")

    # Create target directories
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(tool_dir, exist_ok=True)

    # Rename legacy _output to 灏忚
    legacy_output = os.path.join(work_dir, "_output")
    if os.path.exists(legacy_output) and not os.path.exists(output_dir):
        os.rename(legacy_output, output_dir)

    # Move legacy directories into 宸ュ叿
    for old_name in ["_scripts", "_temp", "_cache"]:
        old_path = os.path.join(work_dir, old_name)
        if os.path.exists(old_path) and os.path.isdir(old_path):
            for fname in os.listdir(old_path):
                src = os.path.join(old_path, fname)
                dst = os.path.join(tool_dir, fname)
                if os.path.isfile(src):
                    shutil.move(src, dst)
            os.rmdir(old_path)

    # Move stray files in root to 宸ュ叿 (except .docx and the two folders)
    for fname in os.listdir(work_dir):
        fpath = os.path.join(work_dir, fname)
        if not os.path.isfile(fpath):
            continue
        # Keep only .docx files in root
        if fname.endswith(".docx"):
            dst = os.path.join(output_dir, fname)
            shutil.move(fpath, dst)
        else:
            dst = os.path.join(tool_dir, fname)
            # Avoid overwrite
            if os.path.exists(dst):
                base, ext = os.path.splitext(fname)
                dst = os.path.join(tool_dir, f"{base}_{id(fpath)}{ext}")
            shutil.move(fpath, dst)

    # Report
    out_count = len([f for f in os.listdir(output_dir) if os.path.isfile(os.path.join(output_dir, f))])
    tool_count = len([f for f in os.listdir(tool_dir) if os.path.isfile(os.path.join(tool_dir, f))])
    print(f"Organized: {out_count} docx in 灏忚/, {tool_count} files in 宸ュ叿/")

if __name__ == "__main__":
    work_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    organize_output(work_dir)