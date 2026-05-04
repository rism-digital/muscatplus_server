import subprocess  # noqa: S404

from sanic.log import logger


def render_svg(
    svginput: str, outpath: str, resvg_path: str, font_path: str, zoom_factor: str = "1"
) -> bool:
    """
    Uses resvg to render an SVG string to a PNG file.

    :param svginput: A templated SVG string
    :param outpath: The full path, including the filename, to write the PNG.
    :param resvg_path: The path to the resvg binary
    :param font_path: The path to the fonts to use when rendering
    :param zoom_factor: The zoom factor to use when rendering
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
    # resvg path and font directory are loaded from trusted server configuration.
    proc = subprocess.run(  # noqa: S603
        command,
        input=svginput.encode(),
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        logger.error(
            "resvg failed with exit code %s; stdout=%s stderr=%s",
            proc.returncode,
            proc.stdout,
            proc.stderr,
        )
        return False

    logger.debug("Rendered incipit to PNG")
    return True
