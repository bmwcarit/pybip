# Copyright (c) 2018 Kannan Subramani <Kannan.Subramani@bmw.de>
# SPDX-License-Identifier: GPL-3.0
# -*- coding: utf-8 -*-
"""Implementation of bipclient to test bipserver ( for cover art of AVRCP )"""

import atexit
import io
import logging
import os
import readline
import sys
import tools

import bluetooth
import bipheaders as headers
import cmd2

from optparse import make_option
from PIL import Image
from PyOBEX import client, responses
from xml_data_binding import image_descriptor, image_handles_descriptor, images_listing

logger = logging.getLogger(__name__)


class BIPClient(client.Client):
    """Basic Imaging Profile Client"""

    def __init__(self, address, port):
        client.Client.__init__(self, address, port)

    def get_capabilities(self):
        """Requests level of support for various imaging capabilities"""
        logger.info("get_capabilities requested")
        # connection_id will be automatically prepended by pyobex/client.py:_send_headers
        header_list = [headers.Type("x-bt/img-capabilities")]
        return self.get(header_list=header_list)

    def get_images_list(self, nb_returned_handles=0, list_startoffset=0, latest_captured_images=0x00):
        """Requests list of handles for available images along with file info like cdate, mdate etc"""
        logger.info("get_images_list requested. params = %s", locals())
        app_parameters_dict = {
            "NbReturnedHandles": headers.NbReturnedHandles(nb_returned_handles),
            "ListStartOffset": headers.ListStartOffset(list_startoffset),
            "LatestCapturedImages": headers.LatestCapturedImages(latest_captured_images)
        }

        # construct the image_handles_descriptor xml using xml_data_binding
        root = image_handles_descriptor.image_handles_descriptor()
        root.filtering_parameters = image_handles_descriptor.filtering_parameters(
            created="19990101T000000Z-20010101T235959Z")
        img_handles_desc_data = tools.export_xml(root)
        header_list = [headers.Type("x-bt/img-listing"),
                       headers.App_Parameters(app_parameters_dict),
                       headers.Img_Descriptor(img_handles_desc_data)]
        return self.get(header_list=header_list)

    def get_image_properties(self, img_handle):
        """Requests info regarding image formats, encodings etc."""
        logger.info("get_image_properties requested")
        header_list = [headers.Type("x-bt/img-properties"), headers.Img_Handle(img_handle)]
        return self.get(header_list=header_list)

    def get_image(self, image_handle):
        """Requests an Image with specified format and encoding"""
        logger.info("get_image requested")
        img_descriptor_object = image_descriptor.image_descriptor()
        img_descriptor_object.image = image_descriptor.image(encoding="JPEG", pixel="1280*1024")
        header_list = [headers.Type("x-bt/img-img"), headers.Img_Handle(image_handle),
                       headers.Img_Descriptor(tools.export_xml(img_descriptor_object))]
        return self.get(header_list=header_list)

    def get_linked_thumbnail(self, image_handle):
        """Requests thumbnail version of the images"""
        logger.info("get_linked_thumbnail requested")
        header_list = [headers.Type("x-bt/img-thm"), headers.Img_Handle(image_handle)]
        return self.get(header_list=header_list)


