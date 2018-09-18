import asyncio
import fnmatch
import os

from aiohttp import web
import aiohttp
import pint
from prometheus_client.core import GaugeMetricFamily, CollectorRegistry
from prometheus_client.exposition import generate_latest


ELASTICSEARCH_HOST = os.environ.get('ELASTICSEARCH_HOST', 'http://elasticsearch:9200/')
ELASTICSEARCH_USERNAME = os.environ.get('ELASTICSEARCH_USERNAME', '')
ELASTICSEARCH_PASSWORD = os.environ.get('ELASTICSEARCH_PASSWORD', '')
OTHER_PATTERNS = os.environ.get('OTHER_PATTERNS', '').split(',')


auth = None
if ELASTICSEARCH_USERNAME and ELASTICSEARCH_PASSWORD:
    auth = aiohttp.BasicAuth(
        login=ELASTICSEARCH_USERNAME,
        password=ELASTICSEARCH_PASSWORD,
    )


ureg = pint.UnitRegistry('/app/share/units.txt')


def find_pattern(patterns, index):
    for pattern in patterns:
        if fnmatch.fnmatch(index, pattern):
            return pattern

    for pattern in OTHER_PATTERNS:
        if fnmatch.fnmatch(index, pattern):
            return pattern

    return 'unknown'



class ElasticsearchCollector(object):

    def __init__(self, patterns, shards):
        self.patterns = patterns
        self.shards = shards

    def collect(self):
        labels = ['pattern', 'index', 'shard', 'node', 'type', 'state']

        doc_count = GaugeMetricFamily(
            'escluster_shards_documents',
            'Number of documents in shard',
            labels=labels,
        )

        bytes = GaugeMetricFamily(
            'escluster_shards_bytes',
            'Bytes stored in shard',
            labels=labels,
        )

        for shard in self.shards:
           label = (find_pattern(self.patterns, shard['index']), shard['index'], shard['shard'], shard['node'], shard['type'], shard['state'])
           doc_count.add_metric(label, shard['count'])
           bytes.add_metric(label, shard['bytes'])

        return [doc_count, bytes]


async def get_patterns(session):
    patterns = []

    result = await session.get(ELASTICSEARCH_HOST + '.kibana/_search', json={
        'size': 100,
        'query': {
            'type': {
                'value': 'index-pattern',
            }
        }
    })

    # if result.status == 404:
    #    return []

    payload = await result.json()
    for hit in payload['hits']['hits']:
        patterns.append(hit['_source']['title'])

    return patterns


async def get_shards(session):
    shards = []

    result = await session.get(ELASTICSEARCH_HOST + '_cat/shards?format=json')
    payload = await result.json()
    for shard in payload:
        shards.append({
            "index": shard['index'],
            "shard": shard['shard'],
            "bytes": int(ureg(shard['store']).to('byte').m),
            "count": int(shard['docs']),
            "node": shard['node'],
            "state": shard['state'],
            "type": "primary" if shard['prirep'] == 'p' else 'replica',
        })

    return sorted(shards, key=lambda x: '{}:{}'.format(x['index'], x['shard']))


async def get_metrics(request):
    async with aiohttp.ClientSession(auth=auth) as session:
        patterns_fut = asyncio.ensure_future(get_patterns(session))
        shards_fut = asyncio.ensure_future(get_shards(session))
        patterns = await patterns_fut
        shards = await shards_fut

    registry = CollectorRegistry()
    registry.register(ElasticsearchCollector(patterns, shards))
    metrics = generate_latest(registry)

    return web.Response(body=metrics, content_type='text/plain', charset='utf-8')


app = web.Application()
app.add_routes([web.get('/metrics', get_metrics)])
web.run_app(app)
