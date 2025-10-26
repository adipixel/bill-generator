from flask import Flask, render_template, request, send_file, abort, redirect, url_for
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
COMPANIES_FILE = 'companies.csv'
CONSULTANCIES_FILE = 'consultancies.csv'

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

def load_companies():
    """Return list of companies as dicts: {'company_id': int, 'name': str, 'bank_details': str}"""
    if not os.path.exists(COMPANIES_FILE):
        return []
    companies = []
    with open(COMPANIES_FILE, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                row['company_id'] = int(row.get('company_id')) if row.get('company_id') not in (None, '') else None
            except (ValueError, TypeError):
                pass
            # normalize bank details
            row['bank_details'] = _normalize_multiline(row.get('bank_details',''))
            companies.append(row)
    return companies

def save_company(name, bank_details):
    fieldnames = ['company_id', 'name', 'bank_details']
    companies = load_companies()
    next_id = 1
    if companies:
        try:
            next_id = max([c.get('company_id') or 0 for c in companies]) + 1
        except Exception:
            next_id = len(companies) + 1
    row = {'company_id': next_id, 'name': name, 'bank_details': _normalize_multiline(bank_details)}
    file_exists = os.path.exists(COMPANIES_FILE)
    with open(COMPANIES_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def load_consultancies():
    """Return list of consultancies as dicts: {'consultancy_id': int, 'name': str}"""
    if not os.path.exists(CONSULTANCIES_FILE):
        return []
    consultancies = []
    with open(CONSULTANCIES_FILE, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                row['consultancy_id'] = int(row.get('consultancy_id')) if row.get('consultancy_id') not in (None, '') else None
            except (ValueError, TypeError):
                pass
            consultancies.append(row)
    return consultancies

def save_consultancy(name):
    fieldnames = ['consultancy_id', 'name']
    consultancies = load_consultancies()
    next_id = 1
    if consultancies:
        try:
            next_id = max([c.get('consultancy_id') or 0 for c in consultancies]) + 1
        except Exception:
            next_id = len(consultancies) + 1
    row = {'consultancy_id': next_id, 'name': name}
    file_exists = os.path.exists(CONSULTANCIES_FILE)
    with open(CONSULTANCIES_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

@app.route('/')
def index():
    bills = load_bills()
    companies = load_companies()
    consultancies = load_consultancies()
    return render_template('index.html', bills=reversed(bills), companies=companies, consultancies=consultancies)

@app.route('/generate', methods=['POST'])
def generate_bill():
    # Get form data
    # Get both client and consultancy names
    client_name = request.form.get('client_name') or ''
    # Resolve consultancy from select (consultancy_id) or fallback to text field
    consultancy_name = ''
    consultancy_id = request.form.get('consultancy_id') or ''
    if consultancy_id and consultancy_id != 'custom':
        # try to resolve consultancy name
        try:
            c_id = int(consultancy_id)
        except Exception:
            c_id = consultancy_id
        for c in load_consultancies():
            # compare int or string
            try:
                if int(c.get('consultancy_id')) == int(c_id):
                    consultancy_name = c.get('name') or ''
                    break
            except Exception:
                if str(c.get('consultancy_id')) == str(c_id):
                    consultancy_name = c.get('name') or ''
                    break
    if not consultancy_name:
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

# Companies management
@app.route('/companies', methods=['GET', 'POST'])
def companies_view():
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        bank_details = request.form.get('bank_details','')
        if name:
            save_company(name, bank_details)
        return redirect(url_for('index'))
    companies = load_companies()
    return render_template('companies.html', companies=companies)

# Consultancies management
@app.route('/consultancies', methods=['GET', 'POST'])
def consultancies_view():
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        if name:
            save_consultancy(name)
        return redirect(url_for('index'))
    consultancies = load_consultancies()
    return render_template('consultancies.html', consultancies=consultancies)

if __name__ == '__main__':
    app.run(debug=True)
