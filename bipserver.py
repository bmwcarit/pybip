# Copyright (c) 2018 Kannan Subramani <Kannan.Subramani@bmw.de>
# SPDX-License-Identifier: GPL-3.0
# -*- coding: utf-8 -*-
"""Implementation of bipserver ( for cover art of AVRCP, only contains Image pull feature )"""

import argparse
import copy
import logging
import operator
import os
import sys
import tools

import bluetooth
import bipheaders as headers
import dateutil.parser

from PyOBEX import server, responses, requests
from xml_data_binding import image_descriptor, image_handles_descriptor, images_listing


logger = logging.getLogger(__name__)


class BIPServer(server.Server):

    def __init__(self, device_address, rootdir=os.getcwd()):
        server.Server.__init__(self, device_address)
        self.rootdir = rootdir

    def process_request(self, connection, request):
        """Processes the request from the connection."""
        logger.info("\n-----------------------------------")
        if isinstance(request, requests.Connect):
            logger.debug("Request type = connect")
            self.connect(connection, request)
        elif isinstance(request, requests.Disconnect):
            logger.debug("Request type = disconnect")
            self.disconnect(connection, request)
        elif isinstance(request, requests.Put):
            logger.debug("Request type = put")
            self.put(connection, request)
        elif isinstance(request, requests.Get):
            logger.debug("Request type = get")
            self.get(connection, request)
        else:
            logger.debug("Request type = Unknown. so rejected")
            self._reject(connection)

    def get(self, socket, request):
        decoded_header = self._decode_header_data(request)
        if request.is_final():
            logger.debug("request is final")
            if decoded_header["Type"] == "x-bt/img-capabilities":
                self._get_capabilities(socket, decoded_header)
            elif decoded_header["Type"] == "x-bt/img-listing":
                self._get_images_list(socket, decoded_header)
            elif decoded_header["Type"] == "x-bt/img-properties":
                self._get_image_properties(socket, decoded_header)
            elif decoded_header["Type"] == "x-bt/img-img":
                self._get_image(socket, decoded_header)
            elif decoded_header["Type"] == "x-bt/img-thm":
                self._get_linked_thumbnail(socket, decoded_header)
            else:
                logger.error("Requested type = %s is not supported yet.", decoded_header["Type"])
                self.send_response(socket, responses.Bad_Request())

    def _decode_header_data(self, request):
        """Decodes all headers in given request and return the decoded values in dict"""
        header_dict = {}
        for header in request.header_data:
            if isinstance(header, headers.Name):
                header_dict["Name"] = header.decode().rstrip("\r\n\t\0")
                logger.info("Name = %s" % header_dict["Name"])
            elif isinstance(header, headers.Length):
                header_dict["Length"] = header.decode().rstrip("\r\n\t\0")
                logger.info("Length = %i" % header_dict["Length"])
            elif isinstance(header, headers.Type):
                header_dict["Type"] = header.decode().rstrip("\r\n\t\0")
                logger.info("Type = %s" % header_dict["Type"])
            elif isinstance(header, headers.Connection_ID):
                header_dict["Connection_ID"] = header.decode().rstrip("\r\n\t\0")
                logger.info("Connection ID = %s" % header_dict["Connection_ID"])
            elif isinstance(header, headers.Img_Descriptor):
                header_dict["Img_Descriptor"] = header.decode().rstrip("\r\n\t\0")
                logger.info("Img Descriptor = %s" % header_dict["Img_Descriptor"])
            elif isinstance(header, headers.Img_Handle):
                header_dict["Img_Handle"] = header.decode().rstrip("\r\n\t\0")
                logger.info("Img Handle = %s" % header_dict["Img_Handle"])
            elif isinstance(header, headers.App_Parameters):
                header_dict["App_Parameters"] = header.decode()
                logger.info("App Parameters are :")
                for param, value in header_dict["App_Parameters"].items():
                    logger.info("{param}: {value}".format(param=param, value=value.decode()))
            else:
                logger.error("Some Header data is not yet added in _decode_header_data")
                raise NotImplementedError("Some Header data is not yet added in _decode_header_data")
        return header_dict

    def _decode_app_params(self, app_params):
        """This will decode or populate app_params with default value."""
        decoded_app_params = {}
        if "NbReturnedHandles" in app_params:
            decoded_app_params["NbReturnedHandles"] = app_params["NbReturnedHandles"].decode()
        if "ListStartOffset" in app_params:
            decoded_app_params["ListStartOffset"] = app_params["ListStartOffset"].decode()
        if "LatestCapturedImages" in app_params:
            decoded_app_params["LatestCapturedImages"] = app_params["LatestCapturedImages"].decode()
        return decoded_app_params

    def _get_capabilities(self, socket, decoded_header):
        """Returns level of support for various imaging capabilities"""
        logger.info("_get_capabilities invoked")
        # TODO: replace with real data
        capabilities_object = tools.generate_dummy_imaging_capabilities()
        header_list = [headers.End_Of_Body(tools.export_xml(capabilities_object))]
        self.send_response(socket, responses.Success(), header_list)

    def _get_images_list(self, socket, decoded_header):
        """Returns list of handles for available images along with file info like cdate, mdate etc"""
        logger.info("_get_images_list invoked")
        app_params = self._decode_app_params(decoded_header["App_Parameters"])

        # TODO: replace with real data
        images_listing_object = tools.generate_dummy_images_listing()

        nb_returned_handles = app_params["NbReturnedHandles"]
        list_startoffset = app_params["ListStartOffset"]
        latest_captured_images = app_params["LatestCapturedImages"]

        # filtering images of images_listing using filtering_parameters
        img_handles_desc = image_handles_descriptor.parseString(decoded_header["Img_Descriptor"], silence=True)
        filtered_images_listing = self._filter_images_listing(img_handles_desc, images_listing_object)
        if nb_returned_handles == 0:
            nb_returned_handles_hdr = {"NbReturnedHandles":
                                       headers.NbReturnedHandles(len(filtered_images_listing.image))
                                       }
            empty_image_listing = images_listing.images_listing()
            header_list = [headers.App_Parameters(nb_returned_handles_hdr),
                           headers.Img_Descriptor(tools.export_xml(img_handles_desc)),
                           headers.End_Of_Body(tools.export_xml(empty_image_listing))]

        else:
            # restrict the images of images_listing using ListStartOffset and NbReturnedHandles
            restricted_images_listing = self._restricted_images_listing(filtered_images_listing,
                                                                        list_startoffset,
                                                                        nb_returned_handles)

            # order descending based on created time to get latest captured images
            if latest_captured_images:
                restricted_images_listing.image.sort(key=operator.attrgetter("created"), reverse=True)

            nb_returned_handles_hdr = {"NbReturnedHandles":
                                       headers.NbReturnedHandles(len(restricted_images_listing.image))
                                       }
            header_list = [headers.App_Parameters(nb_returned_handles_hdr),
                           headers.Img_Descriptor(tools.export_xml(img_handles_desc)),
                           headers.End_Of_Body(tools.export_xml(restricted_images_listing))]
        self.send_response(socket, responses.Success(), header_list)

    @staticmethod
    def _restricted_images_listing(images_listing, list_startoffset, nb_returned_handles):
        images_listing_copy = copy.deepcopy(images_listing)
        images_listing_copy.image = images_listing_copy.image[list_startoffset:
                                                              list_startoffset + nb_returned_handles]
        return images_listing_copy

    @staticmethod
    def _filter_images_listing(img_handles_desc, images_listing):
        """filters the images_listing based on filtering_parameters in img_handles_desc"""
        filtering_parameters = img_handles_desc.filtering_parameters
        images_listing_copy = copy.deepcopy(images_listing)
        for image in images_listing.image:
            match = True
            if filtering_parameters.created:
                match &= (dateutil.parser.parse(image.created) in tools.DatetimeRange(filtering_parameters.created))
            if filtering_parameters.modified:
                match &= (dateutil.parser.parse(image.modified) in tools.DatetimeRange(filtering_parameters.modified))
            if filtering_parameters.encoding:
                match &= (image.encoding == filtering_parameters.encoding)
            if filtering_parameters.pixel:
                match &= (tools.Pixel(image.pixel) in tools.PixelRange(filtering_parameters.pixel))
            if not match:
                images_listing_copy.image.remove(image)
        return images_listing_copy

    def _get_image_properties(self, socket, decoded_header):
        """Returns info regarding image formats, encodings etc."""
        logger.info("_get_image_properties invoked")
        handle = decoded_header["Img_Handle"]
        if handle not in tools.DUMMY_IMAGE_HANDLES:
            self.send_response(socket, responses.Not_Found(), [])
            return
        # TODO: replace with real data and get the properties for specified handle
        img_prop_obj = tools.generate_dummy_image_properties(handle)
        header_list = [headers.End_Of_Body(tools.export_xml(img_prop_obj))]
        self.send_response(socket, responses.Success(), header_list)

    def _get_image(self, socket, decoded_header, thumbnail=False):
        """Returns an Image with specified format and encoding"""
        logger.info("_get_image invoked")
        handle = decoded_header["Img_Handle"]
        if handle not in tools.DUMMY_IMAGE_HANDLES:
            self.send_response(socket, responses.Not_Found(), [])
            return
        if not thumbnail:
            description = image_descriptor.parseString(decoded_header["Img_Descriptor"], silence=True)

        # construct a dummy image
        if not thumbnail:
            imagefile = tools.generate_dummy_image(handle, description.image.encoding,
                                                   map(int, description.image.pixel.split("*")))
        else:
            imagefile = tools.generate_dummy_image(handle, thumbnail=True)
        imagefile_size = len(imagefile)

        # TODO: adjust the max packet length in obex connect, since bt rfcomm can send only ~1000 bytes at once
        max_length = 700
        bytes_transferred = 0

        if imagefile_size < max_length:
            image_last_chunk = imagefile
        else:
            while bytes_transferred < imagefile_size:
                image_chunk = imagefile[bytes_transferred: (bytes_transferred + max_length)]
                header_list = [headers.Length(max_length), headers.Body(image_chunk)]
                # 'continue' response and process the subsequent requests
                self.send_response(socket, responses.Continue(), header_list)
                while True:
                    request = self.request_handler.decode(self.connection)
                    if not isinstance(request, requests.Get_Final):
                        self.process_request(self.connection, request)
                        continue
                    else:
                        break
                bytes_transferred += max_length
            image_last_chunk = ""

        header_list = [headers.Length(imagefile_size), headers.End_Of_Body(image_last_chunk)]
        self.send_response(socket, responses.Success(), header_list)

    def _get_linked_thumbnail(self, socket, decoded_header):
        """Returns thumbnail version of the images"""
        logger.info("_get_linked_thumbnail invoked")
        self._get_image(socket, decoded_header, thumbnail=True)

    def start_service(self, port=bluetooth.PORT_ANY):
        name = "Basic Imaging Profile (CoverArt)"
        service_classes = [bluetooth.IMAGING_RESPONDER_CLASS]
        service_profiles = [bluetooth.IMAGING_PROFILE]
        provider = "BMW CarIT GmbH"
        description = "Basic Imaging Profile (for AVRCP CoverArts)"
        protocols = [bluetooth.L2CAP_UUID, bluetooth.RFCOMM_UUID, bluetooth.OBEX_UUID]

        # advertise_service is not needed if BIP is used only in AVRCP coverarts
        # Remove after integrating it into AVRCP coverarts
        return server.Server.start_service(
            self, port, name, headers.COVERART_UUID, service_classes, service_profiles,
            provider, description, protocols
        )

    def serve(self, socket):
        """Override: changes 'connection' as instance variable.
        So we can access it in other methods, enables handling
        of 'Continue' response and subsequent requests
        """
        while True:
            self.connection, self.address = socket.accept()
            if not self.accept_connection(*self.address):
                self.connection.close()
                continue
            self.connected = True

            while self.connected:
                request = self.request_handler.decode(self.connection)
                self.process_request(self.connection, request)


def run_server(device_address, rootdir):
    # Run the server in a function so that, if the server causes an exception
    # to be raised, the server instance will be deleted properly, giving us a
    # chance to create a new one and start the service again without getting
    # errors about the address still being in use.
    try:
        bip_server = BIPServer(device_address, rootdir)
        socket = bip_server.start_service()
        bip_server.serve(socket)
    except IOError:
        bip_server.stop_service(socket)


def main():
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)-8s %(message)s')

    parser = argparse.ArgumentParser(description="Basic Imaging Profile server...")
    parser.add_argument("--address", required=True,
                        help="bluetooth address to start the server")
    parser.add_argument("--imagedir", default=os.getcwd(),
                        help="images directory from where images needs to be served")
    args = parser.parse_args()

    while True:
        run_server(args.address, args.imagedir)

    sys.exit(0)


if __name__ == "__main__":
    main()
