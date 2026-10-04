# Zero mainboard firmware, read from two printers

No OTA package carries mainboard firmware, so the build every Zero runs exists only on the boards. This is that flash, read from two Zeros on 2026-10-04 over CAN with Klipper's `scripts/dump_mcu.py`, which uses `debug_read` and writes nothing. One unit is factory 1.3.7 and never updated, the other is on 1.4.7. The two reads are byte-identical.

| File | Start | Size | SHA-256 |
|---|---|---|---|
| `sector0-0x08000000.bin` | `0x08000000` | 128 KiB, the bootloader sector | `eae145d64507ffc4c56515bb4a627651377e08a1c7c3c533559c9cb9414e848e` |
| `app-0x08020000.bin` | `0x08020000` | first 64 KiB of the application sector | `74a39acf1876fdd5c2f6db2dfe2362a274ab3b906908382f6949ae7e4222e721` |

- Bootloader: CanBoot `32c53b2-dirty`, 8,612 bytes. The rest of the sector reads erased.
- Application: Klipper `14d7b18-dirty-20250210_015142-SPI-XI` for the STM32H750, 36,904 bytes. The rest of the read is erased.

Against `zero_motherboard_1.3.7.hex`, the recovery file that circulates, the identify dictionary is identical apart from the version string, but the application is a different build (`14d7b18-dirty-20250102_012550`, 36,712 bytes) and so is the bootloader (CanBoot `743f4cf-dirty`, 6,420 bytes).

`14d7b18` is on `klipper/vendor`. The build is "dirty", so its exact source isn't available.
