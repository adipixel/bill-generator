from flask import Flask, render_template, request, send_file, abort
import csv
import os
from datetime import datetime


def _normalize_multiline(text):
    """Trim lines and remove empty lines, return joined with single newline."""
    if not text:
        return ''
    try:
        lines = text.splitlines()
    except Exception:
        return str(text)
    cleaned = [ln.strip() for ln in lines if ln.strip()]
    return "\n".join(cleaned)

app = Flask(__name__)

# Files
BILLS_FILE = 'bills.csv'
BILL_COUNTER_FILE = 'bill_counter.txt'

def get_next_bill_number():
    try:
        with open(BILL_COUNTER_FILE, 'r') as f:
            return int(f.read().strip()) + 1
    except FileNotFoundError:
        return 1001

def save_bill_number(number):
    with open(BILL_COUNTER_FILE, 'w') as f:
        f.write(str(number))

def load_bills():
    if not os.path.exists(BILLS_FILE):
        return []
    
    bills = []
    with open(BILLS_FILE, 'r', newline='') as f:
        first_line = f.readline()
        if not first_line:
            return []
        # Peek first row to detect whether file includes a header
        try:
            first_row = next(csv.reader([first_line]))
        except Exception:
            first_row = []

        expected_fields = ['bill_number', 'consultancy_name', 'client_name', 'date', 'billed_for', 'items', 'total', 'bank_details']
        # If first cell looks like a number (bill number) it's probably data — otherwise it may be a header.
        looks_like_data = False
        if first_row:
            try:
                int(first_row[0])
                looks_like_data = True
            except Exception:
                looks_like_data = False

        f.seek(0)
        if looks_like_data:
            reader = csv.DictReader(f, fieldnames=expected_fields)
        else:
            reader = csv.DictReader(f)

        for row in reader:
            # Parse items from CSV string
            items = []
            if row.get('items'):
                item_lines = row['items'].split(';')
                for line in item_lines:
                    if ':' in line:
                        desc, cost = line.split(':', 1)
                        try:
                            cost_val = float(cost)
                        except (ValueError, TypeError):
                            cost_val = 0.0
                        items.append({'description': desc, 'cost': cost_val})
            row['items'] = items

            # Ensure numeric fields are the correct type
            try:
                row['total'] = float(row['total']) if row.get('total') not in (None, '') else 0.0
            except (ValueError, TypeError):
                row['total'] = 0.0

            try:
                row['bill_number'] = int(row['bill_number']) if row.get('bill_number') not in (None, '') else None
            except (ValueError, TypeError):
                # Leave as-is (string) if it can't be converted
                pass

            # Normalize bank details to remove blank lines
            if 'bank_details' in row:
                row['bank_details'] = _normalize_multiline(row.get('bank_details', ''))

            # Ensure billed_for exists
            if 'billed_for' not in row:
                row['billed_for'] = row.get('billed_for', '')

            # Backwards compatibility: older CSVs may have 'client_name' or only 'consultancy_name'
            if 'consultancy_name' not in row and 'client_name' in row:
                row['consultancy_name'] = row.get('client_name')
            if 'client_name' not in row and 'consultancy_name' in row:
                row['client_name'] = row.get('consultancy_name')

            bills.append(row)
    return bills

def save_bill(bill_data):
    fieldnames = ['bill_number', 'consultancy_name', 'client_name', 'date', 'billed_for', 'items', 'total', 'bank_details']
    
    # Convert items to CSV-friendly string
    items_str = ';'.join([f"{item['description']}:{item['cost']}" for item in bill_data['items']])
    
    row = {
        'bill_number': bill_data['bill_number'],
        'consultancy_name': bill_data['consultancy_name'],
        'client_name': bill_data.get('client_name',''),
        'billed_for': bill_data.get('billed_for',''),
        'date': bill_data['date'],
        'items': items_str,
        'total': bill_data['total'],
        'bank_details': bill_data['bank_details']
    }
    
    file_exists = os.path.exists(BILLS_FILE)
    with open(BILLS_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

@app.route('/')
def index():
    bills = load_bills()
    return render_template('index.html', bills=reversed(bills))

@app.route('/generate', methods=['POST'])
def generate_bill():
    # Get form data
    # Get both client and consultancy names
    client_name = request.form.get('client_name') or ''
    consultancy_name = request.form.get('consultancy_name') or request.form.get('client_name') or ''
    bank_details = request.form.get('bank_details', '')
    billed_for = request.form.get('billed_for', '')
    # Normalize input bank details to remove extra blank lines/spaces
    bank_details = _normalize_multiline(bank_details)
    
    # Process items
    items = []
    total = 0
    
    item_descriptions = request.form.getlist('item_description[]')
    item_costs = request.form.getlist('item_cost[]')
    
    for desc, cost_str in zip(item_descriptions, item_costs):
        if desc.strip():  # Only add if description is not empty
            try:
                cost = float(cost_str)
                items.append({'description': desc, 'cost': cost})
                total += cost
            except ValueError:
                continue
    
    # Generate bill
    bill_number = get_next_bill_number()
    date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


    bill_data = {
        'bill_number': bill_number,
        'consultancy_name': consultancy_name,
        'client_name': client_name,
        'billed_for': billed_for,
        'date': date,
        'items': items,
        'total': total,
        'bank_details': bank_details
    }
    
    # Save bill and update counter
    save_bill(bill_data)
    save_bill_number(bill_number)
    
    return render_template('bill_display.html', bill=bill_data)

@app.route('/download_csv')
def download_csv():
    return send_file(BILLS_FILE, as_attachment=True)

@app.route('/bill/<int:bill_number>')
def show_bill(bill_number):
    bills = load_bills()
    for b in bills:
        # bill_number may be int or string in loaded rows; handle both
        try:
            if int(b.get('bill_number')) == int(bill_number):
                return render_template('bill_display.html', bill=b)
        except (ValueError, TypeError):
            # fallback string comparison
            if str(b.get('bill_number')) == str(bill_number):
                return render_template('bill_display.html', bill=b)
    # not found
    abort(404)

if __name__ == '__main__':
    app.run(debug=True)
