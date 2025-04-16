import json
import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# -------------------------------
# Utility Functions and Data I/O
# -------------------------------

RULES_FILE = "rules.json"


def load_rules(json_file):
    """Load flight rules from a JSON file."""
    try:
        with open(json_file, "r") as f:
            return json.load(f)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to load rules: {e}")
        return []


def save_rules(rules, json_file):
    """Save flight rules to a JSON file."""
    try:
        with open(json_file, "w") as f:
            json.dump(rules, f, indent=4)
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save rules: {e}")


def flight_available(rule):
    """Check if the flight is still available based on today's departure time."""
    now = datetime.datetime.now()
    try:
        dep = datetime.datetime.strptime(rule["departure_time"], "%H:%M").replace(
            year=now.year, month=now.month, day=now.day
        )
        return now < dep
    except Exception:
        return False

# -------------------------------
# Inference Engine
# -------------------------------

def find_flight(rules, cargo_weight, destination):
    """Choose the best flight based on minimal surplus capacity and lower carbon footprint."""
    candidates = []
    for rule in rules:
        if (
            rule["destination"].lower() == destination.lower()
            and cargo_weight <= rule["max_weight"]
            and flight_available(rule)
        ):
            surplus = rule["max_weight"] - cargo_weight
            candidates.append((rule, surplus))
    if not candidates:
        return None, "No available flight for the given cargo and destination."
    candidates.sort(key=lambda x: (x[1], x[0]["carbon_footprint"]))
    best, surplus = candidates[0]
    explanation = (
        f"Flight {best['flight']} selected: surplus capacity {surplus} kg, "
        f"carbon footprint {best['carbon_footprint']}"
    )
    return best, explanation

# -------------------------------
# GUI Setup and Callbacks
# -------------------------------

class CargoExpertGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Airline Cargo Expert System")
        self.root.geometry("800x650")
        self.root.minsize(700, 600)

        # Load data
        self.rules = load_rules(RULES_FILE)
        self.recommended_flight = None
        self.dark_mode = False

        # Configure grid for responsiveness
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        # Setup styles
        self._setup_styles()

        # Build UI
        self._create_menu()
        self._create_header()
        self._create_input_frame()
        self._create_result_frame()
        self._create_button_frame()
        self._create_status_bar()

    def _setup_styles(self):
        style = ttk.Style(self.root)
        style.theme_use('clam')
        # Frame background
        style.configure('TFrame', background='#f7f9fc')
        # Header label
        style.configure('Header.TLabel', background='#34495e', foreground='white', font=('Arial', 16, 'bold'))
        # Regular labels
        style.configure('TLabel', background='#f7f9fc', font=('Arial', 11))
        # Entry and Combobox padding
        style.configure('TEntry', padding=5)
        style.configure('TCombobox', padding=5)
        # Buttons
        style.configure('Accent.TButton', background='#2980b9', foreground='white', font=('Arial', 11, 'bold'), padding=6)
        style.map('Accent.TButton', background=[('active', '#1f6391')])
        style.configure('Success.TButton', background='#27ae60', foreground='white', font=('Arial', 11, 'bold'), padding=6)
        style.map('Success.TButton', background=[('active', '#1e8449')])
        style.configure('Danger.TButton', background='#c0392b', foreground='white', font=('Arial', 11, 'bold'), padding=6)
        style.map('Danger.TButton', background=[('active', '#922b21')])

    def _create_menu(self):
        menubar = tk.Menu(self.root)
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Toggle Theme", command=self.on_toggle_theme)
        menubar.add_cascade(label="View", menu=view_menu)

        admin_menu = tk.Menu(menubar, tearoff=0)
        admin_menu.add_command(label="Add Flight Rule", command=self.on_admin_mode)
        menubar.add_cascade(label="Admin", menu=admin_menu)

        self.root.config(menu=menubar)

    def _create_header(self):
        header = ttk.Frame(self.root, style='TFrame')
        header.grid(row=0, column=0, sticky='ew')
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text="Airline Scheduling & Cargo Expert", style='Header.TLabel').grid(
            row=0, column=0, sticky='ew', pady=10, padx=10
        )

    def _create_input_frame(self):
        frame = ttk.Frame(self.root, style='TFrame', padding=20)
        frame.grid(row=1, column=0, sticky='nsew', padx=10, pady=10)
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text="Cargo Weight (kg):").grid(row=0, column=0, sticky='w', pady=8)
        self.weight_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.weight_var).grid(row=0, column=1, sticky='ew', pady=8)

        ttk.Label(frame, text="Destination:").grid(row=1, column=0, sticky='w', pady=8)
        self.destination_var = tk.StringVar()
        dests = sorted({r['destination'] for r in self.rules}) or ["None"]
        self.destination_var.set(dests[0])
        combo = ttk.Combobox(frame, textvariable=self.destination_var, values=dests, state='readonly')
        combo.grid(row=1, column=1, sticky='ew', pady=8)
        combo.bind('<<ComboboxSelected>>', lambda e: self.update_cargo_limits())

        self.cargo_limit_label = ttk.Label(frame, text="Allowed weight: --")
        self.cargo_limit_label.grid(row=2, column=0, columnspan=2, sticky='w', pady=8)
        self.update_cargo_limits()

    def _create_result_frame(self):
        frame = ttk.Frame(self.root, style='TFrame', padding=(20,10))
        frame.grid(row=2, column=0, sticky='ew', padx=10)
        frame.columnconfigure(0, weight=1)

        self.result_label = ttk.Label(frame, text="Recommended Flight:", font=('Arial', 12, 'bold'))
        self.result_label.grid(row=0, column=0, sticky='w')
        self.explanation_label = ttk.Label(frame, text="", wraplength=760)
        self.explanation_label.grid(row=1, column=0, sticky='w', pady=5)

    def _create_button_frame(self):
        frame = ttk.Frame(self.root, style='TFrame', padding=20)
        frame.grid(row=3, column=0, sticky='ew', padx=10, pady=10)
        for i in range(3): frame.columnconfigure(i, weight=1)

        ttk.Button(frame, text="Find Flight", style='Accent.TButton', command=self.on_find_flight).grid(row=0, column=0, padx=5, pady=5, sticky='ew')
        ttk.Button(frame, text="Reset", style='Danger.TButton', command=self.on_reset).grid(row=0, column=1, padx=5, pady=5, sticky='ew')
        ttk.Button(frame, text="Show All Flights", style='Accent.TButton', command=self.on_show_all_flights).grid(row=0, column=2, padx=5, pady=5, sticky='ew')

        ttk.Button(frame, text="Show Chart", style='Accent.TButton', command=self.on_show_chart).grid(row=1, column=0, padx=5, pady=5, sticky='ew')
        ttk.Button(frame, text="Book Flight", style='Success.TButton', command=self.on_book_flight).grid(row=1, column=1, padx=5, pady=5, sticky='ew')
        ttk.Button(frame, text="Admin Mode", style='Success.TButton', command=self.on_admin_mode).grid(row=1, column=2, padx=5, pady=5, sticky='ew')

    def _create_status_bar(self):
        self.status_var = tk.StringVar(value="Ready")
        bar = ttk.Label(self.root, textvariable=self.status_var, relief='sunken', anchor='w')
        bar.grid(row=4, column=0, sticky='ew')

    # Callback methods (logic unchanged)
    def update_cargo_limits(self):
        city = self.destination_var.get()
        city_rules = [r for r in self.rules if r['destination'].lower() == city.lower()]
        if city_rules:
            mins = min(r['max_weight'] for r in city_rules)
            maxs = max(r['max_weight'] for r in city_rules)
            self.cargo_limit_label.config(text=f"Allowed weight: {mins}–{maxs} kg")
        else:
            self.cargo_limit_label.config(text="No flights for selected city.")

    def on_find_flight(self):
        try:
            w = float(self.weight_var.get())
        except ValueError:
            messagebox.showerror("Input Error", "Enter a valid number for weight.")
            return
        best, exp = find_flight(self.rules, w, self.destination_var.get())
        if best:
            self.recommended_flight = best
            self.result_label.config(text=f"Recommended Flight: {best['flight']}")
            self.explanation_label.config(text=exp)
            self.status_var.set("Flight recommended.")
        else:
            self.result_label.config(text=exp)
            self.explanation_label.config(text="")
            self.status_var.set("No match.")

    def on_reset(self):
        self.weight_var.set("")
        self.result_label.config(text="Recommended Flight:")
        self.explanation_label.config(text="")
        self.status_var.set("Ready")

    def on_show_all_flights(self):
        try:
            w = float(self.weight_var.get())
        except ValueError:
            messagebox.showerror("Input Error", "Enter a valid number for weight.")
            return
        dest = self.destination_var.get()
        matching = []
        for r in self.rules:
            if r['destination'].lower() == dest.lower() and w <= r['max_weight'] and flight_available(r):
                matching.append((r, r['max_weight'] - w))
        if not matching:
            messagebox.showinfo("No Flights", "No available flights match the criteria.")
            return
        win = tk.Toplevel(self.root)
        win.title("Available Flights")
        tree = ttk.Treeview(win, columns=("Flight","Max","Surplus","Airport","Dep","Carbon"), show='headings')
        for col,txt in zip(tree['columns'], ["Flight","Max Weight","Surplus","Airport","Departure","Carbon"]):
            tree.heading(col, text=txt)
        tree.pack(fill='both', expand=True)
        for r,s in matching:
            tree.insert('', 'end', values=(r['flight'], r['max_weight'], s, r.get('airport_code',''), r.get('departure_time',''), r.get('carbon_footprint','')))
        self.status_var.set("Displayed all flights.")

    def on_show_chart(self):
        try:
            w = float(self.weight_var.get())
        except ValueError:
            messagebox.showerror("Input Error", "Enter a valid number for weight.")
            return
        dest = self.destination_var.get()
        flights, surpluses = [], []
        for r in self.rules:
            if r['destination'].lower() == dest.lower() and w <= r['max_weight'] and flight_available(r):
                flights.append(r['flight'])
                surpluses.append(r['max_weight'] - w)
        if not flights:
            messagebox.showinfo("No Data", "No available flights to chart.")
            return
        win = tk.Toplevel(self.root)
        win.title("Surplus Capacity Chart")
        fig, ax = plt.subplots(figsize=(6,4))
        ax.bar(flights, surpluses)
        ax.set_xlabel("Flight")
        ax.set_ylabel("Surplus Capacity (kg)")
        ax.set_title("Surplus Capacity for Matching Flights")
        canvas = FigureCanvasTkAgg(fig, master=win)
        canvas.draw()
        canvas.get_tk_widget().pack(fill='both', expand=True)
        self.status_var.set("Chart displayed.")

    def on_book_flight(self):
        if not self.recommended_flight:
            messagebox.showinfo("No Flight", "No flight recommended to book.")
            return
        win = tk.Toplevel(self.root)
        win.title("Boarding Pass")
        frm = ttk.Frame(win, padding=20)
        frm.pack(fill='both', expand=True)
        ttk.Label(frm, text="BOARDING PASS", font=('Arial',14,'bold')).pack(pady=10)
        details = (
            f"Flight: {self.recommended_flight['flight']}\n"
            f"Destination: {self.recommended_flight['destination']}\n"
            f"Airport Code: {self.recommended_flight.get('airport_code','')}\n"
            f"Departure Time: {self.recommended_flight.get('departure_time','')}\n"
            f"Max Cargo Capacity: {self.recommended_flight['max_weight']} kg\n"
            f"Carbon Footprint: {self.recommended_flight.get('carbon_footprint','')}"
        )
        ttk.Label(frm, text=details, justify='left').pack(pady=5)
        ttk.Button(frm, text="Close", style='Danger.TButton', command=win.destroy).pack(pady=10)
        self.status_var.set("Boarding pass shown.")

    def on_admin_mode(self):
        win = tk.Toplevel(self.root)
        win.title("Admin Mode - Add Flight Rule")
        win.geometry("400x450")
        frm = ttk.Frame(win, padding=20)
        frm.pack(fill='both', expand=True)
        fields = ["Flight","Destination","Max Weight","Airport Code","Departure Time (HH:MM)","Carbon Footprint"]
        entries = {}
        for i, fld in enumerate(fields):
            ttk.Label(frm, text=fld).grid(row=i, column=0, sticky='w', pady=5)
            ent = ttk.Entry(frm)
            ent.grid(row=i, column=1, pady=5)
            entries[fld] = ent
        def add():
            try:
                new = {
                    'flight': entries['Flight'].get(),
                    'destination': entries['Destination'].get(),
                    'max_weight': float(entries['Max Weight'].get()),
                    'airport_code': entries['Airport Code'].get(),
                    'departure_time': entries['Departure Time (HH:MM)'].get(),
                    'carbon_footprint': float(entries['Carbon Footprint'].get())
                }
            except ValueError:
                messagebox.showerror("Input Error","Check numeric fields.")
                return
            self.rules.append(new)
            save_rules(self.rules, RULES_FILE)
            messagebox.showinfo("Success", f"Flight {new['flight']} added.")
            win.destroy()
            self.update_cargo_limits()
        ttk.Button(frm, text="Add Flight", style='Success.TButton', command=add).grid(row=len(fields), column=0, columnspan=2, pady=15)
        self.status_var.set("In Admin mode.")

    def on_toggle_theme(self):
        bg = '#2c3e50' if not self.dark_mode else '#f7f9fc'
        fg = 'white' if not self.dark_mode else 'black'
        self.root.configure(bg=bg)
        for child in self.root.winfo_children():
            try:
                child.configure(style='TFrame')
            except:
                pass
        self.dark_mode = not self.dark_mode
        self.status_var.set("Theme toggled.")

if __name__ == '__main__':
    root = tk.Tk()
    app = CargoExpertGUI(root)
    root.mainloop()
