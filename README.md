# cta861modes
Simple parser to obtain CTA-861 video modes from linux kernel drivers and
generate a VHDL package based on this information for an FPGA/VHDL class at HM.

Contains two quick and dirty scripts:
1. `get_timings.py` retrieves drm_edid.c from the linux kernel sources which contains the parameters of
all the video modes from up to CTA-861-I. Ir parses the file and creates a json file containing the paramters
2. `create_vhdl_pkg.py`: creates a vhdl package with an array of records containing the timing parameter

# Motivation
HDMI video timings are based on the CTA-861 standard. Newest version (2025) is CTA-861-I.

Unfortunately it seems that CTA is not providing any machine readable sources of the parameters and parsing
the pdf is error prone and cumbersome.
Luckily all the timing paramters are also contained in a c file in the linux kernel sources. Namely `drivers/gpu/drm/drm_edid.c`.

# Notes
- This script uses very primitive parsing and will only work as long as the format of setting the timing parameters in `drm_edid.c` is not changed.
- It would be much better to use an actual c parser like pycparser.
- The json file created on 2025-04-18 containing all the modes contained in CTA-861-I is also checked in.
- Not all columns from the timing tables in CTA-861 are contained.
  - Hblank and Vblank can be easily computed as the sum of the respective front, sync and back values.
  - The vfreq (refresh rate) can be computed as $vfreq=\frac{pxl_clk_khz \cdot 1000}{hotal \cdot vtotal}$. Note that for some modes this might be slightly
    different then the refresh rate contained in the name (e.g. 59.4 Hz instead of 60 Hz). This is normal and accepted and is a result of the 1000/1001 factor
    which can be added to some modes to avoid matching powerline frequency. Such modes are considered "the same" (they use the same vic for both frequencies)
