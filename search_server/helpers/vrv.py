import os
import re
import tempfile
import urllib.parse
from difflib import Match

import cdifflib  # type: ignore
import httpx
import orjson
import verovio
from sanic.log import logger

from search_server.helpers.identifiers import get_identifier, strip_prefix
from search_server.helpers.incipit_search_fields import MODE_FIELDS
from search_server.helpers.resvg import render_svg
from search_server.helpers.solr_connection import SolrResult

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

type RenderedIncipit = tuple[str | None, str | None]

CSS_REPLACEMENT_PATTERN: re.Pattern = re.compile(
    r'<style type="text/css">(?P<existing_style>.*)</style>'
)


def render_pae(
    pae: str,
    use_crc: bool = False,
    enlarged: bool = False,
    is_mensural: bool = False,
    hard_truncate: bool = False,
) -> RenderedIncipit:
    """
    Renders Plaine and Easie to SVG and MIDI. Returns None if there was a problem loading the data.

    If use_crc is True, then the IDs will be generated using a CRC32 checksum of the input data. If not,
    then the IDs will be randomly generated.

    :param pae: A plaine and easie-formatted input string
    :param use_crc: Use the CRC of the input for Verovio's ID generator
    :param enlarged: Render the output slightly larger
    :param is_mensural: Set a different spacing for mensural notation
    :param hard_truncate: Truncates the incipit. If it's too long for the set "page", the incipit will
        render the rest on the second page, but since we never render the second page, it effectively
        truncates the incipit.
    :return: A named tuple containing SVG and MIDI.
    """
    custom_options: dict = {"xmlIdChecksum": use_crc}

    if not use_crc:
        vrv_tk.resetXmlIdSeed(0)

    if hard_truncate:
        custom_options["adjustPageWidth"] = False
        custom_options["pageHeight"] = 100

    if enlarged:
        custom_options["pageWidth"] = 1400
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
        return None, None

    svg: str = vrv_tk.renderToSVG()
    if not svg:
        return None, None

    # NB: MIDI is disabled until a Verovio bug is fixed.
    # mid: str = vrv_tk.renderToMIDI()
    # The toolkit has `paeFeatures=True` so this will output the PAE features
    # b64midi = f"data:audio/midi;base64,{mid}"

    # Use an empty string to keep the signature the same.
    b64midi = ""

    return svg, b64midi


async def render_url(url: str) -> str | None:
    """
    Takes a URL to an MEI file and returns the SVG for it.

    :param url:
    :return:
    """
    async with httpx.AsyncClient() as client:
        try:
            res = await client.get(url)
        except httpx.RequestError:
            logger.error("Request error for %s", url)
            return None

        if res.status_code != 200:
            logger.error(
                "Server responded with non-success status code: %s", res.status_code
            )
            return None

        mei: str = res.text
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
            logger.error("Verovio could not load file %s", url)
            return None

        svg: str = vrv_tk.renderToSVG()

        return svg


def render_mei(req, incipit: dict) -> str | None:
    """
    Renders an MEI result from PAE input. Includes information for the MEI header
    in the `x-header` section.

    :param req: the incoming Sanic request
    :param incipit: A Solr result of an incipit record
    :return: The MEI encoded as a string, or None if there was a problem loading
    """
    vrv_opts: dict = VEROVIO_BASE_OPTIONS.copy()
    vrv_tk.setOptions(vrv_opts)
    vrv_tk.setInputFrom("pae")
    incipit_parent_type: str = incipit["parent_type_s"]

    work_num: str = incipit["work_num_s"]

    incipit_url: str
    record_url: str
    if incipit_parent_type == "source":
        source_id: str = strip_prefix(incipit["source_id"])
        record_url = get_identifier(req, "sources.source", source_id=source_id)
        incipit_url = get_identifier(
            req, "sources.incipit_mei_encoding", source_id=source_id, work_num=work_num
        )
    elif incipit_parent_type == "work":
        work_id: str = strip_prefix(incipit["work_id"])
        record_url = get_identifier(req, "works.work", work_id=work_id)
        incipit_url = get_identifier(
            req, "works.incipit_mei_encoding", work_id=work_id, work_num=work_num
        )
    else:
        logger.error(
            "Unknown parent type %s for incipit %s", incipit_parent_type, incipit["id"]
        )
        return None

    metadata_header: dict = {"record_url": record_url, "download_url": incipit_url}

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
        logger.error("Verovio could transform incipit %s to MEI", incipit_id)
        return None

    mei: str = vrv_tk.getMEI()
    return mei


