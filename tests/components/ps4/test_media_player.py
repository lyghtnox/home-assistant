"""Tests for the PS4 media player platform."""
from unittest.mock import MagicMock, patch

from pyps4_homeassistant.credential import get_ddp_message

from homeassistant.components import ps4
from homeassistant.components.media_player.const import (
    ATTR_INPUT_SOURCE,
    ATTR_INPUT_SOURCE_LIST,
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    ATTR_MEDIA_TITLE,
    MEDIA_TYPE_GAME,
)
from homeassistant.components.ps4.const import (
    ATTR_MEDIA_IMAGE_URL,
    CONFIG_ENTRY_VERSION as VERSION,
    DEFAULT_REGION,
    DOMAIN,
    GAMES_FILE,
    PS4_DATA,
)
from homeassistant.const import (
    ATTR_COMMAND,
    ATTR_ENTITY_ID,
    ATTR_LOCKED,
    CONF_HOST,
    CONF_NAME,
    CONF_REGION,
    CONF_TOKEN,
    STATE_IDLE,
    STATE_OFF,
    STATE_PLAYING,
    STATE_UNKNOWN,
)
from homeassistant.setup import async_setup_component
from tests.common import MockConfigEntry, mock_device_registry, mock_registry, mock_coro


MOCK_CREDS = "123412341234abcd12341234abcd12341234abcd12341234abcd12341234abcd"
MOCK_NAME = "ha_ps4_name"
MOCK_REGION = DEFAULT_REGION
MOCK_GAMES_FILE = GAMES_FILE
MOCK_HOST = "192.168.0.2"
MOCK_HOST_NAME = "Fake PS4"
MOCK_HOST_ID = "A0000A0AA000"
MOCK_HOST_VERSION = "09879011"
MOCK_HOST_TYPE = "PS4"
MOCK_STATUS_STANDBY = "Server Standby"
MOCK_STATUS_ON = "Ok"
MOCK_STANDBY_CODE = 620
MOCK_ON_CODE = 200
MOCK_TCP_PORT = 997
MOCK_DDP_PORT = 987
MOCK_DDP_VERSION = "00020020"
MOCK_RANDOM_PORT = "1234"

MOCK_TITLE_ID = "CUSA00000"
MOCK_TITLE_NAME = "Random Game"
MOCK_TITLE_TYPE = MEDIA_TYPE_GAME
MOCK_TITLE_ART_URL = "https://somecoverurl"

MOCK_GAMES_DATA = {
    ATTR_LOCKED: False,
    ATTR_MEDIA_CONTENT_TYPE: MEDIA_TYPE_GAME,
    ATTR_MEDIA_IMAGE_URL: MOCK_TITLE_ART_URL,
    ATTR_MEDIA_TITLE: MOCK_TITLE_NAME,
}

MOCK_GAMES_DATA_LOCKED = {
    ATTR_LOCKED: True,
    ATTR_MEDIA_CONTENT_TYPE: MEDIA_TYPE_GAME,
    ATTR_MEDIA_IMAGE_URL: MOCK_TITLE_ART_URL,
    ATTR_MEDIA_TITLE: MOCK_TITLE_NAME,
}

MOCK_STATUS_PLAYING = {
    "host-type": MOCK_HOST_TYPE,
    "host-ip": MOCK_HOST,
    "host-request-port": MOCK_TCP_PORT,
    "host-id": MOCK_HOST_ID,
    "host-name": MOCK_HOST_NAME,
    "running-app-titleid": MOCK_TITLE_ID,
    "running-app-name": MOCK_TITLE_NAME,
    "status": MOCK_STATUS_ON,
    "status_code": MOCK_ON_CODE,
    "device-discovery-protocol-version": MOCK_DDP_VERSION,
    "system-version": MOCK_HOST_VERSION,
}

MOCK_STATUS_IDLE = {
    "host-type": MOCK_HOST_TYPE,
    "host-ip": MOCK_HOST,
    "host-request-port": MOCK_TCP_PORT,
    "host-id": MOCK_HOST_ID,
    "host-name": MOCK_HOST_NAME,
    "status": MOCK_STATUS_ON,
    "status_code": MOCK_ON_CODE,
    "device-discovery-protocol-version": MOCK_DDP_VERSION,
    "system-version": MOCK_HOST_VERSION,
}

