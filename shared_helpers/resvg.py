import subprocess
import logging

log = logging.getLogger(__name__)


def render_svg(input: str, outpath: str, resvg_path: str) -> bool:
    """
    Uses resvg to render an SVG string to a PNG file.

    :param input: A templated SVG string
    :param outpath: The full path, including the filename, to write the PNG.
    :return: True if successful; else False.
    """
    command = [
        resvg_path,
        "--background", "white",
        "-",
        outpath,
    ]
    proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    stdout, stderr = proc.communicate(input=input.encode())
    print(stdout, stderr)
    return proc.returncode >= 0