def render_png(req, incipit: str) -> bytes | None:
    rendered: RenderedIncipit = render_pae(incipit)
    rendered_svg, _ = rendered
    if not rendered_svg:
        return None

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
        logger.error("There was a problem rendering an SVG!")
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


def get_pae_features(req) -> dict | None:
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
    if not load_success:
        logger.warning("Could not load PAE for %s", pae)
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


# Handles both highlighted and non-highlighted incipits for search results. Will
# not highight if there is no query_pae_features provided.
def render_incipit(
    obj: SolrResult,
    query_pae_features: dict | None = None,
    search_mode: str | None = None,
) -> RenderedIncipit:
    pae_code: str | None = obj.get("original_pae_sni")
    if not pae_code:
        logger.debug("no PAE code")
        return None, None

    is_mensural: bool = obj.get("is_mensural_b", False)

    if query_pae_features is None:
        # If we don't do the highlighting phase, exit now. We don't need to use
        # the CRC for the incipit.
        logger.info("No query features provided, skipping highlighting")
        return render_pae(pae_code, is_mensural=is_mensural)

    svg, b64midi = render_pae(pae_code, use_crc=True, is_mensural=is_mensural)
    if not svg:
        logger.error("Could not load music incipit for %s", obj.get("id"))
        return None, None

    if search_mode is None or search_mode not in MODE_FIELDS:
        logger.info("No search mode, skipping highlighting")
        return svg, b64midi

    # We need to know the search mode so that we know what set of values in the
    # Solr document and in the Query to compare for the longest subsequence.
    feature_field, ids_field, query_features_field = MODE_FIELDS[search_mode]

    if feature_field not in obj:
        logger.info("no feature field, skipping highlighting")
        return svg, b64midi

    document_interval_features: list[str] = list(map(str, obj[feature_field]))
    document_interval_ids: list[list[str]] = obj[ids_field]
    query_interval_feature: list[str] = query_pae_features[query_features_field]

    logger.debug("Document features: %s", document_interval_features)
    logger.debug("Query features: %s", query_interval_feature)

    # The type checker will emit an error here because the default types for
    # a and b are strings, not lists. However, the documentation only says that
    # these need to be iterables, and their contents hashable, so lists should
    # be fine. So we ignore any type checker errors here.
    smtch = cdifflib.CSequenceMatcher(
        a=query_interval_feature,  # type: ignore
        b=document_interval_features,  # type: ignore
    )

    # Matches the longest subsequence in the two lists, starting at the beginning.
    matched_blk: Match = smtch.find_longest_match(
        0, len(query_interval_feature), 0, len(document_interval_features)
    )

    highlight_ids = {
        nid
        for noteids in document_interval_ids[
            matched_blk.b : matched_blk.b + matched_blk.size
        ]
        for nid in noteids
    }

    if not highlight_ids:
        return svg, b64midi

    highlight_css_stmt = " ".join(
        f'g[data-id="{nid}"] {{ fill: red; color: red; }}' for nid in highlight_ids
    )

    highlighted_svg = re.sub(
        CSS_REPLACEMENT_PATTERN,
        rf'<style type="text/css">\1 {highlight_css_stmt}</style>',
        svg,
    )

    return highlighted_svg, b64midi
