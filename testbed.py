# SPDX-License-Identifier: GPL-2.0-only
# Copyright (c) 2021 NITK Surathkal

import time
from multiprocessing import Process
from subprocess import PIPE

from nest import config
from nest.engine import exec_exp_commands, exec_subprocess
from nest.topology import *

config.set_value("assign_random_names", False)
##############################
# Topology
#
# dhcp_client -><-- bng_router --><-- dhcp_server
##############################

dhcp_client = Node("cli")
bng_router = Node("bng")
dhcp_server = Node("ser")
print(exec_subprocess(f"make", output=True))

# Enabling IP forwarding for the routers
bng_router.enable_ip_forwarding()


(client_if, bng_cl_if) = connect(dhcp_client, bng_router, "cl", "b_c")
(server_if, router_server_if) = connect(dhcp_server, bng_router, "s_r", "r_s")
bng_cl_if.set_address("10.0.0.1/24")

with dhcp_client:
    print(exec_subprocess(f"ip link add link {client_if.id} name clv type vlan id 30"))
    print(exec_subprocess(f"ip link set clv up"))
    print(exec_subprocess(f"ip link add link clv name clv.20 type vlan id 20 "))
    print(exec_subprocess(f"ip link set clv.20 up"))



client_if.set_address("10.0.0.2/24")
router_server_if.set_address("10.0.1.1/24")
server_if.set_address("10.0.1.2/24")


# Start dhcclient in client
with dhcp_client:
    cmd = "dhclient -d --decline-wait-time 1 clv.20"
    dhcp_worker = Process(target=exec_subprocess, args=(cmd,))
    dhcp_worker.start()

# time.sleep(1000)
# with switch:
#     print(exec_subprocess(f"ip link add link {sw_bng_if.id} name sbv type vlan id 5"))
#     print(exec_subprocess(f"ip link set dev {switch.id} type bridge vlan_filtering 1"))
#     print(exec_subprocess(f"bridge vlan del dev {sw_cl_if.id} vid 1"))
#     print(exec_subprocess(f"bridge vlan del dev {sw_bng_if.id} vid 1"))
#     print(exec_subprocess(f"bridge vlan del dev {switch.id} vid 1 self"))
# #     # to/from client frames

#     print(exec_subprocess(f"bridge vlan add dev {sw_cl_if.id} vid 19 pvid untagged"))
# #     # print(exec_subprocess(f"bridge vlan add dev {switch.id} vid 20 self"))
# #     # print(exec_subprocess(f"bridge vlan add dev {sw_cl_if.id} vid 1 untagged"))
# #     # to/from bng router frames
#     print(exec_subprocess(f"bridge vlan add dev {sw_bng_if.id} vid 19"))
# #     # print(exec_subprocess(f"bridge vlan add dev {sw_bng_if.id} vid 5 pvid"))
# #     # print(exec_subprocess(f"bridge vlan add dev {switch.id} vid 5 self"))
# #     # print(exec_subprocess(f"bridge vlan add dev sbv vid 5 pvid"))


# dhcp_client.add_route("DEFAULT", client_if)
dhcp_server.add_route("DEFAULT", server_if)

# with bng_router:
# print(exec_subprocess())

# Attach xdp program
cmd = (
    f"ip netns exec {bng_router.id} ./dhcp_user_xdp "
    f"-i {bng_cl_if.id} -d {server_if.address.get_addr(with_subnet=False)}"
)
print(exec_subprocess(cmd, output=True))

# with dhcp_server:
#     cmd = "dhcpd"
#     dhcp_worker = Process(target=exec_subprocess, args=(cmd,))
#     dhcp_worker.start()

xdp_dump_workers = [
    Process(
        target=exec_exp_commands,
        args=(
            f"ip netns exec {node.id} ./xdp-tools/xdp-dump/xdpdump -i b_c -w b_c.pcap",
            PIPE,
            PIPE,
            400,
        ),
    )
    for node in [bng_router]
]

for wrker in xdp_dump_workers:
    wrker.start()

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
    for node in [bng_router]
]

for wrker in shark_workers:
    wrker.start()


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
    for node in [dhcp_client]
]

for wrker in shark_workers:
    wrker.start()


time.sleep(400)
