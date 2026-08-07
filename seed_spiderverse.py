"""
seed_spiderverse.py
--------------------
One-off script to load the "Spider-Verse Hackathon" problem sets into Mongo,
wired up for the new HackerRank-style Code & Run editor.

ALL 6 PROBLEMS ARE AUTO-GRADED, SANDBOX-RUNNABLE "code" PROBLEMS:
The 3 sorting problems (Kth Strongest Henchman, Count Inversions, Sort the
Multiverse Signals) are pure stdin -> stdout transforms, seeded with 9 test
cases each (1 sample + 8 hidden), matching the constraints in the question
doc (large N, duplicates, negatives, etc.)

The 3 billing/simulation problems (Spider-Gear Shop, Pete's Pizza-Time,
Spider-Verse Exhibit Ticket Booking) were originally free-form / manual-
review ("file") problems, since the brief describes them as interactive
programs that print prompts via input("..."). To make them auto-gradable
in the sandbox like the sorting problems, they've been re-specified as
STRICT stdin -> stdout problems: the solution reads every value silently
(no prompt text of its own) and prints only the exact bill/confirmation
format described in the problem statement and starter code. Each has 4
test cases (1 sample + 3 hidden) covering the discount-tier edge cases.

Run with the same MONGO_URI your app uses, e.g.:
    MONGO_URI="mongodb+srv://...&appName=Cluster0" python3 seed_spiderverse.py
"""

import os
import random
from pymongo import MongoClient

MONGO_URI = os.environ.get("MONGO_URI")
if not MONGO_URI:
    raise SystemExit(
        "MONGO_URI environment variable is not set. Refusing to run with a "
        "hardcoded fallback credential - set MONGO_URI to your (rotated) "
        "connection string before running this script, e.g.:\n"
        '  $env:MONGO_URI = "mongodb+srv://user:pass@cluster0.xxxx.mongodb.net/DevHost?retryWrites=true&w=majority"\n'
        "  python seed_spiderverse.py"
    )

EVENT_TITLE = "Spider-Verse Hackathon"


def make_test(input_text, output_text, is_sample, order):
    return {"input": input_text, "output": output_text, "is_sample": is_sample, "order": order}


# ---------------------------------------------------------------- #
# SORT 1 - Kth strongest henchman (kth largest element, 1-indexed)
# ---------------------------------------------------------------- #

def kth_largest_case(n, k, values):
    inp = f"{n} {k}\n{' '.join(map(str, values))}\n"
    out = str(sorted(values, reverse=True)[k - 1])
    return inp, out


def build_sort1_tests():
    tests = []
    rng = random.Random(1)

    # Sample from the question doc
    inp, out = kth_largest_case(6, 3, [7, 10, 4, 3, 20, 15])
    tests.append(make_test(inp, out, True, 1))

    # single element
    inp, out = kth_largest_case(1, 1, [42])
    tests.append(make_test(inp, out, False, 2))

    # all equal
    vals = [7] * 500
    inp, out = kth_largest_case(500, 250, vals)
    tests.append(make_test(inp, out, False, 3))

    # k = 1 (max) and k = n (min)
    vals = rng.sample(range(0, 10**6), 1000)
    inp, out = kth_largest_case(1000, 1, vals)
    tests.append(make_test(inp, out, False, 4))
    inp, out = kth_largest_case(1000, 1000, vals)
    tests.append(make_test(inp, out, False, 5))

    # large values near 1e9
    vals = [rng.randint(999_000_000, 10**9) for _ in range(2000)]
    inp, out = kth_largest_case(2000, 777, vals)
    tests.append(make_test(inp, out, False, 6))

    # zeros included
    vals = [0] * 100 + list(range(1, 401))
    rng.shuffle(vals)
    inp, out = kth_largest_case(500, 450, vals)
    tests.append(make_test(inp, out, False, 7))

    # N = 100000 random
    vals = [rng.randint(0, 10**9) for _ in range(100_000)]
    inp, out = kth_largest_case(100_000, 50_000, vals)
    tests.append(make_test(inp, out, False, 8))

    # N = 100000, k = N (smallest element)
    inp, out = kth_largest_case(100_000, 100_000, vals)
    tests.append(make_test(inp, out, False, 9))

    return tests


# ---------------------------------------------------------------- #
# SORT 2 - Count inversions
# ---------------------------------------------------------------- #

def count_inversions(arr):
    # O(n log n) merge-sort based counter (used only to compute expected output)
    def sort_count(a):
        if len(a) <= 1:
            return a, 0
        mid = len(a) // 2
        left, cl = sort_count(a[:mid])
        right, cr = sort_count(a[mid:])
        merged, cm = [], 0
        i = j = 0
        while i < len(left) and j < len(right):
            if left[i] <= right[j]:
                merged.append(left[i]); i += 1
            else:
                merged.append(right[j]); j += 1
                cm += len(left) - i
        merged.extend(left[i:]); merged.extend(right[j:])
        return merged, cl + cr + cm

    _, count = sort_count(arr)
    return count


