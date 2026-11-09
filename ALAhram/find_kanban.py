import os

found = False
for base in ["/usr/lib/python3/dist-packages/odoo/addons", "/mnt/enterprise"]:
    for root, dirs, files in os.walk(base):
        for f in files:
            if f.endswith(".js") or f.endswith(".xml"):
                path = os.path.join(root, f)
                try:
                    with open(path, "r", errors="ignore") as fp:
                        content = fp.read()
                        if "CardArchParser" in content or "Missing 'card' template" in content:
                            print(f"Match found in: {path}")
                            found = True
                except Exception:
                    pass

# Also print an example kanban view from stock or sale
print("\n--- Example Kanban View from stock ---")
stock_kanban = "/usr/lib/python3/dist-packages/odoo/addons/stock/views/stock_picking_views.xml"
if os.path.exists(stock_kanban):
    with open(stock_kanban, "r") as fp:
        lines = fp.readlines()
        for i, line in enumerate(lines):
            if "<kanban" in line:
                print("".join(lines[i:i+40]))
                break