class REPL(cmd2.Cmd):
    """REPL to use BIP client"""

    def __init__(self):
        cmd2.Cmd.__init__(self)
        self.prompt = self.colorize("bip> ", "yellow")
        self.intro = self.colorize("Welcome to the Basic Imaging Profile!", "green")
        self.client = None
        self._valid_image_handle = None
        self._store_history()
        cmd2.set_use_arg_list(False)

    @staticmethod
    def _store_history():
        history_file = os.path.expanduser('~/.bipclient_history')
        if not os.path.exists(history_file):
            with open(history_file, "w") as fobj:
                fobj.write("")
        readline.read_history_file(history_file)
        atexit.register(readline.write_history_file, history_file)

    @cmd2.options([], arg_desc="server_address")
    def do_connect(self, line, opts):
        """Connects to BIP Server"""
        server_address = line
        if not server_address:
            raise TypeError("server_address cannot be empty")
        logger.info("Finding BIP service ...")
        services = bluetooth.find_service(address=server_address, uuid=headers.COVERART_UUID)
        if not services:
            sys.stderr.write("No BIP (CoverArts) service found\n")
            sys.exit(1)

        host = services[0]["host"]
        port = services[0]["port"]
        logger.info("BIP service found!")

        self.client = BIPClient(host, port)
        logger.info("Connecting to bip server = (%s, %s)", host, port)
        result = self.client.connect(header_list=[headers.Target(headers.COVERART_UUID)])
        if not isinstance(result, responses.ConnectSuccess):
            logger.error("Connect Failed, Terminating the bip client..")
            sys.exit(2)
        logger.info("Connect success")
        self.prompt = self.colorize("bip> ", "green")

    @cmd2.options([], arg_desc="")
    def do_disconnect(self, line, opts):
        """Disconnects the BIP connection"""
        if self.client is None:
            logger.error("BIPClient is not even connected.. Connect and then try disconnect")
            sys.exit(2)
        logger.debug("Disconnecting bip client with bip server")
        self.client.disconnect()
        self.client = None
        self.prompt = self.colorize("bip> ", "yellow")

    @cmd2.options([], arg_desc="")
    def do_capabilities(self, line, opts):
        """Returns the capabilities supported by BIP Server"""
        logger.debug("Requesting BIP Service capabilities")
        result = self.client.get_capabilities()
        if isinstance(result, responses.FailureResponse):
            logger.error("GetCapabilities failed ... reason = %s", result)
            return
        header, capabilities = result
        logger.debug("\n" + capabilities)

    @cmd2.options([make_option('-c', '--max-count', type=int, default=0,
                               help="Maximum number of image handles to be returned"),
                   make_option('-o', '--start-offset', type=int, default=0,
                               help="List start offset"),
                   make_option('-x', '--latest-images-only', type=int, default=0,
                               help="Include latest captured images only")
                   ], arg_desc="")
    def do_imageslist(self, args, opts):
        """Returns list of available images"""
        logger.debug("Requesting for available imageslist")
        result = self.client.get_images_list(opts.max_count, opts.start_offset, opts.latest_images_only)
        if isinstance(result, responses.FailureResponse):
            logger.error("GetImagesList failed ... reason = %s", result)
            return
        header, images_list = result
        logger.debug("\n" + images_list)
        parsed_img_listing = images_listing.parseString(images_list, silence=True)
        if parsed_img_listing.image:
            self._valid_image_handle = parsed_img_listing.image[0].handle

    @cmd2.options([], arg_desc="image_handle")
    def do_imageproperties(self, line, opts):
        """Gets the properties of image for given image_handle"""
        logger.debug("Requesting for image properties of handle = %s", line)
        result = self.client.get_image_properties(line)
        if isinstance(result, responses.FailureResponse):
            logger.error("GetImageProperties failed ... reason = %s", result)
            return
        header, image_prop = result
        logger.debug("\n" + image_prop)

    @cmd2.options([], arg_desc="image_handle")
    def do_getimage(self, line, opts):
        """Gets image for given image_handle"""
        logger.debug("Requesting for image of handle = %s", line)
        result = self.client.get_image(line)
        if isinstance(result, responses.FailureResponse):
            logger.error("GetImage failed ... reason = %s", result)
            return
        header, image_data = result
        im = Image.open(io.BytesIO(image_data))
        im.save("received_image.jpg")
        logger.debug("getimage response. image saved in received_image.jpg")
        im.show()

    @cmd2.options([], arg_desc="image_handle")
    def do_getthumbnail(self, line, opts):
        """Gets Thumbnail version of image for given image_handle"""
        logger.debug("Requesting for thumbnail image of handle = %s", line)
        result = self.client.get_linked_thumbnail(line)
        if isinstance(result, responses.FailureResponse):
            logger.error("GetThumbnail failed ... reason = %s", result)
            return
        header, image_data = result
        im = Image.open(io.BytesIO(image_data))
        im.save("received_thumbnail_image.jpg")
        logger.debug("getthumbnail response. image saved in received_thumbnail_image.jpg")
        im.show()

    @cmd2.options([], arg_desc="server_address")
    def do_test(self, line, opts):
        """Triggers Basic tests for all functionality of BIPClient"""
        self.do_connect(line)
        self.do_capabilities("")
        self.do_imageslist("")
        self.do_imageslist("--max-count 2 --start-offset 1 --latest-images-only 1")
        if self._valid_image_handle:
            self.do_imageproperties(self._valid_image_handle)
            self.do_getimage(self._valid_image_handle)
            self.do_getthumbnail(self._valid_image_handle)
        self._valid_image_handle = None
        self.do_disconnect("")

    do_q = cmd2.Cmd.do_quit


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)-8s %(message)s')
    repl = REPL()
    repl.cmdloop()
