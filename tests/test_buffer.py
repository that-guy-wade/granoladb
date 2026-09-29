from granoladb.buffer import Buffer


def test_flushes_when_size_reached():
    batches = []
    buf = Buffer(batches.append, flush_size=2, flush_interval=None)
    buf.add({"n": 1})
    assert batches == []            # not yet
    buf.add({"n": 2})
    assert batches == [[{"n": 1}, {"n": 2}]]


def test_manual_flush_emits_partial_batch():
    batches = []
    buf = Buffer(batches.append, flush_size=100, flush_interval=None)
    buf.add({"n": 1})
    buf.flush()
    assert batches == [[{"n": 1}]]


def test_flush_on_empty_is_noop():
    batches = []
    buf = Buffer(batches.append, flush_size=100, flush_interval=None)
    buf.flush()
    assert batches == []
