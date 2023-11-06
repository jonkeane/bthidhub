
import asyncio
import re
import sys
import subprocess
from signal import SIGINT

import asyncio_glib
from dasbus.connection import SystemMessageBus

from adapter import BluetoothAdapter
from bluetooth_devices import *
from hid_devices import *
from web import Web

from aiohttp_session import SimpleCookieStorage, session_middleware
from aiohttp_security import check_authorized, \
    is_anonymous, authorized_userid, remember, forget, \
    setup as setup_security, SessionIdentityPolicy
from aiohttp_security.abc import AbstractAuthorizationPolicy

from multiprocessing.connection import Listener

async def handle_message(reader, writer):
    data = await reader.read(100)

    # Try to decode and see if it matches any of our specials
    try:
        message = data.decode()
        if data.decode() == "CONNECT":
            print("Connectione")
            # get the device path to use
            loop = asyncio.get_event_loop()
            if len(bluetooth_devices.all) > 0:
                dev_add = next(iter(bluetooth_devices.all))
            else:
                # There's not a bluetooth device registered, so look in bluetoothctl
                out = subprocess.Popen([ "/usr/bin/bluetoothctl", "devices"], universal_newlines=True, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                # ends up with a double-nested list here, grab the first item — this might also be fragile
                MAC_addy = [ re.findall("(?:[0-9a-fA-F]:?){12}", x) for x in out.stdout.readlines()]
                dev_add = "/org/bluez/hci0/dev_" + MAC_addy[0][0].replace(":", "_")

            # connect
            loop.run_in_executor(None, adapter.device_action, 'connect', dev_add)
            # Now we press spacebar every few seconds while connecting to ensure the keyboard is connected
            # This typically will have one connection that responds "Operation currently not available" and then disconnects
            # but then the second conenction is totally fine
            # TODO: could we "just" wait for the second conenction?
            iterations = 0
            success = 0
            while success < 6:
                if success == 0:
                    await asyncio.sleep(1)
                else:
                    await asyncio.sleep(2)
                bluetooth_devices.send_message(b'\xa1\x01\x00\x00,\x00\x00\x00\x00\x00', True, False)
                print(bluetooth_devices.connected_hosts)
                if len(bluetooth_devices.connected_hosts) >= 1:
                    success += 1
                else:
                    success = 0

                if iterations > 30:
                    print("Didn't ever connect correctly!")
                    break
                iterations += 1

        elif data.decode() == "BROWSER":
            import pdb; pdb.set_trace()
    except UnicodeDecodeError:
        bluetooth_devices.send_message(data, True, False)

async def message_server():
    server = await asyncio.start_server(
        handle_message, '127.0.0.1', 8888)

    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.set_event_loop_policy(asyncio_glib.GLibEventLoopPolicy())
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(SIGINT, sys.exit)
    bus = SystemMessageBus()
    bluetooth_devices = BluetoothDeviceRegistry(bus, loop)
    hid_devices = HIDDeviceRegistry(loop)
    hid_devices.set_bluetooth_devices(bluetooth_devices)
    bluetooth_devices.set_hid_devices(hid_devices)
    adapter = BluetoothAdapter(bus, loop, bluetooth_devices, hid_devices)
    loop.create_task(message_server())

    loop.run_forever()
