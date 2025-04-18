# -----------------------------------------------------------------------------
# Script Name: create_vhdl_pkg.py
# Description: This script reads a JSON file containing CTA-861 video timings and
#              creates a VHDL package with the video mode records.
# Author: Felix Miller
# Date: 2025-04-18
# -----------------------------------------------------------------------------
# Usage:
#   0. Optional: User script get_timings.py to retrieve and parse timings from
#      linux kernel sources and create video_timings.json
#   1. Place the JSON file (video_timings.json) in the same directory as this script.
#   2. Run the script using Python 3.
#   3. The script will generate a VHDL package file named video_timings_pkg.vhdl.
# -----------------------------------------------------------------------------
# Example JSON file format (video_timings.json):
# [
#    {
#        "vic": 16,
#        "name": "1920x1080@60Hz",
#        "pxl_clk_khz": 148500,
#        "hactive": 1920,
#        "vactive": 1080,
#        "interlaced": false,
#        "double_clocked": false,
#        "htotal": 2200,
#        "hblank": 280,
#        "hfront": 88,
#        "hsync": 44,
#        "hback": 148,
#        "hpol": 1,
#        "vtotal": 1125,
#        "vblank": 45,
#        "vfront": 4,
#        "vsync": 5,
#        "vback": 36,
#        "vpol": 1,
#        "ln": 1
#    },
#     ...
# ]
# -----------------------------------------------------------------------------

import json

# Read the JSON file
with open('video_timings.json', 'r') as json_file:
    video_timings = json.load(json_file)

# Create the VHDL package
vhdl_package = """
library IEEE;
use IEEE.STD_LOGIC_1164.ALL;

package video_timings_pkg is

    type video_timing_r is record
        name        : string(1 to 20);
        vic         : natural range 0 to 255;
        pxl_clk_khz : natural range 0 to 2**13-1;
        interlaced  : boolean;
        dbl_clkd    : boolean;
        hactive     : natural range 0 to 2**13-1;
        vactive     : natural range 0 to 2**13-1;
        hfront      : natural range 0 to 2**13-1;
        hsync       : natural range 0 to 2**13-1;
        hback       : natural range 0 to 2**13-1;
        hpol        : std_logic;
        vfront      : natural range 0 to 2**13-1;
        vsync       : natural range 0 to 2**13-1;
        vback       : natural range 0 to 2**13-1;
        vpol        : std_logic;
        ln          : integer range 0 to 7;
    end record;

    type video_timings_a is array (0 to {max_index}) of video_timing_r;

    constant video_timings : video_timings_a := (
    --  VIC    |  Name              | VIC | Pixel Clk kHz | interlaced | double clocked | hactive | vactive | hfront | hsync | hback | hpol | vfront | vsync | vback | vpol | ln
""".format(max_index=max([mode['vic'] for mode in video_timings]))

# Add the records to the array
for mode in video_timings:
    vhdl_package += """
        {vic:>3} => ("{name:<20}", {vic:>4}, {pxl_clk_khz:>14}, {interlaced:>11}, {dbl_clkd:>15}, {hactive:>8}, {vactive:>8}, {hfront:>7}, {hsync:>6}, {hback:>6},   '{hpol}', {vfront:>7}, {vsync:>6}, {vback:>6},   '{vpol}',  {ln} ),""".format(
        vic=mode['vic'],
        name=mode['name'],
        pxl_clk_khz=mode['pxl_clk_khz'],
        interlaced=str(mode['interlaced']).lower(),
        dbl_clkd=str(mode['double_clocked']).lower(),
        hactive=mode['hactive'],
        vactive=mode['vactive'],
        hfront=mode['hfront'],
        hsync=mode['hsync'],
        hback=mode['hback'],
        hpol=mode['hpol'],
        vfront=mode['vfront'],
        vsync=mode['vsync'],
        vback=mode['vback'],
        vpol=mode['vpol'],
        ln = mode['ln']
    )

# Remove the last comma and add the closing parenthesis
vhdl_package += "\n     others => (\"--------------------\",    0,              0,       false,           false,        0,        0,       0,      0,      0,   '0',       0,      0,      0,   '0',  0 )\n    );\nend package video_timings_pkg;\n"

# Write the VHDL package to a file
with open('video_timings_pkg.vhdl', 'w') as vhdl_file:
    vhdl_file.write(vhdl_package)

print("VHDL package created successfully!")
