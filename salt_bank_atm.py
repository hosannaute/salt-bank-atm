import json
import random
from datetime import datetime

#SALT BANK ATM SIMULATOR

DATA_FILE = "bank_data.json"



def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("\n  WARNING: Database file not found. Starting with empty database.")
        return {}

def save_data(users):
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

def log_transaction(users, acc_no, trans_type, amount, details=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{timestamp}] {trans_type}: N{amount} {details}".strip()
    users[acc_no]["history"].append(entry)
    save_data(users)


# DISPLAY MESSAGE
def print_line(char="=", length=50):
    print(char * length)

def print_header(title):
    print()
    print_line()
    print(f"  {title}")
    print_line()

def prompt(label):
    return input(f"  {label}: ").strip()

def info(msg):
    print(f"\n  [OK] {msg}")

def error(msg):
    print(f"\n  [ERROR] {msg}")

def pause():
    input("\n  Press ENTER to continue...")


# LOGIN

def login_screen(users):
    print_header("SALT BANK OS v1.0")
    print("""
  [1] ACCESS ACCOUNT
  [2] CREATE NEW ACCOUNT
  [3] EXIT
    """)
    choice = input("SELECT OPTION")

    if choice == "1":
        return verify_login(users)
    elif choice == "2":
        create_account(users)
        return None
    elif choice == "3":
        print("\n  Goodbye.\n")
        exit()
    else:
        error("Invalid option.")
        return None

def verify_login(users):
    print_header("ACCESS ACCOUNT")
    acc_no = input("ACCOUNT NUMBER")
    pin    = input("PIN")

    if acc_no in users:
        if str(users[acc_no]["pin"]) == pin:
            return acc_no
        else:
            error("Invalid PIN.")
    else:
        error("Account not found.")
    pause()
    return None


# CREATE ACCOUNT

def create_account(users):
    print_header("NEW ACCOUNT SETUP")
    name = input("FULL NAME")
    pin  = input("CREATE 4-DIGIT PIN")

    if not name or not pin:
        error("All fields are required.")
        pause()
        return

    if not pin.isdigit() or len(pin) != 4:
        error("PIN must be exactly 4 digits.")
        pause()
        return

    while True:
        acc_no = str(random.randint(10000000, 99999999))
        if acc_no not in users:
            break

    users[acc_no] = {
        "name": name,
        "pin": int(pin),
        "balance": 0,
        "history": []
    }

    log_transaction(users, acc_no, "SYSTEM", 0, "Account Created")

    print_line()
    print(f"\n  Account Successfully Created!")
    print(f"\n  Name           : {name}")
    print(f"  Account Number : {acc_no}")
    print(f"\n  Please write this down to log in.")
    print_line()
    pause()


# MAIN MENU

def main_menu(users, acc_no):
    name = users[acc_no]["name"]
    print_header(f"WELCOME, {name.upper()}")
    print("""
  [1] CHECK BALANCE
  [2] DEPOSIT
  [3] WITHDRAW
  [4] TRANSFER
  [5] TRANSACTION HISTORY
  [6] LOGOUT
    """)
    return input("SELECT OPTION")


# TRANSACTIONS

def check_balance(users, acc_no):
    balance = users[acc_no]["balance"]
    print_header("ACCOUNT BALANCE")
    print(f"\n  Current Balance: N{balance}")
    pause()

def deposit(users, acc_no):
    print_header("DEPOSIT FUNDS")
    raw = input("ENTER AMOUNT")
    try:
        amount = int(raw)
        if amount <= 0:
            raise ValueError
        users[acc_no]["balance"] += amount
        log_transaction(users, acc_no, "DEPOSIT", amount)
        info(f"Deposited N{amount} successfully.")
    except ValueError:
        error("Please enter a valid positive number.")
    pause()

def withdraw(users, acc_no):
    print_header("WITHDRAW FUNDS")
    raw = input("ENTER AMOUNT")
    try:
        amount = int(raw)
        balance = users[acc_no]["balance"]
        if amount <= 0:
            error("Amount must be greater than zero.")
        elif amount > balance:
            error("Insufficient funds.")
        else:
            users[acc_no]["balance"] -= amount
            log_transaction(users, acc_no, "WITHDRAWAL", amount)
            info(f"Withdrew N{amount} successfully.")
    except ValueError:
        error("Please enter a valid number.")
    pause()

def transfer(users, acc_no):
    print_header("TRANSFER FUNDS")
    target = input("TARGET ACCOUNT NUMBER")

    if target not in users:
        error("Target account does not exist.")
        pause()
        return
    if target == acc_no:
        error("Cannot transfer to yourself.")
        pause()
        return

    raw = prompt("ENTER AMOUNT")
    try:
        amount = int(raw)
        balance = users[acc_no]["balance"]
        if amount <= 0:
            error("Amount must be greater than zero.")
        elif amount > balance:
            error("Insufficient funds.")
        else:
            users[acc_no]["balance"] -= amount
            log_transaction(users, acc_no, "TRANSFER OUT", amount, f"to {target}")

            users[target]["balance"] += amount
            log_transaction(users, target, "TRANSFER IN", amount, f"from {acc_no}")

            info(f"Transferred N{amount} to account {target}.")
    except ValueError:
        error("Please enter a valid number.")
    pause()

def show_history(users, acc_no):
    print_header("TRANSACTION HISTORY")
    history = users[acc_no].get("history", [])
    if not history:
        print("\n  No transactions found.")
    else:
        print()
        for item in reversed(history):
            print(f"  {item}")
    pause()


# MAIN LOOP
def main():
    users = load_data()
    current_user = None

    while True:
        if current_user is None:
            current_user = login_screen(users)
            continue

        choice = main_menu(users, current_user)

        if choice == "1":
            check_balance(users, current_user)
        elif choice == "2":
            deposit(users, current_user)
        elif choice == "3":
            withdraw(users, current_user)
        elif choice == "4":
            transfer(users, current_user)
        elif choice == "5":
            show_history(users, current_user)
        elif choice == "6":
            info("Logged out.")
            current_user = None
        else:
            error("Invalid option.")
            pause()


if __name__ == "__main__":
    main()
