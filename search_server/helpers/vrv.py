import logging
import re
import urllib.parse
from typing import Optional

import ujson
import verovio

log = logging.getLogger(__name__)
verovio.enableLog(False)


log.info("Instantiating Verovio")
vrv_tk = verovio.toolkit()

vrv_tk.setInputFrom(verovio.PAE)
vrv_tk.setOptions(ujson.dumps({
    "footer": 'none',
    "header": 'none',
    "breaks": 'auto',
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
    "xmlIdSeed": 1
}))


def render_pae(pae: str, use_crc: bool = False, enlarged: bool = False, is_mensural: bool = False) -> Optional[tuple]:
    """
    Renders Plaine and Easie to SVG and MIDI. Returns None if there was a problem loading the data.

    If use_crc is True, then the IDs will be generated using a CRC32 checksum of the input data. If not,
    then the IDs will be randomly generated.

    :param pae: A plaine and easie-formatted input string
    :param use_crc: The ID seed to use for Verovio's ID generator
    :return: A named tuple containing SVG and MIDI.
    """
    custom_options: dict = {}

    if use_crc:
        custom_options["xmlIdChecksum"] = True
    else:
        custom_options["xmlIdChecksum"] = False
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

    vrv_tk.setOptions(ujson.dumps(custom_options))

    load_status: bool = vrv_tk.loadData(pae)

    # If loading failed, return None
    if not load_status:
        return None

    svg: str = vrv_tk.renderToSVG()
    mid: str = vrv_tk.renderToMIDI()
    # The toolkit has `paeFeatures=True` so this will output the PAE features
    b64midi = f"data:audio/midi;base64,{mid}"

    return svg, b64midi


def create_pae_from_request(req) -> str:
    """
    Takes an incoming incipit request and extracts the parameters (if present)
    for adjusting the PAE output.

    :param req: A request object
    :param notedata: The PAE note data.

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


def get_pae_features(req) -> dict:
    """
        Parses an incoming search request containing some note data and some
        optional parameters, and returns a dictionary containing the PAE features.

        Note that if Verovio cannot parse the notation it will still return a dictionary
        with the expected keys, but the list of features will be empty.
    """
    vrv_tk.resetXmlIdSeed(0)
    pae: str = create_pae_from_request(req)
    vrv_tk.loadData(pae)
    features: str = vrv_tk.getDescriptiveFeatures("{}")

    feat_output: dict = ujson.loads(features)

    return feat_output


def _find_err_msg(needle: str, transl_haystack: dict[str, dict]) -> dict:
    for k, v in transl_haystack.items():
        if k.startswith(needle):
            return v
    return {}


def validate_pae(req) -> dict:
    vrv_tk.resetXmlIdSeed(0)
    pae: str = create_pae_from_request(req)
    validation: str = vrv_tk.validatePAE(pae)
    validation_output: dict = ujson.loads(validation)

    if "data" not in validation_output:
        return {
            "valid": True
        }

    transl: dict = req.app.ctx.translations

    validation_output: list = validation_output["data"]
    translated_messages: list = []

    for message in validation_output:
        code: int = message.get("code")
        err_needle: str = f"verovio.ERR_{code:03}"
        error_msg: dict = _find_err_msg(err_needle, transl)
        translated_messages.append({"value": error_msg})

    return {
        "valid": False,
        "messages": translated_messages
    }