MOCK_STATUS_OFF = {
    "host-type": MOCK_HOST_TYPE,
    "host-ip": MOCK_HOST,
    "host-request-port": MOCK_TCP_PORT,
    "host-id": MOCK_HOST_ID,
    "host-name": MOCK_HOST_NAME,
    "status": MOCK_STATUS_STANDBY,
    "status_code": MOCK_STANDBY_CODE,
    "device-discovery-protocol-version": MOCK_DDP_VERSION,
    "system-version": MOCK_HOST_VERSION,
}

MOCK_DEVICE = {CONF_HOST: MOCK_HOST, CONF_NAME: MOCK_NAME, CONF_REGION: MOCK_REGION}

MOCK_ENTRY_ID = "SomeID"

MOCK_DEVICE_MODEL = "PlayStation 4"

MOCK_DATA = {CONF_TOKEN: MOCK_CREDS, "devices": [MOCK_DEVICE]}

MOCK_CONFIG = MockConfigEntry(domain=DOMAIN, data=MOCK_DATA, entry_id=MOCK_ENTRY_ID)

MOCK_LOAD = "homeassistant.components.ps4.media_player.load_games"
MOCK_SAVE = "homeassistant.components.ps4.save_json"


async def setup_mock_component(hass, entry=None):
    """Set up Mock Media Player."""
    if entry is None:
        mock_entry = MockConfigEntry(
            domain=ps4.DOMAIN, data=MOCK_DATA, version=VERSION, entry_id=MOCK_ENTRY_ID
        )
    else:
        mock_entry = entry

    mock_entry.add_to_hass(hass)

    # Don't use an actual file.
    with patch(MOCK_LOAD, return_value={}), patch(MOCK_SAVE, side_effect=MagicMock()):
        await async_setup_component(hass, DOMAIN, {DOMAIN: {}})

    await hass.async_block_till_done()

    mock_entities = hass.states.async_entity_ids()

    mock_entity_id = mock_entities[0]

    return mock_entity_id


async def mock_ddp_response(hass, mock_status_data, games=None):
    """Mock raw UDP response from device."""
    mock_protocol = hass.data[PS4_DATA].protocol

    mock_code = mock_status_data.get("status_code")
    mock_status = mock_status_data.get("status")
    mock_status_header = "{} {}".format(mock_code, mock_status)
    mock_response = get_ddp_message(mock_status_header, mock_status_data).encode()

    if games is None:
        games = {}

    with patch(MOCK_LOAD, return_value=games), patch(
        MOCK_SAVE, side_effect=MagicMock()
    ):
        mock_protocol.datagram_received(mock_response, (MOCK_HOST, MOCK_RANDOM_PORT))
        await hass.async_block_till_done()


async def test_async_setup_platform_does_nothing():
    """Test setup platform does nothing (Uses config entries only)."""
    await ps4.media_player.async_setup_platform(None, None, None)


async def test_media_player_is_setup_correctly_with_entry(hass):
    """Test entity is setup correctly with entry correctly."""
    mock_entity_id = await setup_mock_component(hass)
    mock_state = hass.states.get(mock_entity_id).state

    # Assert status updated callback is added to protocol.
    assert len(hass.data[PS4_DATA].protocol.callbacks) == 1

    # Test that entity is added to hass.
    assert hass.data[PS4_DATA].protocol is not None
    assert mock_entity_id == "media_player.{}".format(MOCK_NAME)
    assert mock_state == STATE_UNKNOWN


async def test_state_off_is_set(hass):
    """Test that state is set to off."""
    mock_entity_id = await setup_mock_component(hass)

    with patch(MOCK_SAVE, side_effect=MagicMock()):
        await mock_ddp_response(hass, MOCK_STATUS_OFF)

    assert hass.states.get(mock_entity_id).state == STATE_OFF


async def test_state_playing_is_set(hass):
    """Test that state is set to playing."""
    mock_entity_id = await setup_mock_component(hass)
    mock_func = "{}{}".format(
        "homeassistant.components.ps4.media_player.",
        "pyps4.Ps4Async.async_get_ps_store_data",
    )

    with patch(mock_func, return_value=mock_coro(None)), patch(
        MOCK_SAVE, side_effect=MagicMock()
    ):
        await mock_ddp_response(hass, MOCK_STATUS_PLAYING)

    assert hass.states.get(mock_entity_id).state == STATE_PLAYING


async def test_state_idle_is_set(hass):
    """Test that state is set to idle."""
    mock_entity_id = await setup_mock_component(hass)

    with patch(MOCK_SAVE, side_effect=MagicMock()):
        await mock_ddp_response(hass, MOCK_STATUS_IDLE)

    assert hass.states.get(mock_entity_id).state == STATE_IDLE