def inversions_case(values):
    inp = f"{len(values)}\n{' '.join(map(str, values))}\n"
    out = str(count_inversions(values))
    return inp, out


def build_sort2_tests():
    tests = []
    rng = random.Random(2)

    inp, out = inversions_case([2, 4, 1, 3, 5])
    tests.append(make_test(inp, out, True, 1))

    inp, out = inversions_case([5])
    tests.append(make_test(inp, out, False, 2))

    inp, out = inversions_case([1, 2, 3, 4, 5, 6, 7, 8])  # already sorted -> 0
    tests.append(make_test(inp, out, False, 3))

    inp, out = inversions_case([9, 8, 7, 6, 5, 4, 3, 2, 1])  # fully reversed small
    tests.append(make_test(inp, out, False, 4))

    vals = [rng.randint(-1000, 1000) for _ in range(2000)]
    inp, out = inversions_case(vals)
    tests.append(make_test(inp, out, False, 5))

    vals = [5] * 3000  # all equal -> 0 inversions
    inp, out = inversions_case(vals)
    tests.append(make_test(inp, out, False, 6))

    vals = [rng.randint(-10**9, 10**9) for _ in range(20_000)]
    inp, out = inversions_case(vals)
    tests.append(make_test(inp, out, False, 7))

    # N = 100000 fully reverse-sorted -> max inversions = 4999950000
    vals = list(range(100_000, 0, -1))
    inp, out = inversions_case(vals)
    tests.append(make_test(inp, out, False, 8))

    vals = [rng.randint(-10**9, 10**9) for _ in range(100_000)]
    inp, out = inversions_case(vals)
    tests.append(make_test(inp, out, False, 9))

    return tests


# ---------------------------------------------------------------- #
# SORT 3 - Sort ascending
# ---------------------------------------------------------------- #

def sort_case(values):
    inp = f"{len(values)}\n{' '.join(map(str, values))}\n"
    out = " ".join(map(str, sorted(values)))
    return inp, out


def build_sort3_tests():
    tests = []
    rng = random.Random(3)

    inp, out = sort_case([9, 2, 7, 4, 1])
    tests.append(make_test(inp, out, True, 1))

    inp, out = sort_case([42])
    tests.append(make_test(inp, out, False, 2))

    inp, out = sort_case([3] * 1000)  # duplicates only
    tests.append(make_test(inp, out, False, 3))

    vals = [rng.randint(-10**9, 10**9) for _ in range(1000)]
    inp, out = sort_case(vals)
    tests.append(make_test(inp, out, False, 4))

    vals = list(range(5000, -5000, -1))  # reverse sorted negatives + positives
    inp, out = sort_case(vals)
    tests.append(make_test(inp, out, False, 5))

    vals = [0] * 5000
    inp, out = sort_case(vals)
    tests.append(make_test(inp, out, False, 6))

    vals = [rng.randint(-10**9, 10**9) for _ in range(50_000)]
    inp, out = sort_case(vals)
    tests.append(make_test(inp, out, False, 7))

    # Dropped the two N=100,000 cases (previously order 8 & 9) - correct
    # O(n log n) solutions were hitting Time Limit Exceeded on Render's
    # throttled free-tier CPU even though they ran fine locally. 50,000
    # is still large enough to fail an O(n^2) solution.

    return tests


# ---------------------------------------------------------------- #
# Starter code templates
# ---------------------------------------------------------------- #

STARTER_PY_KTH = """# Read N and K, then N space-separated power levels.
# Print the K-th LARGEST power level.

n, k = map(int, input().split())
powers = list(map(int, input().split()))

# TODO: implement without using sorted()/list.sort() directly if you want
# full marks for a selection-based approach (heap / quickselect).
"""

STARTER_PY_INV = """# Read N, then N space-separated timestamps (can be negative).
# Print the number of inversions (i < j with a[i] > a[j]).
# Naive O(N^2) will TLE on the largest cases - use merge-sort counting.

n = int(input())
arr = list(map(int, input().split()))
"""

STARTER_PY_SORT = """# Read N, then N space-separated integers (can be negative).
# Print them in ascending order, space-separated.
# Implement your own sort (merge sort / quick sort) instead of sorted().

n = int(input())
arr = list(map(int, input().split()))
"""

STARTER_CPP = """#include <bits/stdc++.h>
using namespace std;

int main() {
    // your code here
    return 0;
}
"""

STARTER_C = """#include <stdio.h>

int main() {
    // your code here
    return 0;
}
"""

STARTER_JAVA = """import java.util.*;

public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        // your code here
    }
}
"""

