# -----------------------------------------------------------------------------
# Script Name: get_timings.py
# Description: Retrieves a c file containing video timings from the web. Parses
#              the file and creates a json file with all CTA-861 timings. Performs
#              a couple of consitency checks
# Author: Felix Miller
# Date: 2025-04-18
# -----------------------------------------------------------------------------
# Note: The timing tables in CTA-861 contain a column "ln". This value is not
#       contained in the kernel sources and is hardcoded here for the modes where
#       it is different from 1.
# Usage:
#   1. Run the script using Python 3. The script will generate a JSON file
#      video_timings.json
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
import requests

# List of array names to include
arrays_to_include = ["edid_cea_modes_1", "edid_cea_modes_193"]

# Ln numbers, see CTA-861-I / Table 1. Those numbers are not contained in the linux kernel sources
# The ln field is 1 in most cases. Except view exceptions which are hardcoded here.
ln4 = [6,7,8,9,10,11,12,13,50,51,58,59]
ln7 = [2,3,14,15,35,36,48,49,56,57]

# URL to drm_edid.c
url = 'https://raw.githubusercontent.com/torvalds/linux/refs/heads/master/drivers/gpu/drm/drm_edid.c'

def get_ln(vic):
    if vic in ln4: return 4
    if vic in ln7: return 7
    return 1

