import logging
import subprocess  # noqa: S404

log = logging.getLogger("mp_server")


def render_svg(
    svginput: str, outpath: str, resvg_path: str, font_path: str, zoom_factor: str = "1"
) -> bool:
    """
    Uses resvg to render an SVG string to a PNG file.

    :param svginput: A templated SVG string
    :param outpath: The full path, including the filename, to write the PNG.
    :param resvg_path: The path to the resvg binary
    :param font_path: The path to the fonts to use when rendering
    :return: True if successful; else False.
    """
    command = [
        resvg_path,
        "--background",
        "white",
        "--zoom",
        zoom_factor,
        "--skip-system-fonts",
        "--use-fonts-dir",
        f"{font_path}",
        "--monospace-family",
        "Noto Sans Mono",
        "--sans-serif-family",
        "Noto Sans Display",
        "--resources-dir",
        f"{font_path}",
        "-",
        outpath,
    ]
    proc = subprocess.Popen(  # noqa: S603
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    )
    stdout, stderr = proc.communicate(input=svginput.encode())
    log.info("%s, %s", stdout, stderr)
    return proc.returncode >= 0
