import pysoem

IFACE = "enp47s0"

m = pysoem.Master()
m.open(IFACE)

slave_count = m.config_init()

if slave_count > 0:
    print(f"Found {slave_count} slaves")
    for i, s in enumerate(m.slaves):
        print(
            f"Slave {i}: "
            f"man=0x{s.man:08x}, "
            f"id=0x{s.id:08x}, "
            f"rev=0x{s.rev:08x}, "
            f"name='{s.name}'"
        )
else:
    print("No slaves found")

m.close()
