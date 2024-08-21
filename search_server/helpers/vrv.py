import logging
import os
import re
import tempfile
import urllib.parse
from typing import Optional

import aiohttp
import verovio
from orjson import orjson

from shared_helpers.resvg import render_svg
from shared_helpers.identifiers import ID_SUB, get_identifier

log = logging.getLogger("mp_server")
verovio.enableLog(False)
VEROVIO_BASE_OPTIONS: dict = {
    "footer": "none",
    "header": "none",
    "breaks": "auto",
    "pageMarginTop": 15,
    "pageMarginBottom": 15,
    "spacingSystem": 2,
    "pageMarginLeft": 0,
    "pageMarginRight": 0,
    "ligatureAsBracket": True,
    # "adjustPageWidth": "true",
    "pageWidth": 2000,
    "scale": 40,
    "adjustPageHeight": True,
    "svgHtml5": True,
    "svgFormatRaw": True,
    "svgRemoveXlink": True,
    "svgViewBox": True,
    "paeFeatures": True,
    "xmlIdSeed": 1,
}

vrv_tk = verovio.toolkit()
vrv_tk.setOptions(VEROVIO_BASE_OPTIONS)


def render_pae(
    pae: str, use_crc: bool = False, enlarged: bool = False, is_mensural: bool = False
) -> Optional[tuple]:
    """
    Renders Plaine and Easie to SVG and MIDI. Returns None if there was a problem loading the data.

    If use_crc is True, then the IDs will be generated using a CRC32 checksum of the input data. If not,
    then the IDs will be randomly generated.

    :param pae: A plaine and easie-formatted input string
    :param use_crc: The ID seed to use for Verovio's ID generator
    :return: A named tuple containing SVG and MIDI.
    """
    custom_options: dict = {"xmlIdChecksum": use_crc}

    if not use_crc:
        vrv_tk.resetXmlIdSeed(0)

    if enlarged:
        custom_options["pageWidth"] = 1200
    else:
        custom_options["pageWidth"] = 2000

    if is_mensural:
        custom_options["spacingLinear"] = 0.4
        custom_options["spacingNonLinear"] = 0.4
    else:
        # Default Verovio values (for CWMN)
        custom_options["spacingLinear"] = 0.25
        custom_options["spacingNonLinear"] = 0.6

    vrv_tk.setInputFrom("pae")
    vrv_tk.setOptions(custom_options)

    load_status: bool = vrv_tk.loadData(pae)

    # If loading failed, return None
    if not load_status:
        return None

    svg: str = vrv_tk.renderToSVG()
    mid: str = vrv_tk.renderToMIDI()
    # The toolkit has `paeFeatures=True` so this will output the PAE features
    b64midi = f"data:audio/midi;base64,{mid}"

    return svg, b64midi


async def render_url(url: str) -> Optional[str]:
    """
    Takes a URL to an MEI file and returns the SVG for it.

    :param url:
    :param custom_options:
    :return:
    """
    async with aiohttp.ClientSession() as client:
        try:
            res = await client.get(url)
        except aiohttp.ClientConnectionError as err:
            log.error("Connection to server timed out for %s", url)
            return None
        except aiohttp.ClientError as err:
            log.error("Unknown connection error for %s", url)
            return None

        if res.status != 200:
            log.error("Server responded with non-success status code: %s", res.status)
            return None

        mei: str = await res.text()
        vrv_opts: dict = VEROVIO_BASE_OPTIONS.copy()
        vrv_opts.update(
            {
                "pageWidth": 1000,
            }
        )
        vrv_tk.setOptions(vrv_opts)
        vrv_tk.setInputFrom("mei")
        load_status: bool = vrv_tk.loadData(mei)

        if not load_status:
            log.error("Verovio could not load file %s", url)
            return None

        svg: str = vrv_tk.renderToSVG()

        return svg


