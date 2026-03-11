from prisoners_gambit.core.events import Event, EventBus


def test_named_subscriber_receives_only_matching_events() -> None:
    bus = EventBus()
    received = []

    bus.subscribe("alpha", lambda event: received.append(event.name))

    bus.publish(Event("alpha", {"x": 1}))
    bus.publish(Event("beta", {"x": 2}))

    assert received == ["alpha"]


def test_wildcard_subscriber_receives_all_events_in_order() -> None:
    bus = EventBus()
    received = []

    bus.subscribe("*", lambda event: received.append(event.name))

    bus.publish(Event("alpha"))
    bus.publish(Event("beta"))
    bus.publish(Event("gamma"))

    assert received == ["alpha", "beta", "gamma"]


def test_multiple_named_subscribers_each_receive_event() -> None:
    bus = EventBus()
    received_a = []
    received_b = []

    bus.subscribe("alpha", lambda event: received_a.append(event.payload))
    bus.subscribe("alpha", lambda event: received_b.append(event.payload))

    payload = {"value": 3}
    bus.publish(Event("alpha", payload))

    assert received_a == [payload]
    assert received_b == [payload]


def test_event_payload_is_passed_through_unchanged() -> None:
    bus = EventBus()
    received = []

    payload = {"floor": 4, "player": "You**"}
    bus.subscribe("player_successor_selected", lambda event: received.append(event.payload))

    bus.publish(Event("player_successor_selected", payload))

    assert received == [payload]


def test_named_and_wildcard_subscribers_can_coexist() -> None:
    bus = EventBus()
    named = []
    wildcard = []

    bus.subscribe("alpha", lambda event: named.append(event.name))
    bus.subscribe("*", lambda event: wildcard.append(event.name))

    bus.publish(Event("alpha"))
    bus.publish(Event("beta"))

    assert named == ["alpha"]
    assert wildcard == ["alpha", "beta"]