async def test_state_none_is_set(hass):
    """Test that state is set to None."""
    mock_entity_id = await setup_mock_component(hass)

    assert hass.states.get(mock_entity_id).state == STATE_UNKNOWN


async def test_media_attributes_are_fetched(hass):
    """Test that media attributes are fetched."""
    mock_entity_id = await setup_mock_component(hass)
    mock_func = "{}{}".format(
        "homeassistant.components.ps4.media_player.",
        "pyps4.Ps4Async.async_get_ps_store_data",
    )

    # Mock result from fetching data.
    mock_result = MagicMock()
    mock_result.name = MOCK_TITLE_NAME
    mock_result.cover_art = MOCK_TITLE_ART_URL
    mock_result.game_type = "game"

    with patch(mock_func, return_value=mock_coro(mock_result)) as mock_fetch, patch(
        MOCK_SAVE, side_effect=MagicMock()
    ):
        await mock_ddp_response(hass, MOCK_STATUS_PLAYING)

    mock_state = hass.states.get(mock_entity_id)
    mock_attrs = dict(mock_state.attributes)

    assert len(mock_fetch.mock_calls) == 1

    assert mock_state.state == STATE_PLAYING
    assert len(mock_attrs.get(ATTR_INPUT_SOURCE_LIST)) == 1
    assert mock_attrs.get(ATTR_INPUT_SOURCE_LIST)[0] == MOCK_TITLE_NAME
    assert mock_attrs.get(ATTR_MEDIA_CONTENT_ID) == MOCK_TITLE_ID
    assert mock_attrs.get(ATTR_MEDIA_TITLE) == MOCK_TITLE_NAME
    assert mock_attrs.get(ATTR_MEDIA_CONTENT_TYPE) == MOCK_TITLE_TYPE


async def test_media_attributes_are_loaded(hass):
    """Test that media attributes are loaded."""
    mock_entity_id = await setup_mock_component(hass)
    mock_data = {MOCK_TITLE_ID: MOCK_GAMES_DATA_LOCKED}
    mock_func = "{}{}".format(
        "homeassistant.components.ps4.media_player.",
        "pyps4.Ps4Async.async_get_ps_store_data",
    )

    with patch(mock_func, return_value=mock_coro(None)) as mock_fetch, patch(
        MOCK_SAVE, side_effect=MagicMock()
    ):
        await mock_ddp_response(hass, MOCK_STATUS_PLAYING, mock_data)

    mock_state = hass.states.get(mock_entity_id)
    mock_attrs = dict(mock_state.attributes)

    # Ensure that data is not fetched.
    assert not mock_fetch.mock_calls

    assert mock_state.state == STATE_PLAYING

    assert len(mock_attrs.get(ATTR_INPUT_SOURCE_LIST)) == 1
    assert mock_attrs.get(ATTR_INPUT_SOURCE_LIST)[0] == MOCK_TITLE_NAME
    assert mock_attrs.get(ATTR_MEDIA_CONTENT_ID) == MOCK_TITLE_ID
    assert mock_attrs.get(ATTR_MEDIA_TITLE) == MOCK_TITLE_NAME
    assert mock_attrs.get(ATTR_MEDIA_CONTENT_TYPE) == MOCK_TITLE_TYPE


async def test_device_info_is_set_from_status_correctly(hass):
    """Test that device info is set correctly from status update."""
    mock_d_registry = mock_device_registry(hass)
    with patch(
        "pyps4_homeassistant.ps4.get_status", return_value=MOCK_STATUS_OFF
    ), patch(MOCK_SAVE, side_effect=MagicMock()):
        mock_entity_id = await setup_mock_component(hass)

    await hass.async_block_till_done()

    # Reformat mock status-sw_version for assertion.
    mock_version = MOCK_STATUS_OFF["system-version"]
    mock_version = mock_version[1:4]
    mock_version = "{}.{}".format(mock_version[0], mock_version[1:])

    mock_state = hass.states.get(mock_entity_id).state

    mock_d_entries = mock_d_registry.devices
    mock_entry = mock_d_registry.async_get_device(
        identifiers={(DOMAIN, MOCK_HOST_ID)}, connections={()}
    )
    assert mock_state == STATE_OFF

    assert len(mock_d_entries) == 1
    assert mock_entry.name == MOCK_HOST_NAME
    assert mock_entry.model == MOCK_DEVICE_MODEL
    assert mock_entry.sw_version == mock_version
    assert mock_entry.identifiers == {(DOMAIN, MOCK_HOST_ID)}