# Function to parse the C file and extract video modes
def parse_mode_string(mode_string):

    # Split into 3 parts
    comment = mode_string.split('/*')[1].split('*/')[0].strip()
    macro = mode_string.split('*/')[1].split("(",1)[1].rsplit(')')[0].strip()
    aspect_elmnt = mode_string.split(".picture_aspect_ratio")[1].split(',')[0].strip()

    # parse comment
    cmnt_cta861_id = int(comment.split('-')[0].strip())
    cmnt_name = comment.split('-')[1].strip().split(' ')[0].strip()
    cmnt_freq = cmnt_name.split('@')[1].split('Hz')[0].strip()
    cmnt_hres_str = cmnt_name.split('x')[0]
    if '(' in cmnt_hres_str:
        cmnt_dbl_clocked = True
        cmnt_hres = int(cmnt_hres_str.split('(')[0])
        cmnt_dbl_hres = int(cmnt_hres_str.split('(')[1].split(')')[0].strip())
    else:
        cmnt_dbl_clocked = False
        cmnt_hres = int(cmnt_hres_str)
        cmnt_dbl_hres = None
    cmnt_vres_str = cmnt_name.split('x')[1].split('@')[0].strip()
    if cmnt_vres_str.endswith('i'):
        cmnt_interlaced = True
        cmnt_vres = int(cmnt_vres_str[:-1])
    else:
        cmnt_interlaced = False
        cmnt_vres = int(cmnt_vres_str)
    cmnt_aspect_ratio = comment.split('-')[1].strip().split(' ')[1].strip()
    cmnt_aspect_nom = int(cmnt_aspect_ratio.split(':')[0].strip())
    cmnt_aspect_denom = int(cmnt_aspect_ratio.split(':')[1].strip())

    # parse macro parameters
    mac_name, mac_type, mac_clock, mac_hdisplay, mac_hsync_start, mac_hsync_end, mac_htotal, mac_hskew, mac_vdisplay, mac_vsync_start, mac_vsync_end, mac_vtotal, mac_vscan, mac_flags = macro.replace(" ","").split(",")
    mac_flags = [x.strip() for x in mac_flags.split('|')]
    mac_dbl_clk = "DRM_MODE_FLAG_DBLCLK" in mac_flags
    mac_interlaced = "DRM_MODE_FLAG_INTERLACE" in mac_flags
    mac_hsync_neg = "DRM_MODE_FLAG_NHSYNC" in mac_flags
    mac_vsync_neg = "DRM_MODE_FLAG_NVSYNC" in mac_flags
    mac_name = mac_name.replace("\"","")
    mac_name_hres = int(mac_name.split('x')[0])
    if 'i' in mac_name:
        mac_name_interlaced = True
        mac_name_vres = int(mac_name.split('x')[1][:-1])
    else:
        mac_name_interlaced = False
        mac_name_vres = int(mac_name.split('x')[1])

    # parse aspect ratio
    aspect_nom = int(aspect_elmnt.rsplit('_',2)[1])
    aspect_denom = int(aspect_elmnt.rsplit('_',2)[2])

    # Check for consistency
    # check for unkown flags
    flags_avail = {"DRM_MODE_FLAG_DBLCLK","DRM_MODE_FLAG_INTERLACE","DRM_MODE_FLAG_NHSYNC","DRM_MODE_FLAG_NVSYNC","DRM_MODE_FLAG_PHSYNC","DRM_MODE_FLAG_PVSYNC"}
    assert not set(mac_flags)-flags_avail, f"Unknown flags for mode {cmnt_name}: {flags_avail-set(mac_flags)}"
    # there must always be one flag for the sync polarity for each dimension
    assert len({"DRM_MODE_FLAG_NHSYNC","DRM_MODE_FLAG_PHSYNC"} & set(mac_flags)) == 1, f"Illegal flag combination for mode {cmnt_name}: {mac_flags}"
    assert len({"DRM_MODE_FLAG_NVSYNC","DRM_MODE_FLAG_PVSYNC"} & set(mac_flags)) == 1, f"Illegal flag combination for mode {cmnt_name}: {mac_flags}"
    if mac_interlaced:
        assert mac_name_interlaced, f"In mode {cmnt_name}, interlaced flag is set but no \"i\" in resolution string of mode name"
        assert cmnt_interlaced, f"In mode {cmnt_name}, interlaced flag is set but no \"i\" in resolution string of comment"
    if mac_dbl_clk:
        assert cmnt_dbl_clocked, f"In mode {cmnt_name}, double clocking flag is set but resolution string in comment does not indicate double clocking"
        assert 2*cmnt_hres == cmnt_dbl_hres, f"In mode {cmnt_name}, double clocked resolution is not twice the actual resolution"
    assert int(mac_hdisplay) == cmnt_hres, f"In mode {cmnt_name}, parsed horizontal resolution does not macht the one in the name of the mode (comment)"
    assert mac_name_hres == cmnt_hres, f"In mode {cmnt_name}, parsed horizontal resolution does not macht the one in the name of the mode"
    assert int(mac_vdisplay) == cmnt_vres, f"In mode {cmnt_name}, parsed vertical resolution does not macht the one in the name of the mode (comment)"
    assert mac_name_vres == cmnt_vres, f"In mode {cmnt_name}, parsed vertical resolution does not macht the one in the name of the mode"
    assert aspect_nom == cmnt_aspect_nom, f"Different values for aspect ratio in comment and initializer for mode {cmnt_name}."
    assert aspect_denom == cmnt_aspect_denom, f"Different values for aspect ratio in comment and initializer for mode {cmnt_name}."
    assert mac_type == "DRM_MODE_TYPE_DRIVER", f"Unknown type for mode {cmnt_name}"
    assert int(mac_hskew) == 0, f"For mode {cmnt_name} hskew is set to {mac_hskew}. Expecting 0 for all modes"
    assert int(mac_vscan) == 0, f"For mode {cmnt_name} vscan is set to {mac_hskew}. Expecting 0 for all modes"
    fps_calc = float(int(mac_clock)*1000)/float(int(mac_vtotal)*int(mac_htotal))
    if mac_interlaced: fps_calc = fps_calc * 2
    if (fps_calc != float(cmnt_freq)):
        if abs(float(cmnt_freq)-fps_calc) < 0.005*float(cmnt_freq):
            print(f"Warning: For mode {cmnt_name}, indicated fps frequency in comment is {cmnt_freq}, but computed on paramters is {fps_calc}. This is within the 0.5% tolerance.")
        else:
            assert False, (f"For mode {cmnt_name}, indicated fps frequency in comment is {cmnt_freq}, but computed on paramters is {fps_calc}. This is outside of the 0.5% tolerance.")

    mode = {
        "vic": int(cmnt_cta861_id),
        "name": str(mac_name) +"@" + str(cmnt_freq) + "Hz",
        "pxl_clk_khz" : int(mac_clock),
        "hactive": int(mac_hdisplay),
        "vactive": int(mac_vdisplay),
        "interlaced": mac_interlaced,
        "double_clocked": mac_dbl_clk,
        "htotal": int(mac_htotal),
        "hblank": int(mac_htotal) - int(mac_hdisplay),
        "hfront": int(mac_hsync_start) - int(mac_hdisplay),
        "hsync": int(mac_hsync_end) - int(mac_hsync_start),
        "hback": int(mac_htotal) - int(mac_hsync_end),
        "hpol": 0 if mac_hsync_neg else 1,
        "vtotal": int(mac_vtotal),
        "vblank": int(mac_vtotal) - int(mac_vdisplay),
        "vfront": int(mac_vsync_start) - int(mac_vdisplay),
        "vsync": int(mac_vsync_end) - int(mac_vsync_start),
        "vback": int(mac_vtotal) - int(mac_vsync_end),
        "vpol": 0 if mac_vsync_neg else 1,
        "ln" : get_ln(int(cmnt_cta861_id))
    }

    return mode


# Function to parse the C file and extract video modes
def parse_c_file(file_content, arrays_to_include):
    video_modes = []
    lines = file_content.split('\n')

    current_array = None
    for line in lines:
        line = line.strip()
        if line.startswith("};"):
            current_array = None
            mode_string = None
            continue
        if line.startswith("static const struct drm_display_mode"):
            array_name = line.split()[4].split('[')[0].strip()
            if array_name in arrays_to_include:
                current_array = array_name
                continue
        if current_array:
            if line.startswith("/*"):
                mode_string = line
            else:
                mode_string += line
            if line.endswith("},"):
                video_modes.append(parse_mode_string(mode_string))

    return video_modes

# Fetch the C file content from the URL
response = requests.get(url)
file_content = response.text

# Parse the C file and get the video modes
video_modes = parse_c_file(file_content, arrays_to_include)

print(f"{len(video_modes)} video modes parsed.")

# Write the data to a JSON file
with open('video_timings.json', 'w') as json_file:
    json.dump(video_modes, json_file, indent=4)

print("JSON file created successfully!")
