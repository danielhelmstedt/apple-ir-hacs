"""Constants for the Apple IR Receiver integration."""

DOMAIN = "apple_ir"
DEFAULT_DEVICE_NAME = "Apple IR Receiver"
DEFAULT_ENTITY_ID = "infrared.apple_ir_receiver"

APPLE_VENDOR_ID = 0x05AC
# Apple IR receiver product IDs (see hid-ids.h: USB_DEVICE_ID_APPLE_IRCONTROL*)
APPLE_IR_PRODUCT_IDS = frozenset({0x8240, 0x8241, 0x8242, 0x8243, 0x8245})