async def test_device_info_is_assummed(hass):
    """Test that device info is assumed if device is unavailable."""
    # Create a device registry entry with device info.
    mock_d_registry = mock_device_registry(hass)
    mock_d_registry.async_get_or_create(
        config_entry_id=MOCK_ENTRY_ID,
        name=MOCK_HOST_NAME,
        model=MOCK_DEVICE_MODEL,
        identifiers={(DOMAIN, MOCK_HOST_ID)},
        sw_version=MOCK_HOST_VERSION,
    )
    mock_d_entries = mock_d_registry.devices
    assert len(mock_d_entries) == 1

    # Create a entity_registry entry which is using identifiers from device.
    mock_unique_id = ps4.format_unique_id(MOCK_CREDS, MOCK_HOST_ID)
    mock_e_registry = mock_registry(hass)
    mock_e_registry.async_get_or_create(
        "media_player", DOMAIN, mock_unique_id, config_entry=MOCK_CONFIG
    )
    mock_entity_id = mock_e_registry.async_get_entity_id(
        "media_player", DOMAIN, mock_unique_id
    )

    mock_entity_id = await setup_mock_component(hass)
    mock_state = hass.states.get(mock_entity_id).state

    # Ensure that state is not set.
    assert mock_state == STATE_UNKNOWN

    # Ensure that entity_id is the same as the existing.
    mock_entities = hass.states.async_entity_ids()
    assert len(mock_entities) == 1
    assert mock_entities[0] == mock_entity_id


async def test_device_info_assummed_works(hass):
    """Reverse test that device info assumption works."""
    mock_d_registry = mock_device_registry(hass)
    mock_entity_id = await setup_mock_component(hass)
    mock_state = hass.states.get(mock_entity_id).state
    mock_d_entries = mock_d_registry.devices

    # Ensure that state is not set.
    assert mock_state == STATE_UNKNOWN

    # With no state/status and no existing entries, registry should be empty.
    assert not mock_d_entries


async def test_turn_on(hass):
    """Test that turn on service calls function."""
    mock_entity_id = await setup_mock_component(hass)
    mock_func = "{}{}".format(
        "homeassistant.components.ps4.media_player.", "pyps4.Ps4Async.wakeup"
    )

    with patch(mock_func, return_value=MagicMock()) as mock_call, patch(
        MOCK_SAVE, side_effect=MagicMock()
    ):
        await hass.services.async_call(
            "media_player", "turn_on", {ATTR_ENTITY_ID: mock_entity_id}
        )
        await hass.async_block_till_done()

    assert len(mock_call.mock_calls) == 1


async def test_turn_off(hass):
    """Test that turn off service calls function."""
    mock_entity_id = await setup_mock_component(hass)
    mock_func = "{}{}".format(
        "homeassistant.components.ps4.media_player.", "pyps4.Ps4Async.standby"
    )

    with patch(mock_func, return_value=MagicMock()) as mock_call, patch(
        MOCK_SAVE, side_effect=MagicMock()
    ):
        await hass.services.async_call(
            "media_player", "turn_off", {ATTR_ENTITY_ID: mock_entity_id}
        )
        await hass.async_block_till_done()

    assert len(mock_call.mock_calls) == 1


async def test_media_pause(hass):
    """Test that media pause service calls function."""
    mock_entity_id = await setup_mock_component(hass)
    mock_func = "{}{}".format(
        "homeassistant.components.ps4.media_player.", "pyps4.Ps4Async.remote_control"
    )

    with patch(mock_func, return_value=MagicMock()) as mock_call, patch(
        MOCK_SAVE, side_effect=MagicMock()
    ):
        await hass.services.async_call(
            "media_player", "media_pause", {ATTR_ENTITY_ID: mock_entity_id}
        )
        await hass.async_block_till_done()

    assert len(mock_call.mock_calls) == 1


async def test_media_stop(hass):
    """Test that media stop service calls function."""
    mock_entity_id = await setup_mock_component(hass)
    mock_func = "{}{}".format(
        "homeassistant.components.ps4.media_player.", "pyps4.Ps4Async.remote_control"
    )

    with patch(mock_func, return_value=MagicMock()) as mock_call, patch(
        MOCK_SAVE, side_effect=MagicMock()
    ):
        await hass.services.async_call(
            "media_player", "media_stop", {ATTR_ENTITY_ID: mock_entity_id}
        )
        await hass.async_block_till_done()

    assert len(mock_call.mock_calls) == 1


