"""Brige between virtual pinball and MPF.

Based on proc-visual-pinball of destruk, Gerry Stellenberg, Adam Preble and Michael Ocean.
"""
import asyncio
import sys

try:
    import win32com
    import win32com.server.util
    from win32com.server.util import wrap, unwrap
    import pythoncom
except ImportError:
    win32com = None
    util = None
    wrap = None
    unwrap = None
    pythoncom = None

import logging
from mpf.core.bcp.bcp_socket_client import AsyncioBcpClientSocket

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    filename="mpf-vpcom-bridge.txt")


class ISettings:
    _public_methods_ = []
    _public_attrs_ = [  'Value']

    def Value(self, item, item2):
        del item
        del item2
        return True

    def SetValue(self, item, item2):
        del item
        del item2
        return True


class IGames:
    _public_methods_ = []
    _public_attrs_ = [  'Settings']

    def Settings(self):
        settings = ISettings()
        Settings = wrap( settings )
        return Settings

    def SetSettings(self):
        settings = ISettings()
        Settings = wrap( settings )
        return Settings


class Controller:

    """Main Visual Pinball COM interface class."""

    _public_methods_ = [
        'Run',
        'Stop',
        'PrintGlobal'
    ]
    _reg_progid_ = "MPF.Controller"                         # Visual MPF Controller
    _reg_clsid_ = "{196FF002-17F9-4714-4242-A7BD39AD413B}"  # use a unique class guid for Visual MPF Controller

                                                            # on next play
    _public_attrs_ = [
        'Version',
        'GameName',
        'Games',
        'SplashInfoLine',
        'ShowTitle',
        'ShowFrame',
        'ShowDMDOnly',
        'HandleMechanics',
        'HandleKeyboard',
        'DIP',
        'Switch',
        'Mech',
        'Pause',
        'ChangedSolenoids',
        'ChangedGIStrings',
        'ChangedLamps',
        'GetMech'
    ]

    _readonly_attrs_ = [
        'Version',
        'ChangedSolenoids',
        'ChangedLamps',
        'ChangedGIStrings',
        'GetMech'
    ]

    Version = "22222222"
    ShowTitle = None
    ShowFrame = False
    ShowDMDOnly = False
    HandleKeyboard = False
    DIP = False
    GameName = "Game name"

    Pause = None

    HandleMechanics = True
    ErrorMsg = "Python Failed -- check the log"

    def __init__(self, *, loop=None):
        self._reg_clsctx_ = pythoncom.CLSCTX_LOCAL_SERVER   # LocalSever (no InProc) only means game reloads entirely
        self.bcp_client = None
        self.last_switch = None
        self.switches = {}
        if not loop:
            self.loop = asyncio.get_event_loop()
        else:
            self.loop = loop

    # Need to overload this method to tell that we support IID_IServerWithEvents
    def _query_interface_(self, iid):
        """ Return this main interface if the IController class is queried. """
        IID_IController = pythoncom.MakeIID('{CE9ECC7C-960F-407E-B27B-62E39AB1E30F}')
        if iid == IID_IController:
            return win32com.server.util.wrap(self)

    def PrintGlobal(self):
        """Unused."""
        logging.getLogger('vpcom').info("PrintGlobal called.")
        return True

    def _connect(self):
        """Connect to MPF."""
        reader, writer = self.loop.run_until_complete(asyncio.open_connection("localhost", 5051))
        self.bcp_client = AsyncioBcpClientSocket(writer, reader)

    def Run(self, extra_arg=None):
        """Connect to MPF."""
        if extra_arg is not None:
            logging.getLogger('vpcom').info("Run received extra arg!?")
            logging.getLogger('vpcom').info("Arg was {0}".format(extra_arg))

        logging.getLogger('vpcom').info("Starting bridge. Connecting to localhost:5051")

        self._connect()

        self.bcp_client.send("vpcom_bridge", {"subcommand": "start"})
        self.loop.run_until_complete(self.bcp_client.wait_for_response("vpcom_bridge_response"))

        return True

    def Stop(self):
        if self.bcp_client:
            self.bcp_client.send("vpcom_bridge", {"subcommand": "stop"})
            self.loop.run_until_complete(self.bcp_client.wait_for_response("vpcom_bridge_response"))
            self.bcp_client = None

        sys.exit(1)

    def Games(self, rom_name):
        """Return the IGames interface, by wrapping the object."""
        del rom_name
        games = IGames()
        wrapped_games = wrap (games)
        return wrapped_games

    def SetGames(self, rom_name):
        """Return the IGames interface, by wrapping the object."""
        del rom_name
        games = IGames()
        wrapped_games = wrap (games)
        return wrapped_games

    def _dispatch_to_mpf(self, command, **params):
        """Dispatch to MPF and wait for result."""
        params["subcommand"] = command
        self.bcp_client.send("vpcom_bridge", params)
        response = self.loop.run_until_complete(self.bcp_client.wait_for_response("vpcom_bridge_response"))
        return response[1]

    def Switch(self, number):
        """Return the current value of the requested switch."""
        return self._dispatch_to_mpf("Switch", number=number)

    def SetSwitch(self, number, value):
        """Set the value of the requested switch."""
        return self._dispatch_to_mpf("SetSwitch", number=number, value=value)

    def Mech(self, number):
        """Currently unused."""
        return self._dispatch_to_mpf("Mech", number=number)

    def SetMech(self, number):
        """Currently unused."""
        return self._dispatch_to_mpf("SetMech", number=number)

    def GetMech(self, number):
        """Currently unused."""
        return self._dispatch_to_mpf("GetMech", number=number)

    def ChangedSolenoids(self):
        """Return a list of changed coils."""
        return self._dispatch_to_mpf("ChangedSolenoids")

    def ChangedLamps(self):
        """Return a list of changed lamps."""
        return self._dispatch_to_mpf("ChangedLamps")

    def ChangedGIStrings(self):
        """Return a list of changed GI strings."""
        return self._dispatch_to_mpf("ChangedGIStrings")

    def getGIStates(self):
        """Get the current state of the GI strings."""
        return self._dispatch_to_mpf("getGIStates")

    def getLampStates(self):
        """ Gets the current state of the lamps. """
        return self._dispatch_to_mpf("getLampStates")

    def getCoilStates(self):
        """ Gets the current state of the coils. """
        return self._dispatch_to_mpf("getCoilStates")


def Register(pyclass=Controller, p_game=None):
    """ Registration code for the Visual Pinball COM interface for pyprocgame."""
    pythoncom.CoInitialize()
    from win32com.server.register import UseCommandLine
    UseCommandLine(pyclass)

# Run the registration code by default.  Using the commandline param
# "--unregister" will unregister this COM object.
if __name__=='__main__':
    if not win32com:
        raise AssertionError("Please run: pip3 install pywin32")
    Register(Controller)