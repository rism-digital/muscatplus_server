from collections import namedtuple
from typing import Optional
import logging
import verovio
import ujson

log = logging.getLogger(__name__)
verovio.enableLog(False)


log.info("Instantiating Verovio")
vrv_tk = verovio.toolkit()

vrv_tk.setInputFrom(verovio.PAE)
vrv_tk.setOptions(ujson.dumps({
    "footer": 'none',
    "header": 'none',
    "breaks": 'auto',
    "pageMarginTop": 0,
    "pageMarginBottom": 25,  # Artificially inflate the bottom margin until rism-digital/verovio#1960 is fixed.
    "pageMarginLeft": 0,
    "pageMarginRight": 0,
    # "adjustPageWidth": "true",
    "pageWidth": 2200,
    "spacingStaff": 1,
    "scale": 40,
    "adjustPageHeight": "true",
    "svgHtml5": "true",
    "svgFormatRaw": "true",
    "svgRemoveXlink": "true",
    "svgViewBox": "true",
    "paeFeatures": True,
    "xmlIdSeed": 1
}))


def render_pae(pae: str, use_crc: bool = False) -> Optional[tuple]:
    """
    Renders Plaine and Easie to SVG and MIDI. Returns None if there was a problem loading the data.

    If use_crc is True, then the IDs will be generated using a CRC32 checksum of the input data. If not,
    then the IDs will be randomly generated.

    :param pae: A plaine and easie-formatted input string
    :param use_crc: The ID seed to use for Verovio's ID generator
    :return: A named tuple containing SVG and MIDI.
    """
    if use_crc:
        vrv_tk.setOptions(ujson.dumps({
            "xmlIdChecksum": True
        }))
    else:
        vrv_tk.resetXmlIdSeed(0)

    load_status: bool = vrv_tk.loadData(pae)

    # If loading failed, return None
    if not load_status:
        return None

    svg: str = vrv_tk.renderToSVG()
    mid: str = vrv_tk.renderToMIDI()
    # The toolkit has `paeFeatures=True` so this will output the PAE features
    b64midi = f"data:audio/midi;base64,{mid}"

    return svg, b64midi


def create_pae_from_request(req, notedata: str) -> str:
    """
    Takes an incoming incipit request and extracts the parameters (if present)
    for adjusting the PAE output.

    :param req: A request object
    :param notedata: The PAE note data.

    :return: A string containing PAE for handing off to Verovio to render.
    """
    clef: str = req.args.get("ic", "G-2")
    timesig: str = req.args.get("it", "4/4")
    keysig: str = req.args.get("ik", "")
    music_data = notedata if notedata.endswith("/") else f"{notedata}/"

    pae_elements: list = [
        f"@clef:{clef}",
        f"@key:",
        f"@keysig:{keysig}",
        f"@timesig:{timesig}",
        f"@data:{music_data}"
    ]

    return "\n".join(pae_elements)


def get_pae_features(req, notes: str) -> dict:
    """
        Parses an incoming search request containing some note data and some
        optional parameters, and returns a dictionary containing the PAE features.

        Note that if Verovio cannot parse the notation it will still return a dictionary
        with the expected keys, but the list of features will be empty.
    """
    vrv_tk.resetXmlIdSeed(0)
    pae: str = create_pae_from_request(req, notes)
    vrv_tk.loadData(pae)
    features: str = vrv_tk.getDescriptiveFeatures("{}")

    feat_output: dict = ujson.loads(features)

    return feat_output
