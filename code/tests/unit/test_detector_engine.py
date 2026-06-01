from deepturn_agents.detection.detector_engine import DetectorEngine


def test_detector_deduplicates_burst_events() -> None:
    detector = DetectorEngine(dedup_window_seconds=60)
    e1 = {
        "namespace": "default",
        "workload_ref": "deploy/api",
        "symptom_type": "runtime",
        "severity": "high",
        "observed_at": "2026-05-16T10:00:00Z",
    }
    e2 = {
        "namespace": "default",
        "workload_ref": "deploy/api",
        "symptom_type": "runtime",
        "severity": "high",
        "observed_at": "2026-05-16T10:00:20Z",
    }
    assert detector.from_watch_event(e1) is not None
    assert detector.from_watch_event(e2) is None


def test_detector_skips_malformed_timestamps_without_crashing() -> None:
    detector = DetectorEngine(dedup_window_seconds=60)
    malformed = {
        "namespace": "default",
        "workload_ref": "deploy/api",
        "symptom_type": "runtime",
        "severity": "high",
        "observed_at": "not-a-time",
    }
    assert detector.from_watch_event(malformed) is None


def test_detector_evicts_old_seen_entries() -> None:
    detector = DetectorEngine(dedup_window_seconds=1)
    old = {
        "namespace": "a",
        "workload_ref": "deploy/a",
        "symptom_type": "runtime",
        "severity": "high",
        "observed_at": "2026-05-16T10:00:00Z",
    }
    new = {
        "namespace": "b",
        "workload_ref": "deploy/b",
        "symptom_type": "runtime",
        "severity": "high",
        "observed_at": "2026-05-16T10:10:00Z",
    }
    detector.from_watch_event(old)
    detector.from_watch_event(new)
    assert len(detector._seen) <= 1
