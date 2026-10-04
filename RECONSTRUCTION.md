# Sovol Zero, reconstructed

This fork adds what `Sovol3d/SOVOL-ZERO` doesn't carry: Sovol's own Klipper history for the Zero, the contents of every Zero OTA package I could find, and submodules that resolve. Sovol's `main` is left as published.

## Branches and tags

| Ref | What it is |
|---|---|
| `main` | `Sovol3d/SOVOL-ZERO` as published |
| `reconstruction` | `main` plus `.gitmodules` and this file |
| `klipper/vendor` | Sovol's internal Klipper repository for the Zero: 56 commits from `a6dc07c` "first commit for sv08mini" to `8a8b5e8` "1.4.5", with the original hashes, authors, dates and messages |
| `klipper/shipped` | `cc8afd8` (1.3.7), then the Klipper tree each OTA update left on the printer |
| `ota/packages` | every Zero OTA package found, unpacked, one commit per package, oldest first |
| `vendor/<version>` | the vendor commit whose `menu.cfg` carries that version |
| `shipped/<version>` | the Klipper tree after that update |

## Where the vendor history comes from

| Source | Commits | Head |
|---|--:|---|
| A retail Zero, factory 1.3.7, never updated | 43 | `1c0a784` 2025-01-11 |
| Sovol's 1.3.7 recovery image | 49 | `cc8afd8` 2025-01-20 "1.3.7版本" |
| Sovol's SV08 Max OTA package `KLP_SOC_MKS_SKIPR-08max_20251018.deb`, whose `.git` carries the Zero's main branch as `origin/main` | 56 | `8a8b5e8` 2025-05-08 "1.4.5" |

They are one repository; the shorter histories are prefixes of the longer. `pulponair/sovol-zero-klipper-enhanced` carries the first 43. The SV08 Max's own branch is not included.

Every commit on `klipper/vendor` is Sovol's original object, so it can be checked against any Zero:

```
cd ~/klipper
git log -1 --format=%H
git cat-file -e 8a8b5e8 && echo present
```

## Versions

Each commit's `klippy/extras/display/menu.cfg` names its version and build date, which is a better label than the commit message.

| Version | Vendor commit | OTA package | Shipped Klipper tree |
|---|---|---|---|
| 1.3.7 | `cc8afd8` | 2025-01-20, and the recovery image | `cc8afd8` |
| 1.3.8 | none. `b920e83` is titled 1.3.8, but its `menu.cfg` still says 1.3.7 and the package doesn't match it | 2025-03-29, built 2025-03-18 | 1.3.7 code, new version string |
| 1.3.9 | `503f61d`, `a471c3a` | none found | — |
| 1.4.0 | `36d4468` | none found | — |
| 1.4.1 | — | 2025-04-07 | 1.4.0 code, new version string |
| 1.4.2 | — | 2025-04-22 | 1.4.0 code, new version string |
| 1.4.3 | `056345d`, `901ee7a` | none found | — |
| 1.4.4 | none | none found | — |
| 1.4.5 | `8a8b5e8` | none found | — |
| 1.4.6 | — | 2025-05-10 | 1.4.5 code, new version string |
| 1.4.7 | — | 2025-05-20 | 1.4.5 code, new version string |

"New version string" means that over `klippy/` and `src/`, only `menu.cfg` differs from the vendor commit. So the Klipper code that reached printers by OTA changed twice after launch, at 1.4.1 and at 1.4.6.

`ota/packages` also holds the pre-release packages: 1.2.5 (an empty test package, 2024-12-13), then 1.3.0, 1.3.1, 1.3.2 and 1.3.4 to 1.3.7 from 2024-12-26 to 2025-01-20 (no 1.3.3 package was found), and a 2025-03-18 build that became 1.3.8. A package's `Version` field and its on-screen version disagree twice: 1.3.8 says 1.3.7, and 1.4.1 says 1.4.0.

## About the reconstructed commits

`klipper/shipped` and `ota/packages` are my commits, not Sovol's. Each is dated to the newest file in its package, so `git log` follows Sovol's timeline, and each message carries the package's SHA-256.

On `klipper/shipped` each package's Klipper files are overlaid on the previous tree, with compiled Python caches left out. A package can only add or replace files, so nothing is deleted on that line.

`ota/packages` is each package as unpacked: installed files at their install paths, control files and maintainer scripts under `DEBIAN/`. Empty directories are dropped, since git can't hold them. `home/sovol/printer_data/database/` is withheld from every package that has one.

## What's in the packages

Besides Klipper: Mainsail, Sovol's printer configs (`printer_data/config`, `patch/`), the OTA and service scripts, the toolhead firmware and its CAN flasher (`printer_data/build`), and from 1.4.6 the Realtek 8189FS Wi-Fi driver (`8189fs.ko`, `v5.15.6-11-g51d21ab4e.20230207`, built for kernel `5.16.17-sun50iw9`), a Wi-Fi setup server (`usr/local/bin/wifi_server.py`) and the Flask wheels it installs offline (`offline_lib/flask`, Flask 3.1.0 for Python 3.9 on aarch64).

The firmware images are Sovol's builds. Their build IDs (`cc8afd8-dirty`, `14d7b18-dirty`) name commits on `klipper/vendor`, but "dirty" means the tree had uncommitted changes, so the exact source isn't available. The Wi-Fi driver is a binary of Realtek's out-of-tree driver; its source isn't in the packages.

## Submodules

`.gitmodules` makes every submodule in Sovol's tree resolve. `sovol/klipper` points at `b920e83` on `klipper/vendor` in this repository; the rest are the upstream commits Sovol pinned.

| Path | Commit | Upstream |
|---|---|---|
| `sovol/klipper` | `b920e83` | this repository |
| `sovol/KlipperScreen` | `7127b5d` | KlipperScreen/KlipperScreen |
| `sovol/crowsnest` | `d75a3ae` | mainsail-crew/crowsnest |
| `sovol/kiauh` | `a63cf8c` | dw-0/kiauh |
| `sovol/mainsail-config` | `e57810d` | mainsail-crew/mainsail-config |
| `sovol/moonraker` | `4e00a07` | Arksine/moonraker |
| `sovol/moonraker-obico` | `4c0b7b6` | TheSpaghettiDetective/moonraker-obico |
| `sovol/moonraker-timelapse` | `c7fff11` | mainsail-crew/moonraker-timelapse |

```
git clone --recursive -b reconstruction https://github.com/rpcyan586/SOVOL-ZERO
```

## Licensing

Klipper, its firmware, Mainsail and Moonraker are GPL-3.0; see `COPYING` on the Klipper branches. Sovol's own configs and scripts carry no licence statement. They are here as shipped, for reference, and this repository grants no licence over them.
