/* SPDX-License-Identifier: GPL-2.0-or-later */

#include <linux/bpf.h>
#include <linux/in.h>
#include <bpf/bpf_helpers.h>
#include <xdp/parsing_helpers.h>
#include <xdp/context_helpers.h>
#include "dhcp-relay.h"

/*
 * This map is for storing the DHCP relay server
 * IP address configured by user. It is received
 * as an argument by user program.
*/
struct {
	__uint(type, BPF_MAP_TYPE_ARRAY);
	__type(key, __u32);
	__type(value, __u32);
	__uint(max_entries, 1);
} dhcp_server SEC(".maps");

#define static_offset                                                          \
	sizeof(struct ethhdr) + sizeof(struct iphdr) + sizeof(struct udphdr) + \
		offsetof(struct dhcp_packet, options)

static __u8 buf[static_offset + VLAN_MAX_DEPTH * sizeof(struct vlan_hdr)];

int xdp_dhcp_relay(struct xdp_md *ctx)
{
	void *data_end = (void *)(long)ctx->data_end;
	void *data = (void *)(long)ctx->data;
	struct collect_vlans vlans = { 0 };
	struct ethhdr *eth;
	struct iphdr *ip;
	struct iphdr oldip;
	struct udphdr *udp;
	__u32 *dhcp_srv;
	int rc = XDP_PASS;
	__u16 offset = static_offset;
	__u16 ip_offset = 0;
	int i = 0;

	/* These keep track of the next header type and iterator pointer */
	struct hdr_cursor nh;
	int ether_type;
	int h_proto = 0;
	int key = 0;
	int len = 0;

	if (data + 1 > data_end)
		return XDP_ABORTED;

	nh.pos = data;

	ether_type = parse_ethhdr(&nh, data_end, &eth); //NOW nh.pos is at IP header

	if (ether_type < 0) {
		rc = XDP_ABORTED;
		goto out;
	}
	if (ether_type != bpf_htons(ETH_P_IP))
		goto out;

	h_proto = parse_iphdr(&nh, data_end, &ip);

	/* only handle fixed-size IP header due to static copy */
	if (h_proto != IPPROTO_UDP || ip->ihl > 5) {
		goto out;
	}

	ip_offset = ((void *)ip - data) & 0x3fff;
	len = parse_udphdr(&nh, data_end, &udp);
	if (len < 0)
		goto out;	

	// if (udp->dest != bpf_htons(DEST_PORT))   ??NEED TO LOOK INTO
	// 	goto out;

	if (xdp_load_bytes(ctx, 0, buf, static_offset))
		goto out;
	
	nh.pos += offsetof(struct dhcp_packet, options);

	struct dhcp_option_82 *option82 = nh.pos;

	__u16 vlan[2]; 
	vlan[0] = option82->circuit_id.val;
	vlan[1] = option82->remote_id.val;

	if (bpf_xdp_adjust_head(ctx, 0 - 2*(int)sizeof(struct vlan_hdr))<0)
		return XDP_ABORTED;



	data_end = (void *)(long)ctx->data_end;
	data = (void *)(long)ctx->data;

	if (data + offset > data_end)
		return XDP_ABORTED;

	if (xdp_store_bytes(ctx, 0, buf, static_offset, 0))
		return XDP_ABORTED;

	struct vlan_hdr *vlan_h;

	vlh->h_vlan_TCI = 
	vlh->h_vlan_encapsulated_proto = //SET IT TO THE PREVIOUS protocol header
	vlan_h[] 
}