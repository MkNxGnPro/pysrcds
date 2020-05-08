import struct
import time
from essentials import socket_ops_v2


# Packet types
SERVERDATA_AUTH = 3
SERVERDATA_AUTH_RESPONSE = 2
SERVERDATA_AUTH_FAILED_RESPONSE = -1
SERVERDATA_EXECCOMMAND = 2
SERVERDATA_RESPONSE_VALUE = 0

class RconPacket(object):
    """RCON packet"""

    def __init__(self, pkt_id=0, pkt_type=-1, body=b''):
        self.pkt_id = pkt_id
        self.pkt_type = pkt_type
        self.body = body

    def __str__(self):
        """Return the body string."""
        try:
            return self.body.decode()
        except:
            return self.body

    def size(self):
        """Return the pkt_size field for this packet."""
        return len(self.body) + 10

    def pack(self):
        """Return the packed version of the packet."""
        return struct.pack('<3i{0}s'.format(len(self.body) + 2),
                           self.size(), self.pkt_id, self.pkt_type,
                           bytearray(self.body, 'utf-8'))

def ParsePacket(data):
    """Read one RCON packet"""
    header = data[:struct.calcsize('<3i')]
    (_, pkt_id, pkt_type) = struct.unpack('<3i', header)
    body = data[struct.calcsize('<3i'):][:-2]
    return RconPacket(pkt_id, pkt_type, body)

class RconConnection(object):

    def __init__(self, server, port, password=None):
        """Construct an RconConnection.

        Parameters:
            server (str) server hostname or IP address
            port (int) server port number
            password (str) server RCON password

        """

        self.pk_id = 1
        self.open_requests = {}
        self.server = server
        self.port = port
        self.password = password
        self.con = socket_ops_v2.Socket_Connector(server, port)
        self.con.configuration.LEGACY = True
        self.con.configuration.on_data_recv = self.__match_response__
        def con_closed():
            print("RCON Server Closed")
        self.con.configuration.on_connection_close = con_closed
        self.con.connect()
        if password is not None:
            self.authenticated = None
            self.Authenticate()
        else:
            self.authenticated = False

    def __match_response__(self, data):
        """Matches incoming data to Command requests and Authentication Requests

        You'll not need this
        """
        parsed = ParsePacket(data)
        if parsed.pkt_id in self.open_requests:
            self.open_requests[parsed.pkt_id] = data
        elif parsed.pkt_id == SERVERDATA_AUTH_FAILED_RESPONSE:
            print("[ SERVER ] Authentication: Failed")
            self.con.shutdown()
            self.authenticated = False
        elif parsed.pkt_type == SERVERDATA_AUTH_RESPONSE:
            print("[ SERVER ] Authentication: Passed")
            self.authenticated = True
        
    def Command(self, command, timeout=10):
        """Execute the given RCON command.

        Parameters:
            command (str) the RCON command string (ex. "status")
            timeout (int) how long to wait before the function return None

        Returns the response body
        """
        tk = int(self.pk_id)
        self.open_requests[tk] = None
        self.con.send(RconPacket(tk, SERVERDATA_EXECCOMMAND, command).pack())
        if self.pk_id > 200:
            self.pk_id = 0
        self.pk_id += 1
        tm_out = 0
        while tm_out < timeout and self.open_requests[tk] == None:
            tm_out += 0.05
            time.sleep(0.05)

        if self.open_requests[tk] is None:
            del self.open_requests[tk]
            return False, None
        else:
            packet = ParsePacket(self.open_requests[tk])
            del self.open_requests[tk]
            return not tm_out >= timeout, packet

    def Authenticate(self):
        """ Self Authenticating Function, You can use this to Reauthenticate.
        
        Returns:
            True on Authentication Success
        Raises:
            PermissionError if Authentication Failure
        """
        self.con.send(RconPacket(self.pk_id, SERVERDATA_AUTH, self.password).pack())
        tm_out = 0
        while tm_out < 10 and self.authenticated is None:
            tm_out += 0.05
            time.sleep(0.05)
        if self.authenticated != True:
            raise PermissionError("Authentication Failed")
        return True


#                   TODO
"""
Impliment:

    _read_multi_response

    single_packet_mode (bool) set to True for servers which do not hand 0-length SERVERDATA_RESPONSE_VALUE
                requests (i.e. Factorio).

"""


#                   HOW TO USE
"""   
rcon = RconConnection("192.168.0.12", 25575, "pro")
                    #SERVER IP     PORT   PASSWORD

                    #RconConnection will Authenticate or raise a PermissionError


while True:         #LOOP
    ret, resp = rcon.Command(input("Command:"))
                    # rcon.Command will take in a command, if the command isn't answered ret will be false and resp will be None
    if ret:         # Check is ret is True
        print(resp) # Print the responce
    else:
        print("Command didn't give response")
                    # Alert the user the command didn't return a response
"""