async def test_select_source(hass):
    """Test that select source service calls function with title."""
    mock_data = {MOCK_TITLE_ID: MOCK_GAMES_DATA}
    with patch(
        "pyps4_homeassistant.ps4.get_status", return_value=MOCK_STATUS_IDLE
    ), patch(MOCK_LOAD, return_value=mock_data):
        mock_entity_id = await setup_mock_component(hass)

    mock_func = "{}{}".format(
        "homeassistant.components.ps4.media_player.", "pyps4.Ps4Async.start_title"
    )

    with patch(mock_func, return_value=MagicMock()) as mock_call, patch(
        MOCK_SAVE, side_effect=MagicMock()
    ):
        # Test with title name.
        await hass.services.async_call(
            "media_player",
            "select_source",
            {ATTR_ENTITY_ID: mock_entity_id, ATTR_INPUT_SOURCE: MOCK_TITLE_NAME},
        )
        await hass.async_block_till_done()

    assert len(mock_call.mock_calls) == 1


async def test_select_source_caps(hass):
    """Test that select source service calls function with upper case title."""
    mock_data = {MOCK_TITLE_ID: MOCK_GAMES_DATA}
    with patch(
        "pyps4_homeassistant.ps4.get_status", return_value=MOCK_STATUS_IDLE
    ), patch(MOCK_LOAD, return_value=mock_data):
        mock_entity_id = await setup_mock_component(hass)

    mock_func = "{}{}".format(
        "homeassistant.components.ps4.media_player.", "pyps4.Ps4Async.start_title"
    )

    with patch(mock_func, return_value=MagicMock()) as mock_call, patch(
        MOCK_SAVE, side_effect=MagicMock()
    ):
        # Test with title name in caps.
        await hass.services.async_call(
            "media_player",
            "select_source",
            {
                ATTR_ENTITY_ID: mock_entity_id,
                ATTR_INPUT_SOURCE: MOCK_TITLE_NAME.upper(),
            },
        )
        await hass.async_block_till_done()

    assert len(mock_call.mock_calls) == 1


async def test_select_source_id(hass):
    """Test that select source service calls function with Title ID."""
    mock_data = {MOCK_TITLE_ID: MOCK_GAMES_DATA}
    with patch(
        "pyps4_homeassistant.ps4.get_status", return_value=MOCK_STATUS_IDLE
    ), patch(MOCK_LOAD, return_value=mock_data):
        mock_entity_id = await setup_mock_component(hass)

    mock_func = "{}{}".format(
        "homeassistant.components.ps4.media_player.", "pyps4.Ps4Async.start_title"
    )

    with patch(mock_func, return_value=MagicMock()) as mock_call, patch(
        MOCK_SAVE, side_effect=MagicMock()
    ):
        # Test with title ID.
        await hass.services.async_call(
            "media_player",
            "select_source",
            {ATTR_ENTITY_ID: mock_entity_id, ATTR_INPUT_SOURCE: MOCK_TITLE_ID},
        )
        await hass.async_block_till_done()

    assert len(mock_call.mock_calls) == 1


async def test_ps4_send_command(hass):
    """Test that ps4 send command service calls function."""
    mock_entity_id = await setup_mock_component(hass)
    mock_func = "{}{}".format(
        "homeassistant.components.ps4.media_player.", "pyps4.Ps4Async.remote_control"
    )

    with patch(mock_func, return_value=MagicMock()) as mock_call, patch(
        MOCK_SAVE, side_effect=MagicMock()
    ):
        await hass.services.async_call(
            DOMAIN, "send_command", {ATTR_ENTITY_ID: mock_entity_id, ATTR_COMMAND: "ps"}
        )
        await hass.async_block_till_done()

    assert len(mock_call.mock_calls) == 1


async def test_entry_is_unloaded(hass):
    """Test that entry is unloaded."""
    mock_entry = MockConfigEntry(
        domain=ps4.DOMAIN, data=MOCK_DATA, version=VERSION, entry_id=MOCK_ENTRY_ID
    )
    mock_entity_id = await setup_mock_component(hass, mock_entry)
    mock_unload = await ps4.async_unload_entry(hass, mock_entry)

    assert mock_unload is True
    assert not hass.data[PS4_DATA].devices

    # Test that callback listener for entity is removed from protocol.
    assert not hass.data[PS4_DATA].protocol.callbacks

    assert hass.states.get(mock_entity_id) is None