STARTER_PY_PIZZA = """# IMPORTANT: read every input value SILENTLY - do NOT print any prompt text
# (no "Enter Name: ", no "Choose item: ", etc). Only the final bill below
# should ever be printed. The judge compares your stdout byte-for-byte
# against the exact bill format, so any extra printed text will fail it.
#
# Input format (one value per line):
#   Line 1: customer name
#   Line 2: delivery address
#   Line 3: number of people at the table
#   Then, repeating until a 0 is read:
#     one line: menu item number (1-4), or 0 to stop ordering
#     one line: quantity (only present when the item number was not 0)
#   Final line: "yes" or "no" - was delivery late?
#
# Menu (fixed prices):
#   1. Margherita Pizza - Rs.150
#   2. Pepperoni Pizza  - Rs.180
#   3. Garlic Bread     - Rs.60
#   4. Soda             - Rs.40
# Each menu item is chosen at most once per order.
#
# Output - print EXACTLY this format (see problem statement for the full
# worked example):
#   ----- ORDER SUMMARY -----
#   Customer: <name> | People: <people>
#   Address: <address>
#   <blank line>
#   <item name left-padded to 17 chars>x<qty>  = <amount>   (one line per item ordered, in order chosen)
#   -------------------------- (26 dashes)
#   <"Subtotal" left-padded to 21 chars>: <subtotal>
#   <"Delivery Tax (5%)" left-padded to 21 chars>: <tax>          (5% of subtotal, rounded to nearest integer)
#   <"Friendly Discount" left-padded to 21 chars>: <-100 if people >= 4, else 0>
#   <"Late Fee" left-padded to 21 chars>: <30 if late, else 0>
#   -------------------------- (26 dashes)
#   <"Total Payable" left-padded to 21 chars>: <total>
#   -------------------------- (26 dashes)
#   Thwip! Thanks for ordering.

import sys

MENU = [
    ("Margherita Pizza", 150),
    ("Pepperoni Pizza", 180),
    ("Garlic Bread", 60),
    ("Soda", 40),
]

# TODO: implement the billing logic and print the exact format described above.
"""

STARTER_PY_GEAR = """# IMPORTANT: read every input value SILENTLY - do NOT print any prompt text
# (no "Enter Hero Alias: ", no menu, etc). Only the final bill below should
# ever be printed. The judge compares your stdout byte-for-byte against the
# exact bill format, so any extra printed text will fail every test case.
#
# Input format (one value per line):
#   Line 1: hero alias
#   Line 2: secret identity
#   Line 3: contact number
#   Line 4: item number chosen (1-4)
#   Line 5: quantity
#
# Menu (fixed prices):
#   1. Web Shooter (pair)    - Rs.45000
#   2. Web Fluid Cartridge   - Rs.500
#   3. Spider-Tracer (pack)  - Rs.1200
#   4. Impact Webbing Suit   - Rs.1800
#
# Discount tiers (based on subtotal = price * quantity):
#   Subtotal >= 50000 -> 15% discount
#   Subtotal >= 20000 -> 10% discount
#   Subtotal <  20000 -> 0% discount
# Discount Amount = round(subtotal * pct / 100). Final Amount = subtotal - Discount Amount.
#
# Output - print EXACTLY this format (see problem statement for the full
# worked example):
#   ----- HERO REGISTRATION -----
#   Alias: <alias>
#   Identity: <identity>
#   Contact: <contact>
#   <blank line>
#   ----- GEAR BILL -----
#   Item: <item name>
#   Quantity: <qty>
#   Price/unit: <price>
#   Subtotal: <subtotal>
#   Discount Applied: <pct>%
#   Discount Amount: <discount amount>
#   Final Amount: <final amount>
#   ---------------------------- (28 dashes)
#   Stay safe out there, Spidey!

GEAR_MENU = [
    ("Web Shooter (pair)", 45000),
    ("Web Fluid Cartridge", 500),
    ("Spider-Tracer (pack)", 1200),
    ("Impact Webbing Suit", 1800),
]

# TODO: implement the billing logic and print the exact format described above.
"""

STARTER_PY_TICKET = """# IMPORTANT: read every input value SILENTLY - do NOT print any prompt text
# (no "Enter Name: ", no slot list, etc). Only the final booking confirmation
# below should ever be printed. The judge compares your stdout byte-for-byte
# against the exact format, so any extra printed text will fail every test case.
#
# Input format (one value per line):
#   Line 1: visitor name
#   Line 2: visitor age (integer)
#   Line 3: dimension of origin
#   Line 4: slot number chosen (1-3)
#   Line 5: number of tickets
#
# Slots (fixed prices per seat):
#   1. Earth-616 Wing     - Rs.250/seat
#   2. Earth-1610 Wing    - Rs.180/seat
#   3. Earth-928 Wing     - Rs.200/seat
#
# Discount logic (applied to subtotal = price * tickets):
#   Age < 12 or Age > 60      -> +20% discount
#   Tickets >= 4                -> +10% discount
#   (percentages ADD, e.g. both conditions -> 30% off; discount amount =
#    round(subtotal * total_pct / 100))
# Cleanup fee: flat Rs.20 per ticket, added AFTER the discount.
#
# Discount line text (must match exactly):
#   no discount     -> "0 (no discount)"
#   age only        -> "<amount> (20% age discount)"
#   group only       -> "<amount> (10% group discount)"
#   both             -> "<amount> (30% age + group discount)"
#
# Output - print EXACTLY this format (see problem statement for the full
# worked example). Every "label : value" line pads the label to 20 characters
# before the colon:
#   ----- BOOKING CONFIRMATION -----
#   Name: <name> | Age: <age> | Dimension: <dimension>
#   Slot: <slot name>
#   Tickets: <tickets>
#   <blank line>
#   Price/seat          : <price>
#   Discount            : <discount line text above>
#   Subtotal            : <subtotal after discount>
#   Cleanup Fee         : <cleanup fee>
#   --------------------------------- (33 dashes)
#   Total Payable       : <total>
#   --------------------------------- (33 dashes)
#   Enjoy the multiverse!

TICKET_SLOTS = [
    ("Earth-616 Wing", 250),
    ("Earth-1610 Wing", 180),
    ("Earth-928 Wing", 200),
]

# TODO: implement the booking logic and print the exact format described above.
"""


