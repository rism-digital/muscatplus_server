class IncipitModeValues:
    INTERVALS = "intervals"
    EXACT_PITCHES = "exact-pitches"
    CONTOUR = "contour"


MODE_FIELDS: dict = {
    IncipitModeValues.INTERVALS: (
        "intervals_im",
        "interval_ids_json",
        "intervalsChromatic",
    ),
    IncipitModeValues.EXACT_PITCHES: (
        "pitches_sm",
        "pitches_ids_json",
        "pitchesChromatic",
    ),
    IncipitModeValues.CONTOUR: (
        "contour_refined_sm",
        "interval_ids_json",
        "intervalRefinedContour",
    ),
}
