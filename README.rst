==========
sockpuppet
==========


A socket level TCP metrics exporter for prometheus. 


Description
===========

Exports the following metrics:

- sockpuppet_tcp_rtt
- sockpuppet_tcp_rcv_rtt
- sockpuppet_tcp_bytes_acked
- sockpuppet_tcp_bytes_received
- sockpuppet_tcp_notsent_bytes
- sockpuppet_tcp_tmem_bytes
- sockpuppet_tcp_wmem_bytes

You must specify the flows you want to collect in a config file, see:
``config/config_example.py`` for an example.
