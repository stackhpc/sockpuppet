flow_definitions = [
    # run this on the compute nodes
    {
        "class": "ceph",
        "flows": [
            {
                "flow": "ceph-mon",
                "dst_port": 6789,
            },
            {
                "flow": "ceph-mds",
                "dst_port": 6800,
                "dst": { "10.42.0.4", "10.10.120.2", "192.168.246.128" }
            },
            # By default, Ceph OSD Daemons bind to the first available ports
            # on a Ceph Node beginning at port 6800
            {
                "flow": "ceph-osd-outbound",
                "dst_port": "6800:7300",
            },
            {
                "flow": "ceph-osd-inbound",
                "src_port": "6800:7300"
            },
        ]
    },
]