from __future__ import absolute_import
from future import standard_library
standard_library.install_aliases()  # noqa

import urllib.parse as parse


def sanitize_url(url, mask_url_query=True, mask_url_path=False):
    parsed = parse.urlsplit(url)

    # masking - may be give some hints in masking query and path instead of '?' ??
    host = '{}:{}'.format(parsed.hostname, parsed.port) if parsed.port else parsed.hostname
    query = str(parse.urlencode({k: '?' for k in parse.parse_qs(parsed.query).keys()})) if \
        mask_url_query else parsed.query
    path = '/??/' if parsed.path and mask_url_path else parsed.path

    components = parse.SplitResult(parsed.scheme, host, path, query, parsed.fragment)

    return parse.urlunsplit(components)
