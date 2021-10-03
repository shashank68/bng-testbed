# SPDX-License-Identifier: GPL-2.0-only
# Copyright (c) 2021 NITK Surathkal


import time
from multiprocessing import Process

from nest import config
from nest.engine import exec_subprocess
from nest.topology import *


def pexec(command):
    """Run command as a subprocess"""
    print(exec_subprocess(command, output=True))


def run_cmd_bg(command):
    """Run command in background"""
    wrker = Process(target=exec_subprocess, args=(command,))
    wrker.start()


pexec("make")
config.set_value("assign_random_names", False)

dhcp_client = Node("cli")
bng_router = Node("bng")
dhcp_server = Node("ser")

bng_router.enable_ip_forwarding()

# dhcp_client -><-- bng_router --><-- dhcp_server

(client_if, bng_cl_if) = connect(dhcp_client, bng_router, "cl", "b_c")
(server_if, router_server_if) = connect(dhcp_server, bng_router, "s_r", "r_s")

bng_cl_if.set_address("10.0.0.1/24")
router_server_if.set_address("10.0.1.1/24")
server_if.set_address("10.0.1.2/24")

OUTER_VLAN = 15
INNER_VLAN = 25

VLAN_IF1 = f"cv.{OUTER_VLAN}"
VLAN_IF2 = f"{VLAN_IF1}.{INNER_VLAN}"

with dhcp_client:
    pexec(f"ip link add link {client_if.id} name {VLAN_IF1} type vlan id {OUTER_VLAN}")
    pexec(f"ip link add link {VLAN_IF1} name {VLAN_IF2} type vlan id {INNER_VLAN}")
    pexec(f"ip link set {VLAN_IF1} up")
    pexec(f"ip link set {VLAN_IF2} up")

# Start dhcclient in client
with dhcp_client:
    pexec(f"ethtool -K {client_if.id} txvlan off")

    cmd = f"dhclient --decline-wait-time 1 --dad-wait-time 1 {VLAN_IF2}"
    run_cmd_bg(cmd)

# Attach xdp program
with bng_router:
    cmd = f"./dhcp_user_xdp -i {bng_cl_if.id} -d {server_if.address.get_addr(with_subnet=False)}"
    pexec(cmd)

for node in [bng_router]:
    run_cmd_bg(f"ip netns e {node.id} wireshark")

time.sleep(500)
