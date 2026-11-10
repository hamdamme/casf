"""Immutable event snapshots and exact request fields."""

import pytest

EVENT_ID = "123e4567-e89b-42d3-a456-426600000001"


def event(**changes):
    return {"event_id": EVENT_ID, "actor": "alice", "event_type": "created",
            "payload": {"items": [{"value": "original"}]},
            "attributes": {"labels": ["original"]}, **changes}


def test_event_request_owns_inputs_and_all_returned_objects():
    from dataclasses import FrozenInstanceError

    from casf.model.api import EventRequest

    values = event()
    request = EventRequest.from_dict(values)
    values["payload"]["items"][0]["value"] = "caller change"
    values["attributes"]["labels"].append("caller change")
    returned = request.to_dict()
    returned["payload"]["items"].clear()
    request.payload["items"].clear()
    request.attributes["labels"].append("accessor change")
    assert request.to_dict() == event()
    assert request.event_id == EVENT_ID
    assert request.actor == "alice"
    assert request.event_type == "created"
    with pytest.raises(FrozenInstanceError):
        request._encoded = b"{}"
    assert "original" not in repr(request)


@pytest.mark.parametrize("change", ["missing", "extra", "not_object"])
def test_event_mapping_requires_the_exact_field_set(change):
    from casf.errors import SchemaError
    from casf.model.api import EventRequest

    values = event()
    if change == "missing":
        values.pop("attributes")
    elif change == "extra":
        values["extra"] = "private-value"
    else:
        values = []
    with pytest.raises(SchemaError) as error:
        EventRequest.from_dict(values)
    assert "private-value" not in str(error.value)
