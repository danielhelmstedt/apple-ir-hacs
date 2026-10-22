# Apple IR Receiver for Home Assistant

Exposes the built-in IR receiver of older Apple Macs as a Home Assistant **Infrared receiver** entity, so other integrations can subscribe to IR Remote button presses.


## Requirements
- Home Assistant 2026.4 or later, which includes the `infrared` component with receiver
  support.
- The receiver visible to Home Assistant as a hidraw device (e.g. USB passthrough to a VM) and readable by the HA process.

## Installation (HACS) - Recommended

1. Have [HACS](https://hacs.xyz/) installed.
2. Add `https://github.com/danielhelmstedt/apple-ir-hacs` as a
   [custom repository](https://hacs.xyz/docs/faq/custom_repositories/) with
   **Type: Integration**.
3. In HACS, find **Apple IR Receiver** and click **Download**, then restart Home
   Assistant for the installation to take effect.
4. Go to **Settings → Devices & services → Add integration**, search for
   **Apple IR Receiver**, and complete setup.

## Installation (Manual)

1. Download this repository as a ZIP and unzip the archive.
2. Copy `custom_components/apple_ir` into
   `/config/custom_components/apple_ir`.
   - Create the `custom_components` folder if it does not exist.
3. Restart Home Assistant.
4. Go to **Settings → Devices & services → Add integration**, search for
   **Apple IR Receiver**, and complete setup.

## Supported remotes
This integration uses the Mac's built-in IR receiver, which exclusively decodes 32-bit NEC protocol signals operating on a 38 kHz carrier frequency. 

- **Apple Remotes:** Supports the white plastic and the silver aluminium remotes used up to the 3rd-generation Apple TV.
- **Third-Party & Generic NEC Remotes:** Many brands implement the NEC protocol including Yamaha, Pioneer, Onkyo, Hisense, TCL, and others.

Remotes which use proprietary protocols (e.g. Sony, LG, Samsung, Panasonic) are not recognised by the Apple IR receiver, so cannot be used with this integration. 

**Note: This integration has been tested to work with Apple, Yamaha and Chiq remotes. Other NEC remotes should work, but this is not guaranteed.**

## Decoding
- The Apple IR receiver firmware decodes NEC-style signals and exposes them as raw HID reports. The integration reads these from `/dev/hidraw*`, so no kernel driver (`CONFIG_HID_APPLEIR`) is needed.

- A HID report has the form `25 87 ee <remote id> <key>`. Interpreting the report with `infrared_protocols.commands.nec.NECCommand.from_raw_timings(timings, decode_subfunction=True)` yields `address=0xEE87`, `command=<remote id>`, and `subfunction=<key byte>`.
- A `26 …` HID report represents a repeat; the integration emits it as an NEC repeat frame, not as another full data frame.
- Some button presses arrive as two reports (with `0x5x` key bytes), so subscribers receive two frames.
- The raw HID reports are converted back into 38 kHz NEC-style timings, and delivered to subscribers as an `InfraredReceivedSignal` via `async_subscribe_receiver`.