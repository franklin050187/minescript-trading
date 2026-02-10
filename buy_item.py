from system.lib import minescript as m
from minescript_plus import Inventory
import time
import lib_nbt
from minescript_plus import Screen


def buy_item(slot: int):
    """
    Clicks the buy button for an item in the AH and confirms the result.
    Returns True if the buy was successful, False otherwise.
    Closes the AH screen after confirming the result.
    """
    if not isinstance(slot, int):
        m.echo("Slot must be an integer.")
        return False
    elif slot < 0 or slot > 44:
        m.echo("Slot must be from 0 to 44.")
        return False
    Inventory.click_slot(slot)
    result = wait_for_confirm_result()
    if not result:
        m.echo("Failed to confirm buy result.")
        Screen.close_screen()
        return False

    m.echo("Buy result confirmed.")
    Inventory.click_slot(15)  # accept
    Screen.close_screen()
    return True


def wait_for_confirm_result(
    slot=15,
    success_id="minecraft:lime_stained_glass_pane",
    fail_id="minecraft:red_stained_glass_pane",
    max_retries=3,
    delay=0.2,
):
    for attempt in range(1, max_retries + 1):
        items = m.container_get_items()

        item = next((i for i in items if i.slot == slot), None)
        if not item or not item.nbt:
            m.echo(f"⚠ Slot {slot} empty or no NBT (attempt {attempt})")
            time.sleep(delay)
            continue

        try:
            nbt = lib_nbt.parse_snbt(item.nbt)
            item_id = nbt.get("id")
        except Exception:
            m.echo(f"⚠ NBT parse failed (attempt {attempt})")
            time.sleep(delay)
            continue

        if item_id == success_id:
            m.echo("✓ Found success item, UI is updated")
            return True

        if item_id == fail_id:
            m.echo("✗ Found fail item, UI is updated")
            return True

        # UI not updated yet
        m.echo(f"⏳ Waiting for UI update... ({attempt}/{max_retries})")
        time.sleep(delay)

    m.echo("❌ Timeout waiting for confirm result")
    return False