# ---------------------------------------------------------------- #
# PIZZA - Pete's Pizza-Time Billing System
# ---------------------------------------------------------------- #

PIZZA_MENU = [
    ("Margherita Pizza", 150),
    ("Pepperoni Pizza", 180),
    ("Garlic Bread", 60),
    ("Soda", 40),
]


def pizza_case(name, address, people, order, late):
    """order: list of (menu_index_1_based, qty). Returns (input_text, output_text)
    using the exact same reference logic used to build the problem statement's
    worked example, so grading matches a straightforward correct implementation."""
    lines = [name, address, str(people)]
    for idx, qty in order:
        lines.append(str(idx))
        lines.append(str(qty))
    lines.append("0")
    lines.append("yes" if late else "no")
    input_text = "\n".join(lines) + "\n"

    items = []
    subtotal = 0
    for idx, qty in order:
        item_name, price = PIZZA_MENU[idx - 1]
        amt = price * qty
        items.append((item_name, qty, amt))
        subtotal += amt

    tax = round(subtotal * 0.05)
    discount = 100 if people >= 4 else 0
    late_fee = 30 if late else 0
    total = subtotal + tax - discount + late_fee

    out_lines = [
        "----- ORDER SUMMARY -----",
        f"Customer: {name} | People: {people}",
        f"Address: {address}",
        "",
    ]
    for item_name, qty, amt in items:
        out_lines.append(f"{item_name:<17}x{qty}  = {amt}")
    out_lines.append("-" * 26)
    out_lines.append(f"{'Subtotal':<21}: {subtotal}")
    out_lines.append(f"{'Delivery Tax (5%)':<21}: {tax}")
    out_lines.append(f"{'Friendly Discount':<21}: {-discount if discount else 0}")
    out_lines.append(f"{'Late Fee':<21}: {late_fee}")
    out_lines.append("-" * 26)
    out_lines.append(f"{'Total Payable':<21}: {total}")
    out_lines.append("-" * 26)
    out_lines.append("Thwip! Thanks for ordering.")
    output_text = "\n".join(out_lines)

    return input_text, output_text


def build_pizza_tests():
    tests = []

    # Sample - matches the brief's worked example exactly (Total Payable: 518).
    inp, out = pizza_case("MJ", "20 Ingram Street", 5, [(2, 2), (4, 5)], True)
    tests.append(make_test(inp, out, True, 1))

    # No discount (people < 4), no late fee, two items.
    inp, out = pizza_case("Peter", "10 Baxter St", 2, [(1, 2), (3, 1)], False)
    tests.append(make_test(inp, out, False, 2))

    # Discount at exact threshold (people == 4), no late fee, one item.
    inp, out = pizza_case("Gwen", "5 Webb Ave", 4, [(2, 3)], False)
    tests.append(make_test(inp, out, False, 3))

    # No discount, late fee applies, single item, small subtotal.
    inp, out = pizza_case("Miles", "42 Visions Rd", 1, [(3, 1)], True)
    tests.append(make_test(inp, out, False, 4))

    return tests


# ---------------------------------------------------------------- #
# GEAR - Spider-Gear Shop Billing System
# ---------------------------------------------------------------- #

GEAR_MENU = [
    ("Web Shooter (pair)", 45000),
    ("Web Fluid Cartridge", 500),
    ("Spider-Tracer (pack)", 1200),
    ("Impact Webbing Suit", 1800),
]


def gear_case(alias, identity, contact, item_no, qty):
    """item_no: 1-based menu index. Returns (input_text, output_text) using
    the exact reference logic used to build the problem statement's worked
    example, so grading matches a straightforward correct implementation."""
    lines = [alias, identity, contact, str(item_no), str(qty)]
    input_text = "\n".join(lines) + "\n"

    item_name, price = GEAR_MENU[item_no - 1]
    subtotal = price * qty
    if subtotal >= 50000:
        pct = 15
    elif subtotal >= 20000:
        pct = 10
    else:
        pct = 0
    discount_amount = round(subtotal * pct / 100)
    final_amount = subtotal - discount_amount

    out_lines = [
        "----- HERO REGISTRATION -----",
        f"Alias: {alias}",
        f"Identity: {identity}",
        f"Contact: {contact}",
        "",
        "----- GEAR BILL -----",
        f"Item: {item_name}",
        f"Quantity: {qty}",
        f"Price/unit: {price}",
        f"Subtotal: {subtotal}",
        f"Discount Applied: {pct}%",
        f"Discount Amount: {discount_amount}",
        f"Final Amount: {final_amount}",
        "-" * 28,
        "Stay safe out there, Spidey!",
    ]
    output_text = "\n".join(out_lines)

    return input_text, output_text


