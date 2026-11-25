"""HTTP Accept-header parsing and representation selection."""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from types import MappingProxyType

_TOKEN = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")
_QVALUE = re.compile(r"^(?:0(?:\.\d{0,3})?|1(?:\.0{0,3})?)$")

type _Candidate = tuple[str, str, Mapping[str, str]]


@dataclass(frozen=True)
class _MediaRange:
    type: str
    subtype: str
    parameters: tuple[tuple[str, str], ...]
    quality: Decimal

    @property
    def specificity(self) -> tuple[int, int, int]:
        """Rank exact media ranges above wildcards, then prefer more parameters.

        Tuples compare lexicographically: a concrete type beats ``*``, a
        concrete subtype beats ``*``, and additional media parameters add
        specificity (for example, ``application/json`` beats ``*/*``).
        """
        return (
            int(self.type != "*"),
            int(self.subtype != "*"),
            len(self.parameters),
        )


def _split_quoted(value: str, separator: str) -> list[str]:
    """Split on a delimiter, leaving delimiters inside quoted strings intact."""
    if '"' not in value:
        return [part.strip() for part in value.split(separator)]

    parts: list[str] = []
    start = 0
    quoted = False
    escaped = False

    for index, char in enumerate(value):
        if escaped:
            escaped = False
        elif char == "\\" and quoted:
            escaped = True
        elif char == '"':
            quoted = not quoted
        elif char == separator and not quoted:
            parts.append(value[start:index].strip())
            start = index + 1

    parts.append(value[start:].strip())
    return parts


def _parse_parameter(value: str) -> tuple[str, str] | None:
    name, separator, parameter_value = value.partition("=")
    name = name.strip().lower()
    parameter_value = parameter_value.strip()
    if not separator or not _TOKEN.fullmatch(name) or not parameter_value:
        return None

    if parameter_value.startswith('"') and parameter_value.endswith('"'):
        parameter_value = parameter_value[1:-1]
        parameter_value = re.sub(r"\\(.)", r"\1", parameter_value)
    elif '"' in parameter_value or not _TOKEN.fullmatch(parameter_value):
        return None

    return name, parameter_value


def _parse_media_type(value: str) -> tuple[str, str, dict[str, str]] | None:
    parts = _split_quoted(value, ";")
    media_type = parts[0].lower()
    type_parts = media_type.split("/")
    if len(type_parts) != 2:
        return None

    type_name, subtype = (part.strip() for part in type_parts)
    if type_name == "*" and subtype != "*":
        return None
    if type_name != "*" and not _TOKEN.fullmatch(type_name):
        return None
    if subtype != "*" and not _TOKEN.fullmatch(subtype):
        return None

    parameters: dict[str, str] = {}
    for part in parts[1:]:
        if not part:
            continue
        parsed = _parse_parameter(part)
        if parsed is None:
            return None
        name, parameter_value = parsed
        if name in parameters:
            return None
        parameters[name] = parameter_value

    return type_name, subtype, parameters


def _parse_accept(accept: str) -> list[_MediaRange]:
    ranges: list[_MediaRange] = []

    for member in _split_quoted(accept, ","):
        if not member:
            continue

        parts = _split_quoted(member, ";")
        parsed_media_type = _parse_media_type(parts[0])
        if parsed_media_type is None:
            continue
        type_name, subtype, _ = parsed_media_type

        parameters: list[tuple[str, str]] = []
        quality = Decimal(1)
        found_quality = False
        valid = True

        for part in parts[1:]:
            if not part:
                valid = False
                break
            if found_quality and "=" not in part:
                if not _TOKEN.fullmatch(part.strip()):
                    valid = False
                    break
                # accept-ext permits a bare token after q.
                continue
            parsed_parameter = _parse_parameter(part)
            if parsed_parameter is None:
                valid = False
                break
            name, value = parsed_parameter

            if name == "q":
                if found_quality or not _QVALUE.fullmatch(value):
                    valid = False
                    break
                try:
                    quality = Decimal(value)
                except InvalidOperation:
                    valid = False
                    break
                found_quality = True
            elif not found_quality:
                parameters.append((name, value))
            # Parameters after q are accept extensions, not media-type constraints.

        if valid:
            ranges.append(
                _MediaRange(
                    type_name,
                    subtype,
                    tuple(parameters),
                    quality,
                )
            )

    return ranges


@lru_cache(maxsize=32)
def _candidate_parameters(media_type: str) -> _Candidate | None:
    """Compile a server-offered media type, never a client header value."""
    parsed = _parse_media_type(media_type)
    if parsed is None:
        return None

    type_name, subtype, parameters = parsed
    base_type = f"{type_name}/{subtype}"
    # These are the parameters present on the representations produced by the
    # application, even though they are not part of the negotiation constants.
    if base_type in {
        "text/html",
        "application/json",
        "application/ld+json",
    } and "profile" not in parameters:
        parameters.setdefault("charset", "utf-8")
    return type_name, subtype, MappingProxyType(parameters)


def _matches(media_range: _MediaRange, candidate: _Candidate) -> bool:
    type_name, subtype, parameters = candidate
    if media_range.type not in ("*", type_name):
        return False
    if media_range.subtype not in ("*", subtype):
        return False

    for name, value in media_range.parameters:
        candidate_value = parameters.get(name)
        if candidate_value is None:
            return False
        if name == "charset":
            if candidate_value.lower() != value.lower():
                return False
        elif candidate_value != value:
            return False

    return True


def negotiate_media_type(
    accept: str | None, supported_media_types: Sequence[str]
) -> str | None:
    """Choose the best supported representation for an Accept header.

    Quality values are honored. For each representation, the most-specific
    matching media range determines its quality. When qualities tie, a more
    specific match wins; any remaining tie is resolved by the order of
    ``supported_media_types``.

    An absent or empty Accept header is treated as no preference, so the
    endpoint's first supported representation is selected.
    """
    if not supported_media_types:
        return None
    if accept is None or not accept.strip():
        return supported_media_types[0]

    ranges = _parse_accept(accept)
    if not ranges:
        return None

    best_media_type: str | None = None
    best_score: tuple[Decimal, tuple[int, int, int], int] | None = None

    for index, media_type in enumerate(supported_media_types):
        candidate = _candidate_parameters(media_type)
        if candidate is None:
            continue

        matching_ranges = [item for item in ranges if _matches(item, candidate)]
        if not matching_ranges:
            continue

        # Specificity takes precedence over q when multiple ranges match one
        # representation (e.g. application/json;q=0, */*;q=1).
        effective_range = max(
            matching_ranges, key=lambda item: (item.specificity, item.quality)
        )
        if effective_range.quality == 0:
            continue

        score = (
            effective_range.quality,
            effective_range.specificity,
            -index,
        )
        if best_score is None or score > best_score:
            best_media_type = media_type
            best_score = score

    return best_media_type
