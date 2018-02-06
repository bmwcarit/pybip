# pybip
Python implementation of Bluetooth's Basic Imaging Profile for sending images between devices and includes the ability to resize, and convert images to make them suitable for the receiving device

>This is a prototype implementation where some dummy data is used to make user experience easier. To make it to production grade, you need to tweak a little. Supports only linux platform as of now.

#### Installation
pybip requires Linux and python2 to run.

```
$ cd pybip
$ sudo python setup.py build
$ sudo python setup.py install
```

#### Motivation
This python project is created to test the CoverArts feature of bluetooth's AVRCP 1.6 profile in CAR Infotainment system.
Inorder to test that we primarily need 'bipserver' implementation, but we have implemented 'bipclient' as well to make development easier.
This implementation is developed on top of [pybluez](https://github.com/karulis/pybluez) and [pyobex](https://bitbucket.org/dboddie/pyobex) thanks to them!!

#### Usage Instructions
Make sure the setup have two bluetooth adapters since loopback support is not available in bluetooth, we cannot run both client and server in same hardware.
```
$ hciconfig
hci1:   Type: BR/EDR  Bus: USB
    BD Address: 00:1A:7D:DA:71:05  ACL MTU: 310:10  SCO MTU: 64:8
    UP RUNNING PSCAN ISCAN
    RX bytes:7329 acl:134 sco:0 events:275 errors:0
    TX bytes:28619 acl:199 sco:0 commands:71 errors:0
hci0:   Type: BR/EDR  Bus: USB
    BD Address: F8:16:54:86:11:FD  ACL MTU: 1021:5  SCO MTU: 96:5
    UP RUNNING PSCAN ISCAN
    RX bytes:73576 acl:553 sco:0 events:1472 errors:0
    TX bytes:39635 acl:488 sco:0 commands:421 errors:0
```

Start the server on one of the bluetooth address.
```
$ cd pybip
$ python bipserver.py --address 00:1A:7D:DA:71:05
Starting server for 00:1A:7D:DA:71:05 on port 1
....
```

Start the client by specifying server's bluetooth address.
```
$ cd pybip
$ python bipclient.py
Welcome to the Basic Imaging Profile!
bip> connect 00:1A:7D:DA:71:05
2018-02-06 17:18:33,250 __main__ INFO     Finding BIP service ...
2018-02-06 17:18:36,893 __main__ INFO     BIP service found!
2018-02-06 17:18:36,893 __main__ INFO     Connecting to bip server = (00:1A:7D:DA:71:05, 1)
2018-02-06 17:18:37,939 __main__ INFO     Connect success

bip> capabilities
2018-02-06 17:18:42,775 __main__ DEBUG    Requesting BIP Service capabilities
2018-02-06 17:18:42,775 __main__ INFO     get_capabilities requested
2018-02-06 17:18:42,806 __main__ DEBUG    
<imaging-capabilities>
    <preferred-format encoding="JPEG" pixel="1280*960"/>
    <image-formats encoding="JPEG" pixel="160*120" maxsize="5000"/>
    <image-formats encoding="JPEG" pixel="320*240"/>
    <image-formats encoding="JPEG" pixel="640*480"/>
    <image-formats encoding="JPEG" pixel="1280*960"/>
    <attachment-formats content-type="audio/basic"/>
    <filtering-parameters created="1" modified="1"/>
</imaging-capabilities>

bip> imageslist --max-count=2 --start-offset=1 --latest-images-only=1
2018-02-06 17:19:22,633 __main__ DEBUG    Requesting for available imageslist
2018-02-06 17:19:22,634 __main__ INFO     get_images_list requested. params = {'self': <__main__.BIPClient instance at 0x7fc5a93ade60>, 'list_startoffset': 1, 'latest_captured_images': 1, 'nb_returned_handles': 2}
2018-02-06 17:19:22,914 __main__ DEBUG    
<images-listing>
    <image handle="1000004" created="20000801T060137Z"/>
    <image handle="1000003" created="20000801T060115Z" modified="20000808T071500Z"/>
</images-listing>

bip> imageproperties 1000003
2018-02-06 17:19:36,772 __main__ DEBUG    Requesting for image properties of handle = 1000003
2018-02-06 17:19:36,772 __main__ INFO     get_image_properties requested
2018-02-06 17:19:37,054 __main__ DEBUG    
<image-properties handle="1000003">
    <native encoding="JPEG" pixel="1280*1024" size="1048576"/>
    <variant encoding="JPEG" pixel="640*480"/>
    <variant encoding="JPEG" pixel="160*120"/>
    <variant encoding="GIF" pixel="80*60-640*480"/>
    <attachment content-type="text/plain" name="ABCD0001.txt" size="5120"/>
    <attachment content-type="audio/basic" name="ABCD0001.wav" size="102400"/>
</image-properties>

bip> !ls
bipclient.py  bipclient.pyc  BIP.egg-info  bipheaders.py  bipheaders.pyc  bipserver.py  build  dist  doc  License.txt  __pycache__  README.md  setup.py  tools.py  tools.pyc  xml_data_binding

bip> getimage 1000003
2018-02-06 17:20:23,965 __main__ DEBUG    Requesting for image of handle = 1000003
2018-02-06 17:20:23,965 __main__ INFO     get_image requested
2018-02-06 17:20:25,197 __main__ DEBUG    getimage response. image saved in received_image.jpg

bip> getthumbnail 1000003
2018-02-06 17:20:51,763 __main__ DEBUG    Requesting for thumbnail image of handle = 1000003
2018-02-06 17:20:51,763 __main__ INFO     get_linked_thumbnail requested
2018-02-06 17:20:52,260 __main__ DEBUG    getthumbnail response. image saved in received_thumbnail_image.jpg
bip> disconnect
2018-02-06 17:20:57,584 __main__ DEBUG    Disconnecting bip client with bip server
bip> quit
```

#### License
Code is licensed under the GPL-3.0 (Look into License.txt for more information)