def build_gear_tests():
    tests = []

    # Sample - matches the brief's worked example exactly (Final Amount: 2400).
    inp, out = gear_case("Spider-Man", "Peter Parker", "9876543210", 3, 2)
    tests.append(make_test(inp, out, True, 1))

    # Exact 10% boundary (subtotal == 20000).
    inp, out = gear_case("Ms. Marvel", "Kamala Khan", "9998887776", 2, 40)
    tests.append(make_test(inp, out, False, 2))

    # Exact 15% boundary (subtotal == 50000).
    inp, out = gear_case("Ghost-Spider", "Gwen Stacy", "9112233445", 2, 100)
    tests.append(make_test(inp, out, False, 3))

    # No discount, single unit, different item.
    inp, out = gear_case("Spidey", "Miles Morales", "9223344556", 4, 1)
    tests.append(make_test(inp, out, False, 4))

    return tests


# ---------------------------------------------------------------- #
# TICKET - Spider-Verse Exhibit Ticket Booking
# ---------------------------------------------------------------- #

TICKET_SLOTS = [
    ("Earth-616 Wing", 250),
    ("Earth-1610 Wing", 180),
    ("Earth-928 Wing", 200),
]


def ticket_case(name, age, dimension, slot_no, tickets):
    """slot_no: 1-based slot index. Returns (input_text, output_text) using
    the exact reference logic used to build the problem statement's worked
    example, so grading matches a straightforward correct implementation."""
    lines = [name, str(age), dimension, str(slot_no), str(tickets)]
    input_text = "\n".join(lines) + "\n"

    slot_name, price = TICKET_SLOTS[slot_no - 1]
    subtotal = price * tickets

    age_applies = age < 12 or age > 60
    group_applies = tickets >= 4
    pct = (20 if age_applies else 0) + (10 if group_applies else 0)
    discount_amount = round(subtotal * pct / 100)

    if pct == 0:
        discount_str = "0 (no discount)"
    elif age_applies and group_applies:
        discount_str = f"{discount_amount} ({pct}% age + group discount)"
    elif age_applies:
        discount_str = f"{discount_amount} ({pct}% age discount)"
    else:
        discount_str = f"{discount_amount} ({pct}% group discount)"

    final_subtotal = subtotal - discount_amount
    cleanup_fee = 20 * tickets
    total = final_subtotal + cleanup_fee

    out_lines = [
        "----- BOOKING CONFIRMATION -----",
        f"Name: {name} | Age: {age} | Dimension: {dimension}",
        f"Slot: {slot_name}",
        f"Tickets: {tickets}",
        "",
        f"{'Price/seat':<20}: {price}",
        f"{'Discount':<20}: {discount_str}",
        f"{'Subtotal':<20}: {final_subtotal}",
        f"{'Cleanup Fee':<20}: {cleanup_fee}",
        "-" * 33,
        f"{'Total Payable':<20}: {total}",
        "-" * 33,
        "Enjoy the multiverse!",
    ]
    output_text = "\n".join(out_lines)

    return input_text, output_text


def build_ticket_tests():
    tests = []

    # Sample - matches the brief's worked example exactly (Total Payable: 540).
    inp, out = ticket_case("Gwen", 17, "Earth-65", 1, 2)
    tests.append(make_test(inp, out, True, 1))

    # Age discount only (age < 12).
    inp, out = ticket_case("Miles", 10, "Earth-1610", 2, 2)
    tests.append(make_test(inp, out, False, 2))

    # Group discount only (tickets >= 4).
    inp, out = ticket_case("Peni", 30, "Earth-14512", 3, 4)
    tests.append(make_test(inp, out, False, 3))

    # Both discounts stack (age > 60 and tickets >= 4).
    inp, out = ticket_case("Uncle Ben", 70, "Earth-616", 1, 5)
    tests.append(make_test(inp, out, False, 4))

    return tests


# ---------------------------------------------------------------- #

