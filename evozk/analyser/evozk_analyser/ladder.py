"""A0-pad capacity ladder (Algorithm 1 input L):
L = (16, 31, 64, 128, 256, 512, 1024, 2048, 4096), finite.

Beyond the last rung (Algorithm 1 l.17: "or sigma' if no rung covers it") K is sigma and the step is flagged
`beyond_ladder`. It is never reached at B = 1 on the RQ2 histories (largest sigma 421); it is reached by FHIR at the
B = 4 sensitivity (sigma 4412-5255)."""
from .errors import StateError

POLICIES = ("tight-refit", "structural-step")
LADDER = (16, 31, 64, 128, 256, 512, 1024, 2048, 4096)


def _check(s):
    if not isinstance(s, int) or isinstance(s, bool) or s < 0:
        raise StateError(f"sigma must be a non-negative integer, got {s!r}")


def ladder_ceil(s):
    """min{l in L : l >= s}, or None when s exceeds the last rung (beyond the ladder)."""
    _check(s)
    for r in LADDER:
        if r >= s:
            return r
    return None


def ladder_min(s):
    """Initial capacity: the smallest rung covering s; beyond the ladder, K := s (as Algorithm 1 l.17)."""
    c = ladder_ceil(s)
    return s if c is None else c


def beyond_ladder(s):
    return ladder_ceil(s) is None


def next_K(policy, K, sigma_new):
    """K after a transition to sigma_new; Algorithm 1 l.16-17: unchanged unless sigma' > K, then K <- sigma' under
    tight-refit, else min{l in L : l >= sigma'}, or sigma' if no rung covers it."""
    if policy not in POLICIES:
        raise StateError(f"unknown A0-pad policy {policy!r}")
    _check(sigma_new)
    if sigma_new <= K:
        return K
    return sigma_new if policy == "tight-refit" else ladder_min(sigma_new)
