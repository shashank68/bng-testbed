import time
from multiprocessing import Process
from subprocess import PIPE

from nest import config
from nest.engine import exec_exp_commands, exec_subprocess
from nest.topology import *

config.set_value("assign_random_names", False)


def pexec(cmd):
    print(exec_subprocess(cmd, shell=True, output=True))


##############################
# Topology
#
# dhcp_client --><- Switch -><-- bng_router --><-- dhcp_server
##############################

dhcp_client = Node("cli")
switch = Switch("swi")
bng_router = Node("bng")
dhcp_server = Node("ser")


# Enabling IP forwarding for the routers
bng_router.enable_ip_forwarding()
(server_if, router_server_if) = connect(dhcp_server, bng_router, "s_r", "r_s")

pexec(
    f"""
    ip netns exec {dhcp_client.id} 
    ip netns exec {switch.id} touch defg.txt
    """
)
# time.sleep(1000)

(bng_sw_if, sw_bng_if) = connect(bng_router, switch, "b_s", "s_b")
(client_if, sw_cl_if) = connect(dhcp_client, switch, "cl", "s_c")
bng_sw_if.set_address("10.0.0.1/24")

# with dhcp_client:
#     print(exec_subprocess(f"ip link add link {client_if.id} name clv type vlan id 20"))

client_if.set_address("10.0.0.2/24")
router_server_if.set_address("10.0.1.1/24")
server_if.set_address("10.0.1.2/24")

# time.sleep(1000)
with dhcp_client:
    pexec(
        f"""
        ip link add link {client_if.id} name c_sv type vlan id 5
        ip link set dev c_sv up
        """
    )
with switch:

    pexec(f"ip link set dev {switch.id} type bridge vlan_filtering 1")
    # pexec(
    #     f"""
    #     ip link set {sw_bng_if.id} nomaster
    #     # ip link set {sw_cl_if.id} nomaster
        
    #     # ip link add link {sw_cl_if.id} name clv type vlan id 5
    #     # ip link set dev s_cv up
    #     # ip link set s_cv master {switch.id}

    #     ip link add link {sw_bng_if.id} name blv type vlan id 6
    #     ip link set dev s_bv up
    #     ip link set s_bv master {switch.id}
    #     """
    # )
    # pexec(f"ip link add link {sw_bng_if.id} name sbv type vlan id 5")
    # pexec(f"bridge vlan del dev clv vid 1")
    # pexec(f"bridge vlan del dev blv vid 1")
    # pexec(f"bridge vlan del dev {switch.id} vid 1 self")
    # to/from client frames

    # pexec(f"bridge vlan add dev clv vid 19 pvid untagged")
    # print(exec_subprocess(f"bridge vlan add dev {switch.id} vid 20 self"))
    # print(exec_subprocess(f"bridge vlan add dev {sw_cl_if.id} vid 1 untagged"))
    # to/from bng router frames
    # pexec(f"bridge vlan add dev blv vid 19")
    print(exec_subprocess(f"bridge vlan add dev {sw_bng_if.id} vid 5 pvid untagged"))
    # print(exec_subprocess(f"bridge vlan add dev {switch.id} vid 5 self"))
    # print(exec_subprocess(f"bridge vlan add dev sbv vid 5 pvid"))


# dhcp_client.add_route("DEFAULT", client_if, bng_sw_if.get_address())
# dhcp_server.add_route("DEFAULT", server_if)


# Start dhcclient in client
with dhcp_client:
    cmd = "dhclient c_sv"
    dhcp_worker = Process(target=exec_subprocess, args=(cmd,))
    dhcp_worker.start()

# Attach xdp program
cmd = (
    f"ip netns exec {bng_router.id} ./dhcp_user_xdp "
    f"-i {bng_sw_if.id} -d {server_if.address.get_addr(with_subnet=False)}"
)
pexec(cmd)

# with dhcp_server:
#     cmd = "dhcpd"
#     dhcp_worker = Process(target=exec_subprocess, args=(cmd,))
#     dhcp_worker.start()


shark_workers = [
    Process(
        target=exec_exp_commands,
        args=(
            f"ip netns exec {node.id} wireshark",
            PIPE,
            PIPE,
            400,
        ),
    )
    for node in [switch, switch, bng_router]
]

for wrker in shark_workers:
    wrker.start()


time.sleep(400)
