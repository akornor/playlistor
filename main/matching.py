from strsimpy.jaro_winkler import JaroWinkler


def pairwise_max(a, b, f):
    """Find maximum similarity score between elements of two lists"""
    mx = 0
    for i in a:
        for j in b:
            mx = max(mx, f(i, j))
    return mx


def normalized_string_similarity(s1, s2):
    """Returns a similarity score between 0 and 1. Penalizes differences in keywords like 'instrumental'"""
    special_terms = [
        "instrumental",
        "remix",
        "cover",
        "live",
        "version",
        "edit",
        "nightcore",
    ]
    for term in special_terms:
        in_s1 = term in s1.lower()
        in_s2 = term in s2.lower()
        if in_s1 ^ in_s2:
            return 0
    return JaroWinkler().similarity(s1.lower(), s2.lower())


def aliased_string_similarity(s1, s2):
    return pairwise_max(s1, s2, normalized_string_similarity)


def track_similarity(track1, track2):

    def artists_similarity(artists1, artists2):
        if len(artists1) == 0 or len(artists2) == 0:
            return 0.5
        return pairwise_max(artists1, artists2, aliased_string_similarity)

    def album_similarity(album1, album2):
        return pairwise_max(album1, album2, aliased_string_similarity)

    def length_similarity(length_sec_1, length_sec_2):
        d = abs(length_sec_1 - length_sec_2)
        max_dist = 5
        if d > max_dist:
            return 0
        return 1 - d / max_dist

    # Feature weights
    weights = {
        "name": 50,
        "album": 20,
        "artists": 30,
        "length": 20,
    }

    feature_scores = {}

    # Compute feature scores only if both tracks have the feature
    if track1.name and track2.name:
        feature_scores["name"] = aliased_string_similarity(track1.name, track2.name)

    if track1.artists and track2.artists:
        feature_scores["artists"] = artists_similarity(track1.artists, track2.artists)

    if track1.albums and track2.albums:
        feature_scores["album"] = album_similarity(track1.albums, track2.albums)

    if track1.length and track2.length:
        feature_scores["length"] = length_similarity(track1.length, track2.length)

    used_features = feature_scores.keys()
    if not used_features:
        return 0.0

    # Calculate weighted average
    weighted_sum = sum(
        feature_scores[feature] * weights[feature] for feature in used_features
    )
    total_weight = sum(weights[feature] for feature in used_features)
    similarity = weighted_sum / total_weight

    assert 0 <= similarity <= 1
    return similarity


def are_tracks_same(track1, track2, threshold=0.7):
    return track_similarity(track1, track2) >= threshold
