# Copyright (C) 2020 Christopher Gearhart
# chris@bblanimation.com
# http://bblanimation.com/


# System imports
import fnmatch
import json
import os
import sys

# Blender imports
import bpy


def expand_frames(frame_range):
    """ Helper function takes frame range string and returns list with frame ranges expanded """
    frames = []
    for i in frame_range:
        if type(i) == list:
            frames += range(i[0], i[1]+1)
        elif type(i) == int:
            frames.append(i)
        else:
            sys.stderr.write("Unknown type in frames list")

    return list(set(frames))


def ints_to_frame_ranges(ints:list):
    """ turns list of ints to list of frame ranges """
    frame_ranges_s = ""
    i = 0
    while i < len(ints):
        s = ints[i] # start index
        e = s       # end index
        while i < len(ints) - 1 and ints[i + 1] - ints[i] == 1:
            e += 1
            i += 1
        frame_ranges_s += "{s},".format(s=s) if s == e else "{s}-{e},".format(s=s, e=e)
        i += 1
    return frame_ranges_s[:-1]


def list_missing_frames(filename:str, frame_range:list):
    """ lists all missing files from local render dump directory

    Parameters:
    filename    - Name of the file (e.g. name prepended to '_####.png')
    frame_range - List of lists, formatted '[startFrame, endFrame]'

    assumes frame number is padded to 4 digits, and '_' follows the filename
    """
    dump_folder = get_render_dump_path()[0]
    comp_list = expand_frames(frame_range)
    if not os.path.exists(dump_folder):
        error_msg = "The folder does not exist: {path}".format(path=dump_folder)
        sys.stderr.write(error_msg)
        print(error_msg)
        return str(comp_list)[1:-1]
    try:
        all_files = os.listdir(dump_folder)
    except:
        error_msg = "Error listing directory {path}".format(path=dump_folder)
        sys.stderr.write(error_msg)
        print(error_msg)
        return str(comp_list)[1:-1]
    im_list = []
    for f in all_files:
        if "_average." not in f and not fnmatch.fnmatch(f, "*_seed-*_????.???") and f[:len(filename)] == filename:
            im_list.append(int(f[len(filename) + 1:len(filename) + 5]))
    # compare lists to determine which frames are missing from imlist
    missing_f = [i for i in comp_list if i not in im_list]
    # convert list of ints to string with frame ranges
    missing_fr = ints_to_frame_ranges(missing_f)
    # return the list of missing frames as string, omitting the open and close brackets
    return missing_fr
