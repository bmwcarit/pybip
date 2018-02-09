# Copyright (c) 2018 Kannan Subramani <Kannan.Subramani@bmw.de>
# SPDX-License-Identifier: GPL-3.0
# -*- coding: utf-8 -*-
"""Tools and utilities to support BIP (Basic Imaging Profile)"""

import datetime
import functools
import io

import dateutil.parser

from PIL import Image
from xml_data_binding import *


def export_xml(root_element):
    """export to xml from root element of xml data binding object"""
    outfile = io.BytesIO()
    root_element.export(outfile, 0)
    outfile.seek(0)
    buf = outfile.read()
    data = ""
    while buf:
        data += buf
        buf = outfile.read()
    # xml meta tag is not used in Basic Imaging Profile
    return data.replace('<?xml version="1.0" ?>', '')


class DatetimeRange(object):
    """To represent datetime range"""

    def __init__(self, timestamp_range):
        """Accepts the timestamp range in following format

        Acceptable formats:
        ===================
        1. YYYYMMDDTHHMMSS[Z]-YYYYMMDDTHHMMSS[Z]
        2. *-*
        3. *-YYYYMMDDTHHMMSS[Z]
        4. YYYYMMDDTHHMMSS[Z]-*
        """
        self.start, self.end = self._parse_range(timestamp_range)

    def _parse_range(self, timestamp_range):
        if "-" not in timestamp_range:
            raise TypeError("Given value is not a range. ex: YYYYMMDDTHHMMSS[Z]-YYYYMMDDTHHMMSS[Z]")
        start, end = timestamp_range.split("-")
        if start == "*":
            start = datetime.datetime.min
        if end == "*":
            end = datetime.datetime.max
        return map(dateutil.parser.parse, [start, end])

    def contains(self, value):
        return self.start <= value <= self.end

    def __contains__(self, value):
        return self.contains(value)

    def __str__(self):
        return str(self.start) + "  -  " + str(self.end)


@functools.total_ordering
class Pixel(object):
    def __init__(self, pixel_str):
        self.width, self.height = self._parse_pixel_str(pixel_str)

    def _parse_pixel_str(self, pixel_str):
        return map(int, pixel_str.split("*"))

    def __eq__(self, other):
        return self.width == other.width and self.height == other.height

    def __lt__(self, other):
        if self.height > other.height:
            return False
        elif self.height == other.height and self.width > other.width:
            return False
        else:
            return True

    def __str__(self):
        return "(width={width}, height={height})".format(width=str(self.width), height=str(self.height))


class PixelRange(object):
    def __init__(self, pixel_range_str):
        """Accepts the timestamp range in following format

        Acceptable formats:
        ===================
        1. 80*60-1280*1024
        2. *-*
        3. *-1280*1024
        4. 80*60-*
        5. W1**-W2*H2 (#TODO: not yet handled)
        """
        self.start, self.end = self._parse_range(pixel_range_str)

    def _parse_range(self, pixel_range_str):
        if "-" not in pixel_range_str:
            raise TypeError("Given value is not a range.")
        start, end = pixel_range_str.split("-")
        if start == "*":
            start = "0*0"
        if end == "*":
            end = "65535*65535"
        return map(Pixel, [start, end])

    def contains(self, value):
        return self.start <= value <= self.end

    def __contains__(self, value):
        return self.contains(value)

    def __str__(self):
        return str(self.start) + "  -  " + str(self.end)


DUMMY_IMAGE_HANDLES = ["1000001", "1000003", "1000004"]


def generate_dummy_image(handle, format="JPEG", size=(128, 128), thumbnail=False):
    data = ""
    width, height = size
    color = chr(255) + chr(255) + chr(0)
    if handle == DUMMY_IMAGE_HANDLES[0]:
        color = chr(200) + chr(0) + chr(0)
    elif handle == DUMMY_IMAGE_HANDLES[1]:
        color = chr(0) + chr(200) + chr(0)
    elif handle == DUMMY_IMAGE_HANDLES[2]:
        color = chr(0) + chr(0) + chr(200)
    for i in range(height):
        for j in range(width):
            data += color
    im = Image.fromstring("RGB", (width, height), data)
    buf = io.BytesIO()
    if thumbnail:
        im.thumbnail((200, 200))
    im.save(buf, format=format)
    return buf.getvalue()


def generate_dummy_imaging_capabilities():
    root = imaging_capabilities.imaging_capabilities()
    root.preferred_format = imaging_capabilities.preferred_format(encoding="JPEG", pixel="1280*960")
    root.image_formats.append(imaging_capabilities.image_formats(encoding="JPEG", pixel="160*120", maxsize="5000"))
    root.image_formats.append(imaging_capabilities.image_formats(encoding="JPEG", pixel="320*240"))
    root.image_formats.append(imaging_capabilities.image_formats(encoding="JPEG", pixel="640*480"))
    root.image_formats.append(imaging_capabilities.image_formats(encoding="JPEG", pixel="1280*960"))
    root.attachment_formats.append(imaging_capabilities.attachment_formats(content_type="audio/basic"))
    root.filtering_parameters = imaging_capabilities.filtering_parameters(created="1", modified="1")
    return root


def generate_dummy_images_listing():
    root = images_listing.images_listing()
    root.image.append(images_listing.image(handle=DUMMY_IMAGE_HANDLES[0], created="20000801T060000Z"))
    root.image.append(images_listing.image(handle=DUMMY_IMAGE_HANDLES[1],
                                           created="20000801T060115Z", modified="20000808T071500Z"))
    root.image.append(images_listing.image(handle=DUMMY_IMAGE_HANDLES[2], created="20000801T060137Z"))
    return root


def generate_dummy_image_properties(handle):
    root = image_properties.image_properties()
    root.handle = handle
    root.native = image_properties.native(encoding="JPEG", pixel="1280*1024", size="1048576")
    root.variant.append(image_properties.variant(encoding="JPEG", pixel="640*480"))
    root.variant.append(image_properties.variant(encoding="JPEG", pixel="160*120"))
    root.variant.append(image_properties.variant(encoding="GIF", pixel="80*60-640*480"))
    root.attachment.append(image_properties.attachment(
        content_type="text/plain", name="ABCD0001.txt", size="5120"))
    root.attachment.append(image_properties.attachment(
        content_type="audio/basic", name="ABCD0001.wav", size="102400"))
    return root