def main():
    client = MongoClient(MONGO_URI)
    db = client.get_default_database()

    event = db.events.find_one({"title": EVENT_TITLE})
    if not event:
        from datetime import datetime
        result = db.events.insert_one({
            "title": EVENT_TITLE,
            "description": "Sorting + simulation challenges across the Spider-Verse.",
            "start_date": datetime(2026, 1, 1),
            "end_date": datetime(2026, 12, 31),
        })
        event_id = str(result.inserted_id)
        print(f"Created event '{EVENT_TITLE}' -> {event_id}")
    else:
        event_id = str(event["_id"])
        print(f"Using existing event '{EVENT_TITLE}' -> {event_id}")

    def upsert_problem(title, problem_type, **fields):
        existing = db.problem_statements.find_one({"event_id": event_id, "title": title})
        doc = {"event_id": event_id, "title": title, "problem_type": problem_type, **fields}
        if existing:
            db.problem_statements.update_one({"_id": existing["_id"]}, {"$set": doc})
            pid = str(existing["_id"])
            db.test_cases.delete_many({"problem_id": pid})
            print(f"Updated problem '{title}' -> {pid}")
        else:
            result = db.problem_statements.insert_one(doc)
            pid = str(result.inserted_id)
            print(f"Inserted problem '{title}' -> {pid}")
        return pid

    # ---- SET 1 ----
    pid = upsert_problem(
        "The K-th Strongest Henchman", "code",
        difficulty="Easy",
        description=(
            "Peter has hacked into Kingpin's servers and pulled a list of N henchmen with "
            "their power levels. He needs to know who the K-th strongest henchman is, so he "
            "knows exactly how much muscle he's up against."
        ),
        input_format="Line 1: N K\nLine 2: N space-separated power levels",
        output_format="A single integer — the K-th largest power level",
        constraints=(
            "1 <= K <= N <= 100000\n0 <= power level <= 10^9\n"
            "No built-in \"find kth\" library shortcuts — solve via a sorting-based or "
            "selection approach (quickselect / heap / sort)."
        ),
        sample_input="6 3\n7 10 4 3 20 15\n",
        sample_output="10",
        time_limit_ms=2000,
        starter_code={"python3": STARTER_PY_KTH, "cpp": STARTER_CPP, "c": STARTER_C, "java": STARTER_JAVA},
        max_size_mb=20,
    )
    for t in build_sort1_tests():
        t["problem_id"] = pid
        db.test_cases.insert_one(t)

    pid = upsert_problem(
        "Spider-Gear Shop Billing System", "code",
        difficulty="Easy",
        description=(
            "Peter needs gear before patrol. Build a program that takes hero registration "
            "details, shows a gear menu, lets the user pick an item and quantity, applies a "
            "tiered discount based on total bill value, and prints a formatted final bill.\n\n"
            "IMPORTANT - this is auto-graded, so the output format below is a strict "
            "requirement, not just an example: read every input value silently (no prompt "
            "text or menu of your own printed to stdout) and print ONLY the exact bill format "
            "shown in the starter code / output format below. Any extra printed text will "
            "cause every test case to fail, since the judge compares stdout byte-for-byte."
        ),
        input_format=(
            "Line 1: hero alias\nLine 2: secret identity\nLine 3: contact number\n"
            "Line 4: item number chosen (1-4)\nLine 5: quantity\n\n"
            "Fixed menu:\n1. Web Shooter (pair)    - Rs.45000\n2. Web Fluid Cartridge   - Rs.500\n"
            "3. Spider-Tracer (pack)  - Rs.1200\n4. Impact Webbing Suit   - Rs.1800"
        ),
        output_format=(
            "----- HERO REGISTRATION -----\n"
            "Alias: <alias>\nIdentity: <identity>\nContact: <contact>\n"
            "<blank line>\n"
            "----- GEAR BILL -----\n"
            "Item: <item name>\nQuantity: <qty>\nPrice/unit: <price>\nSubtotal: <price*qty>\n"
            "Discount Applied: <pct>%\nDiscount Amount: <round(subtotal*pct/100)>\n"
            "Final Amount: <subtotal - discount amount>\n"
            "---------------------------- (28 dashes)\n"
            "Stay safe out there, Spidey!"
        ),
        constraints=(
            "1 <= quantity <= 1000\n"
            "Discount tiers (based on subtotal = price * quantity):\n"
            "Subtotal >= 50000 -> 15% off\nSubtotal >= 20000 -> 10% off\nSubtotal < 20000 -> no discount"
        ),
        sample_input="Spider-Man\nPeter Parker\n9876543210\n3\n2\n",
        sample_output=(
            "----- HERO REGISTRATION -----\n"
            "Alias: Spider-Man\n"
            "Identity: Peter Parker\n"
            "Contact: 9876543210\n\n"
            "----- GEAR BILL -----\n"
            "Item: Spider-Tracer (pack)\n"
            "Quantity: 2\n"
            "Price/unit: 1200\n"
            "Subtotal: 2400\n"
            "Discount Applied: 0%\n"
            "Discount Amount: 0\n"
            "Final Amount: 2400\n"
            "----------------------------\n"
            "Stay safe out there, Spidey!"
        ),
        time_limit_ms=2000,
        starter_code={"python3": STARTER_PY_GEAR, "cpp": STARTER_CPP, "c": STARTER_C, "java": STARTER_JAVA},
        max_size_mb=20,
    )
    for t in build_gear_tests():
        t["problem_id"] = pid
        db.test_cases.insert_one(t)

    # ---- SET 2 ----
    pid = upsert_problem(
        "Count the Out-of-Order Pairs", "code",
        difficulty="Hard",
        description=(
            "J. Jonah Jameson has a strip of N photo-timestamps that got shuffled by MJ. He "
            "wants to know how many pairs of photos are in the wrong relative order (a "
            "later-index photo has a smaller timestamp than an earlier one) before deciding "
            "whether it's worth re-sorting them for print. This is the classic inversion "
            "count problem."
        ),
        input_format="Line 1: N\nLine 2: N space-separated integers (timestamps, can be negative)",
        output_format="A single integer — the number of inversions (pairs i<j with a[i] > a[j])",
        constraints=(
            "1 <= N <= 100000\n-10^9 <= value <= 10^9\n"
            "Output can be as large as ~5x10^9 — use a 64-bit integer type.\n"
            "Naive O(N^2) will TLE on the large cases; use merge-sort based counting "
            "(O(N log N)) for full marks."
        ),
        sample_input="5\n2 4 1 3 5\n",
        sample_output="3",
        time_limit_ms=3000,
        starter_code={"python3": STARTER_PY_INV, "cpp": STARTER_CPP, "c": STARTER_C, "java": STARTER_JAVA},
        max_size_mb=20,
    )
    for t in build_sort2_tests():
        t["problem_id"] = pid
        db.test_cases.insert_one(t)

    pid = upsert_problem(
        "Pete's Pizza-Time Billing System", "code",
        difficulty="Medium",
        description=(
            "Between web-slinging, Peter delivers pizza. Build a program that takes customer "
            "details, displays a food menu, lets the customer order multiple items in a loop, "
            "adds a 5% delivery tax, applies a flat Rs.100 'Friendly Neighborhood Discount' for "
            "groups of 4+, adds a Rs.30 late fee if applicable, and prints an itemized bill.\n\n"
            "IMPORTANT - this is auto-graded, so the output format below is a strict "
            "requirement, not just an example: read every input value silently (no prompt "
            "text of your own printed to stdout) and print ONLY the exact bill format shown "
            "in the starter code / output format below. Any extra printed text (menus, "
            "prompts, debug output) will cause every test case to fail, since the judge "
            "compares stdout byte-for-byte."
        ),
        input_format=(
            "Line 1: customer name\nLine 2: delivery address\nLine 3: number of people\n"
            "Then, repeating until a 0 is read: one line with a menu item number (1-4, or 0 "
            "to stop ordering), followed by one line with the quantity (only when the item "
            "number wasn't 0). Each menu item is chosen at most once per order.\n"
            "Final line: \"yes\" or \"no\" - was delivery late?\n\n"
            "Fixed menu:\n1. Margherita Pizza - Rs.150\n2. Pepperoni Pizza  - Rs.180\n"
            "3. Garlic Bread     - Rs.60\n4. Soda             - Rs.40"
        ),
        output_format=(
            "----- ORDER SUMMARY -----\n"
            "Customer: <name> | People: <people>\n"
            "Address: <address>\n"
            "<blank line>\n"
            "<item name left-padded to 17 chars>x<qty>  = <amount>   (one line per ordered item, in order chosen)\n"
            "-------------------------- (26 dashes)\n"
            "Subtotal (left-padded label to 21 chars): <subtotal>\n"
            "Delivery Tax (5%) (left-padded to 21 chars): <tax, 5% of subtotal rounded to nearest integer>\n"
            "Friendly Discount (left-padded to 21 chars): <-100 if people >= 4, else 0>\n"
            "Late Fee (left-padded to 21 chars): <30 if late, else 0>\n"
            "-------------------------- (26 dashes)\n"
            "Total Payable (left-padded to 21 chars): <subtotal + tax - discount + late fee>\n"
            "-------------------------- (26 dashes)\n"
            "Thwip! Thanks for ordering."
        ),
        constraints=(
            "1 <= number of people <= 20\n1 <= quantity per item <= 100\n"
            "Each of the 4 menu items is ordered at most once per order (at least 1 item ordered)."
        ),
        sample_input="MJ\n20 Ingram Street\n5\n2\n2\n4\n5\n0\nyes\n",
        sample_output=(
            "----- ORDER SUMMARY -----\n"
            "Customer: MJ | People: 5\n"
            "Address: 20 Ingram Street\n\n"
            "Pepperoni Pizza  x2  = 360\n"
            "Soda             x5  = 200\n"
            "--------------------------\n"
            "Subtotal             : 560\n"
            "Delivery Tax (5%)    : 28\n"
            "Friendly Discount    : -100\n"
            "Late Fee             : 30\n"
            "--------------------------\n"
            "Total Payable        : 518\n"
            "--------------------------\n"
            "Thwip! Thanks for ordering."
        ),
        time_limit_ms=2000,
        starter_code={"python3": STARTER_PY_PIZZA, "cpp": STARTER_CPP, "c": STARTER_C, "java": STARTER_JAVA},
        max_size_mb=20,
    )
    for t in build_pizza_tests():
        t["problem_id"] = pid
        db.test_cases.insert_one(t)

    # ---- SET 3 ----
    pid = upsert_problem(
        "Sort the Multiverse Signals", "code",
        difficulty="Medium",
        description=(
            "Miguel O'Hara's dimensional tracker picked up N signal strengths from across the "
            "Spider-Verse. Sort them in ascending order so the team can scan from weakest to "
            "strongest anomaly."
        ),
        input_format="Line 1: N\nLine 2: N space-separated integers (can be negative)",
        output_format="N space-separated integers in ascending order",
        constraints=(
            "1 <= N <= 100000\n-10^9 <= value <= 10^9\n"
            "No built-in sort function allowed — implement manually (merge sort / quick sort "
            "recommended; bubble/insertion sort will be too slow at N=100000)."
        ),
        sample_input="5\n9 2 7 4 1\n",
        sample_output="1 2 4 7 9",
        time_limit_ms=2000,
        starter_code={"python3": STARTER_PY_SORT, "cpp": STARTER_CPP, "c": STARTER_C, "java": STARTER_JAVA},
        max_size_mb=20,
    )
    for t in build_sort3_tests():
        t["problem_id"] = pid
        db.test_cases.insert_one(t)

    pid = upsert_problem(
        "Spider-Verse Exhibit Ticket Booking", "code",
        difficulty="Medium",
        description=(
            "Build a program for visitor registration and exhibit ticket booking: show slots "
            "and prices, let the visitor pick a slot and ticket count, apply age-based and "
            "group-size discounts, add a flat Rs.20 cleanup fee per ticket, and print the "
            "final bill.\n\n"
            "IMPORTANT - this is auto-graded, so the output format below is a strict "
            "requirement, not just an example: read every input value silently (no prompt "
            "text or slot menu of your own printed to stdout) and print ONLY the exact "
            "confirmation format shown in the starter code / output format below. Any extra "
            "printed text will cause every test case to fail, since the judge compares "
            "stdout byte-for-byte."
        ),
        input_format=(
            "Line 1: visitor name\nLine 2: visitor age (integer)\nLine 3: dimension of origin\n"
            "Line 4: slot number chosen (1-3)\nLine 5: number of tickets\n\n"
            "Fixed slots:\n1. Earth-616 Wing     - Rs.250/seat\n2. Earth-1610 Wing    - Rs.180/seat\n"
            "3. Earth-928 Wing     - Rs.200/seat"
        ),
        output_format=(
            "----- BOOKING CONFIRMATION -----\n"
            "Name: <name> | Age: <age> | Dimension: <dimension>\n"
            "Slot: <slot name>\nTickets: <tickets>\n"
            "<blank line>\n"
            "<\"Price/seat\" left-padded to 20 chars>: <price>\n"
            "<\"Discount\" left-padded to 20 chars>: <discount amount> (<pct>% ...discount) or "
            "\"0 (no discount)\"\n"
            "<\"Subtotal\" left-padded to 20 chars>: <subtotal after discount>\n"
            "<\"Cleanup Fee\" left-padded to 20 chars>: <20 * tickets>\n"
            "--------------------------------- (33 dashes)\n"
            "<\"Total Payable\" left-padded to 20 chars>: <subtotal + cleanup fee>\n"
            "--------------------------------- (33 dashes)\n"
            "Enjoy the multiverse!"
        ),
        constraints=(
            "1 <= tickets <= 50\n0 <= age <= 120\n"
            "Discount: age < 12 or age > 60 adds 20%; tickets >= 4 adds 10% (percentages ADD, "
            "e.g. both -> 30%). Discount amount = round(subtotal * total_pct / 100), where "
            "subtotal = price * tickets. Cleanup fee (Rs.20/ticket) is added AFTER the discount.\n"
            "Discount line text: \"0 (no discount)\" / \"<amt> (20% age discount)\" / "
            "\"<amt> (10% group discount)\" / \"<amt> (30% age + group discount)\"."
        ),
        sample_input="Gwen\n17\nEarth-65\n1\n2\n",
        sample_output=(
            "----- BOOKING CONFIRMATION -----\n"
            "Name: Gwen | Age: 17 | Dimension: Earth-65\n"
            "Slot: Earth-616 Wing\n"
            "Tickets: 2\n\n"
            "Price/seat          : 250\n"
            "Discount            : 0 (no discount)\n"
            "Subtotal            : 500\n"
            "Cleanup Fee         : 40\n"
            "---------------------------------\n"
            "Total Payable       : 540\n"
            "---------------------------------\n"
            "Enjoy the multiverse!"
        ),
        time_limit_ms=2000,
        starter_code={"python3": STARTER_PY_TICKET, "cpp": STARTER_CPP, "c": STARTER_C, "java": STARTER_JAVA},
        max_size_mb=20,
    )
    for t in build_ticket_tests():
        t["problem_id"] = pid
        db.test_cases.insert_one(t)

    print("\nDone. 6 code problems (auto-graded, sandbox-runnable) seeded across 3 sets.")


if __name__ == "__main__":
    main()