def render_mei(req, incipit: dict) -> Optional[str]:
    """
    Renders an MEI result from PAE input. Includes information for the MEI header
    in the `x-header` section.

    :param incipit: A Solr result of an incipit record
    :return: The MEI encoded as a string, or None if there was a problem loading
    """
    vrv_opts: dict = VEROVIO_BASE_OPTIONS.copy()
    vrv_tk.setOptions(vrv_opts)
    vrv_tk.setInputFrom("pae")

    source_id: str = re.sub(ID_SUB, "", incipit["source_id"])
    work_num: str = incipit["work_num_s"]

    source_url: str = get_identifier(req, "sources.source", source_id=source_id)
    incipit_url: str = get_identifier(
        req, "sources.incipit_mei_encoding", source_id=source_id, work_num=work_num
    )

    metadata_header: dict = {"source_url": source_url, "download_url": incipit_url}

    if t := incipit.get("titles_sm", []):
        metadata_header["title"] = " ".join(t)
    if c := incipit.get("creator_name_s"):
        metadata_header["composer"] = c
    if sc := incipit.get("scoring_sm", []):
        metadata_header["scoring"] = ", ".join(sc)
    if st := incipit.get("main_title_s"):
        metadata_header["source_title"] = st
    if nt := incipit.get("general_notes_sm", []):
        metadata_header["notes"] = nt
    if vi := incipit.get("voice_instrument_s"):
        metadata_header["voice_instrument"] = vi
    if mv := incipit.get("work_num_s"):
        metadata_header["movement"] = mv

    pae: dict = {
        "x-header": metadata_header,  # TBD
        "clef": incipit.get("clef_s", ""),
        "keysig": incipit.get("key_s", ""),
        "timesig": incipit.get("timesit_s", ""),
        "data": incipit.get("music_incipit_s", ""),
    }

    load_status: bool = vrv_tk.loadData(orjson.dumps(pae).decode("utf8"))
    if not load_status:
        incipit_id: str = incipit["id"]
        log.error("Verovio could transform incipit %s to MEI", incipit_id)
        return None

    mei: str = vrv_tk.getMEI()
    return mei


def render_png(req, incipit: str) -> Optional[bytes]:
    rendered_svg, _ = render_pae(incipit)
    cfg: dict = req.app.ctx.config
    # Create the temporary image file
    fd, tmpfile = tempfile.mkstemp()

    render_success: bool = render_svg(
        rendered_svg,
        tmpfile,
        cfg["social"]["resvg"],
        cfg["social"]["font_path"],
        zoom_factor="2",
    )
    if not render_success:
        log.error("There was a problem rendering an SVG!")
        return None

    # The tempfile should have the PNG data in it now.
    with os.fdopen(fd, "rb") as t:
        pngdata: bytes = t.read()

    # we need to manually remove the temporary file.
    os.unlink(tmpfile)

    return pngdata


def create_pae_from_request(req) -> str:
    """
    Takes an incoming incipit request and extracts the parameters (if present)
    for adjusting the PAE output.

    :param req: A request object

    :return: A string containing PAE for handing off to Verovio to render.
    """
    raw_notedata: str = req.args.get("n", "")
    # Unencode spaces, etc.
    unquoted_notedata: str = urllib.parse.unquote(raw_notedata)
    # Since "+" is a meaningful character in URLs, both "+" and "_" can be encoded with an underscore (_) when
    # passed along in the URL. This regex will insert the "+" back into the PAE string until the PAE spec is
    # updated to allow "_" for ties.
    notedata: str = re.sub("_", "+", unquoted_notedata)

    # Clefs can also contain plus symbols indicating mensural notation
    raw_clef: str = req.args.get("ic", "G-2")
    clef: str = urllib.parse.unquote(raw_clef)

    timesig: str = req.args.get("it", "")
    keysig: str = req.args.get("ik", "")
    music_data = notedata if notedata.endswith("/") else f"{notedata}/"

    pae_elements: list = []

    if clef:
        pae_elements.append(f"@clef:{clef}")
    if keysig:
        pae_elements.append(f"@keysig:{keysig}")
    if timesig:
        pae_elements.append(f"@timesig:{timesig}")
    pae_elements.append(f"@data:{music_data}")

    return "\n".join(pae_elements)


def get_pae_features(req) -> Optional[dict]:
    """
    Parses an incoming search request containing some note data and some
    optional parameters, and returns a dictionary containing the PAE features.

    Note that if Verovio cannot parse the notation it will still return a dictionary
    with the expected keys, but the list of features will be empty.
    """
    vrv_tk.resetXmlIdSeed(0)
    pae: str = create_pae_from_request(req)
    vrv_tk.setInputFrom("pae")
    load_success: bool = vrv_tk.loadData(pae)
    if load_success is False:
        log.warning("Could not load PAE for %s", pae)
        return None
    return vrv_tk.getDescriptiveFeatures({})


def _find_err_msg(needle: str, transl_haystack: dict[str, dict]) -> dict:
    for k, v in transl_haystack.items():
        if k.startswith(needle):
            return v
    return {}


def validate_pae(req) -> dict:
    vrv_tk.resetXmlIdSeed(0)
    pae: str = create_pae_from_request(req)
    vrv_tk.setInputFrom("pae")
    validation_output: dict = vrv_tk.validatePAE(pae)

    if "data" not in validation_output:
        return {"valid": True}

    transl: dict = req.ctx.translations

    validation_data: list = validation_output["data"]
    translated_messages: list = []

    for message in validation_data:
        code: int = message.get("code")
        err_needle: str = f"verovio.ERR_{code:03}"
        error_msg: dict = _find_err_msg(err_needle, transl)
        translated_messages.append({"value": error_msg})

    return {"valid": False, "messages": translated_messages}
