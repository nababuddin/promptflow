import json
from typing import Callable

from opentelemetry.trace import Span

from ._trace import TraceType, _traced, global_span_enricher

keys = ["id", "score", "content", "metadata"]


def enrich_retrieval_span(span: Span, inputs, output: list):
    if "query" in inputs:
        query = inputs["query"]
        span.set_attribute("retrieval.query", query)
        #  span.add_event("promptflow.retrieval.query", {"payload": query})
    if not isinstance(output, list):
        return
    docs = []

    # It's tricky here when switching index from one to another
    for doc in output:
        if not isinstance(doc, dict):
            continue
        item = {}
        for key in keys:
            if key in doc:
                item["document." + key] = doc[key]
        if item:
            docs.append(item)
    if docs:
        #  span.set_attribute("retrieval.documents", json.dumps(docs))
        span.add_event("promptflow.retrieval.documents", {"payload": json.dumps(docs)})


global_span_enricher.register(TraceType.RETRIEVAL, enrich_retrieval_span)


def retrieval(
    func: Callable,
) -> Callable:
    return _traced(func, trace_type=TraceType.RETRIEVAL)
