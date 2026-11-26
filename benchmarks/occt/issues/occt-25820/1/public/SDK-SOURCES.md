# Offline WOK toolchain for Linux x86-64

The four original Debian archives include their copyright and license files under `usr/share/doc/<package>/copyright`. They are extracted into the build directory. No installation or administrative privileges are required. The WOK generator is used only at build time.

| Archive | SHA-256 | Source |
| --- | --- | --- |
| libopencascade-foundation-6.3.0_6.3.0.dfsg.1-6_amd64.deb | 31399ec96f8aee28d256b1d5c8a06ada9bedb130b0648d0b0697c7f0c3684dbb | [Debian](https://archive.debian.org/debian/pool/main/o/opencascade/libopencascade-foundation-6.3.0_6.3.0.dfsg.1-6_amd64.deb) |
| opencascade-wok_6.3.0.dfsg.1-6_amd64.deb | ef3c7de217b5e43b375b46e92b145511c187ade03fb18bcbb3c46a6d103c64b6 | [Debian](https://archive.debian.org/debian/pool/main/o/opencascade/opencascade-wok_6.3.0.dfsg.1-6_amd64.deb) |
| tcl8.5_8.5.8-2_amd64.deb | 0747615df00116206aac1f14c9eee04228c7b9246bdb3b83ccf2a5b7907ecddb | [Debian](https://archive.debian.org/debian/pool/main/t/tcl8.5/tcl8.5_8.5.8-2_amd64.deb) |
| tk8.5_8.5.8-1_amd64.deb | 87236cb6eb9b3d554c65f0a875c5c1eae520b52e10c23d772965a4c5c5ce5e79 | [Debian](https://archive.debian.org/debian/pool/main/t/tk8.5/tk8.5_8.5.8-1_amd64.deb) |

The generator bridge uses the WOK headers in the corresponding Debian source release, SHA-256 `7dc22fe21bdf377623ff05379b122021e787106356518315d3bb5569522d2443`. The SDK includes just the headers selected by the compiler dependency scan. [Debian source](https://archive.debian.org/debian/pool/main/o/opencascade/opencascade_6.3.0.dfsg.1.orig.tar.gz)

The supplied CPPExt EDL templates are from upstream WOK commit `958949b10481094ee482d1d883a8cf14ab819cf3`. Individual files retain upstream notices. [WOK templates](https://github.com/Open-Cascade-SAS/OCCT-wok/tree/958949b10481094ee482d1d883a8cf14ab819cf3/src/CPPExt)

The host provides GCC, Python 3, Ninja, GNU binutils, dpkg-deb, xz and Tcl development headers. The source-tree Standard copy stage selects its own persistent prototype. The two generated numeric comparator override signatures are taken from their generated base classes. All modeling translation units and runtime symbols are built from the supplied OCCT source and its CDL declarations.
For the 6.9-era input, the build-only imported-transient.py adapter maps three later imported transient declarations for the 6.3 CDL parser. It restores the original OCCT Handle type of the three generated cache fields. The committed handwritten classes and kernel algorithms are compiled from the supplied source tree.
