import tkinter as tk
from tkinter import messagebox
import json
from datetime import datetime
import random

class SaltBankGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Salt Bank - System Terminal")
        self.root.geometry("450x650")
        
        # Retro Terminal Aesthetic
        self.bg_color = "#050505"      # Deep black
        self.fg_color = "#00ff41"      # Terminal green
        self.btn_bg = "#1a1a1a"        # Dark gray for buttons
        self.font_style = ("Courier", 12)
        self.title_font = ("Courier", 18, "bold")
        
        self.root.configure(bg=self.bg_color)
        
        self.data_file = "bank_data.json"
        self.current_user = None
        
        self.load_data()
        self.build_login_screen()

    def load_data(self):
        """Loads user data from the JSON file."""
        try:
            with open(self.data_file, "r") as file:
                self.users = json.load(file)
        except FileNotFoundError:
            self.users = {}
            messagebox.showerror("System Error", "Database file (bank_data.json) not found! Starting with empty database.")

    def save_data(self):
        """Saves current state to the JSON file."""
        with open(self.data_file, "w") as file:
            json.dump(self.users, file, indent=4)

    def log_transaction(self, acc_no, trans_type, amount, details=""):
        """Records a transaction in the user's history."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {trans_type}: N{amount} {details}"
        self.users[acc_no]["history"].append(log_entry)
        self.save_data()

    def clear_screen(self):
        """Destroys all current widgets to switch screens."""
        for widget in self.root.winfo_children():
            widget.destroy()

    # ================= LOGIN SCREEN =================
    
    def build_login_screen(self):
        self.clear_screen()
        
        tk.Label(self.root, text="SALT BANK OS v1.0", font=self.title_font, bg=self.bg_color, fg=self.fg_color).pack(pady=40)

        tk.Label(self.root, text="ACCOUNT NUMBER:", font=self.font_style, bg=self.bg_color, fg=self.fg_color).pack(pady=5)
        self.acc_entry = tk.Entry(self.root, font=self.font_style, bg=self.bg_color, fg=self.fg_color, insertbackground=self.fg_color)
        self.acc_entry.pack(pady=5)

        tk.Label(self.root, text="PIN:", font=self.font_style, bg=self.bg_color, fg=self.fg_color).pack(pady=5)
        self.pin_entry = tk.Entry(self.root, font=self.font_style, show="*", bg=self.bg_color, fg=self.fg_color, insertbackground=self.fg_color)
        self.pin_entry.pack(pady=5)

        tk.Button(self.root, text="ACCESS ACCOUNT", font=self.font_style, bg=self.btn_bg, fg=self.fg_color, command=self.verify_login).pack(pady=15)
        tk.Button(self.root, text="CREATE NEW ACCOUNT", font=self.font_style, bg=self.btn_bg, fg=self.fg_color, command=self.build_create_account_screen).pack(pady=10)

    def verify_login(self):
        acc_no = self.acc_entry.get().strip()
        pin = self.pin_entry.get().strip()

        if acc_no in self.users:
            if str(self.users[acc_no]["pin"]) == pin:
                self.current_user = acc_no
                self.build_main_menu()
            else:
                messagebox.showerror("Access Denied", "Invalid PIN.")
        else:
            messagebox.showerror("Access Denied", "Account not found.")

    # ================= ACCOUNT CREATION =================

    def build_create_account_screen(self):
        self.clear_screen()
        
        tk.Label(self.root, text="NEW ACCOUNT SETUP", font=self.title_font, bg=self.bg_color, fg=self.fg_color).pack(pady=30)

        tk.Label(self.root, text="FULL NAME:", font=self.font_style, bg=self.bg_color, fg=self.fg_color).pack(pady=5)
        self.new_name_entry = tk.Entry(self.root, font=self.font_style, bg=self.bg_color, fg=self.fg_color, insertbackground=self.fg_color)
        self.new_name_entry.pack(pady=5)

        tk.Label(self.root, text="CREATE 4-DIGIT PIN:", font=self.font_style, bg=self.bg_color, fg=self.fg_color).pack(pady=5)
        self.new_pin_entry = tk.Entry(self.root, font=self.font_style, bg=self.bg_color, fg=self.fg_color, insertbackground=self.fg_color)
        self.new_pin_entry.pack(pady=5)

        tk.Button(self.root, text="GENERATE ACCOUNT", font=self.font_style, bg=self.btn_bg, fg=self.fg_color, command=self.process_create_account).pack(pady=25)
        tk.Button(self.root, text="BACK TO LOGIN", font=self.font_style, bg=self.btn_bg, fg=self.fg_color, command=self.build_login_screen).pack()

    def process_create_account(self):
        name = self.new_name_entry.get().strip()
        pin = self.new_pin_entry.get().strip()

        if not name or not pin:
            messagebox.showerror("Error", "All fields are required.")
            return

        if not pin.isdigit() or len(pin) != 4:
            messagebox.showerror("Error", "PIN must be exactly 4 digits.")
            return

        while True:
            acc_no = str(random.randint(10000000, 99999999))
            if acc_no not in self.users:
                break

        self.users[acc_no] = {
            "name": name,
            "pin": int(pin),
            "balance": 0,
            "history": []
        }
        
        self.save_data()
        self.log_transaction(acc_no, "SYSTEM", 0, "Account Created")

        messagebox.showinfo("Success", f"Account Successfully Created!\n\nName: {name}\nAccount Number: {acc_no}\n\nPlease write this down to log in.")
        self.build_login_screen()

    # ================= MAIN MENU =================

    def build_main_menu(self):
        self.clear_screen()
        user_name = self.users[self.current_user]["name"]
        
        tk.Label(self.root, text=f"WELCOME, {user_name.upper()}", font=self.title_font, bg=self.bg_color, fg=self.fg_color).pack(pady=20)

        buttons = [
            ("CHECK BALANCE", self.check_balance),
            ("DEPOSIT", self.build_deposit_screen),
            ("WITHDRAW", self.build_withdraw_screen),
            ("TRANSFER", self.build_transfer_screen),
            ("TRANSACTION HISTORY", self.build_history_screen),
            ("LOGOUT", self.logout)
        ]

        for text, command in buttons:
            tk.Button(self.root, text=text, font=self.font_style, bg=self.btn_bg, fg=self.fg_color, width=25, command=command).pack(pady=8)

    def logout(self):
        self.current_user = None
        self.build_login_screen()

    # ================= TRANSACTIONS =================

    def check_balance(self):
        balance = self.users[self.current_user]["balance"]
        messagebox.showinfo("Balance", f"Current Balance: N{balance}")

    def build_deposit_screen(self):
        self.clear_screen()
        tk.Label(self.root, text="DEPOSIT FUNDS", font=self.title_font, bg=self.bg_color, fg=self.fg_color).pack(pady=30)
        
        tk.Label(self.root, text="ENTER AMOUNT:", font=self.font_style, bg=self.bg_color, fg=self.fg_color).pack()
        self.amount_entry = tk.Entry(self.root, font=self.font_style, bg=self.bg_color, fg=self.fg_color, insertbackground=self.fg_color)
        self.amount_entry.pack(pady=10)

        tk.Button(self.root, text="CONFIRM DEPOSIT", font=self.font_style, bg=self.btn_bg, fg=self.fg_color, command=self.process_deposit).pack(pady=20)
        tk.Button(self.root, text="BACK", font=self.font_style, bg=self.btn_bg, fg=self.fg_color, command=self.build_main_menu).pack()

    def process_deposit(self):
        try:
            amount = int(self.amount_entry.get())
            if amount <= 0:
                raise ValueError
            self.users[self.current_user]["balance"] += amount
            self.log_transaction(self.current_user, "DEPOSIT", amount)
            messagebox.showinfo("Success", f"Deposited N{amount} successfully.")
            self.build_main_menu()
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid positive number.")

    def build_withdraw_screen(self):
        self.clear_screen()
        tk.Label(self.root, text="WITHDRAW FUNDS", font=self.title_font, bg=self.bg_color, fg=self.fg_color).pack(pady=30)
        
        tk.Label(self.root, text="ENTER AMOUNT:", font=self.font_style, bg=self.bg_color, fg=self.fg_color).pack()
        self.amount_entry = tk.Entry(self.root, font=self.font_style, bg=self.bg_color, fg=self.fg_color, insertbackground=self.fg_color)
        self.amount_entry.pack(pady=10)

        tk.Button(self.root, text="CONFIRM WITHDRAWAL", font=self.font_style, bg=self.btn_bg, fg=self.fg_color, command=self.process_withdraw).pack(pady=20)
        tk.Button(self.root, text="BACK", font=self.font_style, bg=self.btn_bg, fg=self.fg_color, command=self.build_main_menu).pack()

    def process_withdraw(self):
        try:
            amount = int(self.amount_entry.get())
            current_balance = self.users[self.current_user]["balance"]
            
            if amount <= 0:
                messagebox.showerror("Error", "Amount must be greater than zero.")
            elif amount > current_balance:
                messagebox.showerror("Error", "Insufficient funds.")
            else:
                self.users[self.current_user]["balance"] -= amount
                self.log_transaction(self.current_user, "WITHDRAWAL", amount)
                messagebox.showinfo("Success", f"Withdrew N{amount} successfully.")
                self.build_main_menu()
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number.")

    def build_transfer_screen(self):
        self.clear_screen()
        tk.Label(self.root, text="TRANSFER FUNDS", font=self.title_font, bg=self.bg_color, fg=self.fg_color).pack(pady=20)
        
        tk.Label(self.root, text="TARGET ACCOUNT NO:", font=self.font_style, bg=self.bg_color, fg=self.fg_color).pack()
        self.target_entry = tk.Entry(self.root, font=self.font_style, bg=self.bg_color, fg=self.fg_color, insertbackground=self.fg_color)
        self.target_entry.pack(pady=5)

        tk.Label(self.root, text="ENTER AMOUNT:", font=self.font_style, bg=self.bg_color, fg=self.fg_color).pack()
        self.amount_entry = tk.Entry(self.root, font=self.font_style, bg=self.bg_color, fg=self.fg_color, insertbackground=self.fg_color)
        self.amount_entry.pack(pady=5)

        tk.Button(self.root, text="CONFIRM TRANSFER", font=self.font_style, bg=self.btn_bg, fg=self.fg_color, command=self.process_transfer).pack(pady=20)
        tk.Button(self.root, text="BACK", font=self.font_style, bg=self.btn_bg, fg=self.fg_color, command=self.build_main_menu).pack()

    def process_transfer(self):
        target_acc = self.target_entry.get().strip()
        
        if target_acc not in self.users:
            messagebox.showerror("Error", "Target account does not exist.")
            return
        if target_acc == self.current_user:
            messagebox.showerror("Error", "Cannot transfer to yourself.")
            return

        try:
            amount = int(self.amount_entry.get())
            current_balance = self.users[self.current_user]["balance"]

            if amount <= 0:
                messagebox.showerror("Error", "Amount must be greater than zero.")
            elif amount > current_balance:
                messagebox.showerror("Error", "Insufficient funds.")
            else:
                # Deduct from sender
                self.users[self.current_user]["balance"] -= amount
                self.log_transaction(self.current_user, "TRANSFER OUT", amount, f"to {target_acc}")
                
                # Add to receiver
                self.users[target_acc]["balance"] += amount
                self.log_transaction(target_acc, "TRANSFER IN", amount, f"from {self.current_user}")
                
                messagebox.showinfo("Success", f"Transferred N{amount} to {target_acc}.")
                self.build_main_menu()
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid number.")

    def build_history_screen(self):
        self.clear_screen()
        tk.Label(self.root, text="TRANSACTION HISTORY", font=self.title_font, bg=self.bg_color, fg=self.fg_color).pack(pady=10)
        
        history_box = tk.Text(self.root, height=15, width=45, bg=self.btn_bg, fg=self.fg_color, font=("Courier", 10))
        history_box.pack(pady=10)
        
        history_list = self.users[self.current_user].get("history", [])
        if not history_list:
            history_box.insert(tk.END, "No transactions found.")
        else:
            for item in reversed(history_list):
                history_box.insert(tk.END, item + "\n")
                
        history_box.config(state=tk.DISABLED)

        tk.Button(self.root, text="BACK", font=self.font_style, bg=self.btn_bg, fg=self.fg_color, command=self.build_main_menu).pack(pady=10)

if __name__ == "__main__":
    root = tk.Tk()
    app = SaltBankGUI(root)
    root.mainloop()