"""Validate PBIR JSON against Microsoft's schemas (not a Desktop/DAX test).

Schema downloads require explicit --download-schemas. Cached checks are offline.
Install jsonschema in a development environment to use this optional checker.
"""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urldefrag
from urllib.request import urlopen

from jsonschema import Draft7Validator
from referencing import Registry, Resource

PREFIX = 'https://developer.microsoft.com/json-schemas/fabric/'


def validate(project, cache, *, download=False):
    cache = Path(cache)
    cache.mkdir(parents=True, exist_ok=True)
    documents = {}

    def retrieve(uri):
        uri = urldefrag(uri)[0]
        if not uri.startswith(PREFIX):
            raise ValueError(f'Untrusted schema URL: {uri}')
        if uri not in documents:
            local = cache / (hashlib.sha256(uri.encode()).hexdigest() + '.json')
            if not local.exists():
                if not download:
                    raise ValueError(f'Missing cached schema: {uri}; use --download-schemas explicitly')
                with urlopen(uri, timeout=30) as response:
                    local.write_bytes(response.read())
            documents[uri] = json.loads(local.read_text(encoding='utf-8-sig'))
        return Resource.from_contents(documents[uri])

    registry = Registry(retrieve=retrieve)
    count = 0
    for path in sorted(Path(project).rglob('*')):
        if not path.is_file() or path.suffix not in ('.json', '.pbip', '.pbir', '.pbism'):
            continue
        data = json.loads(path.read_text(encoding='utf-8'))
        if '$schema' not in data:
            continue
        resource = retrieve(data['$schema'])
        current = registry.with_resource(data['$schema'], resource)
        errors = list(Draft7Validator(resource.contents, registry=current).iter_errors(data))
        if errors:
            raise ValueError(f'{path}: {errors[0].message}')
        count += 1
    if not count:
        raise ValueError('No project JSON definitions found')
    return {'schema_validated_files': count, 'desktop_validated': False, 'dax_executed': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project')
    parser.add_argument('--cache', default='outputs/powerbi-schema-cache')
    parser.add_argument('--download-schemas', action='store_true')
    args = parser.parse_args()
    print(json.dumps(validate(args.project, args.cache, download=args.download_schemas), indent=2))
