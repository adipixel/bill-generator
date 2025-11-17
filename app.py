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
BILL_COUNTERS_FILE = 'bill_counters.csv'  # New file for per-consultancy counters
COMPANIES_FILE = 'companies.csv'
CONSULTANCIES_FILE = 'consultancies.csv'

def get_next_bill_number(consultancy_id):
    """Get next bill number for specific consultancy"""
    counters = {}
    try:
        with open(BILL_COUNTERS_FILE, 'r', newline='') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    counters[row['consultancy_id']] = int(row['last_number'])
                except (ValueError, KeyError):
                    continue
    except FileNotFoundError:
        # Initialize file if it doesn't exist
        counters = {}
    
    # Get or initialize counter for this consultancy
    current = counters.get(str(consultancy_id), 1000)
    next_number = current + 1
    
    # Update counter
    counters[str(consultancy_id)] = next_number
    
    # Save all counters back
    with open(BILL_COUNTERS_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['consultancy_id', 'last_number'])
        writer.writeheader()
        for cid, num in counters.items():
            writer.writerow({'consultancy_id': cid, 'last_number': num})
    
    return next_number

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
    """Return list of companies as dicts: {'company_id': int, 'name': str, 'consultancy_id': int}"""
    if not os.path.exists(COMPANIES_FILE):
        return []
    companies = []
    with open(COMPANIES_FILE, 'r', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                row['company_id'] = int(row.get('company_id')) if row.get('company_id') not in (None, '') else None
                row['consultancy_id'] = int(row.get('consultancy_id')) if row.get('consultancy_id') not in (None, '') else None
            except (ValueError, TypeError):
                pass
            companies.append({
                'company_id': row.get('company_id'), 
                'name': row.get('name',''),
                'consultancy_id': row.get('consultancy_id')
            })
    return companies

def save_company(name, consultancy_id=None):
    """Save a company with consultancy association"""
    fieldnames = ['company_id', 'name', 'consultancy_id']
    companies = load_companies()
    next_id = 1
    if companies:
        try:
            next_id = max([c.get('company_id') or 0 for c in companies]) + 1
        except Exception:
            next_id = len(companies) + 1
    row = {
        'company_id': next_id, 
        'name': name,
        'consultancy_id': consultancy_id
    }
    file_exists = os.path.exists(COMPANIES_FILE)
    with open(COMPANIES_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def load_consultancies():
    """Return list of consultancies as dicts: {'consultancy_id': int, 'name': str, 'bank_details': str, 'notes': str, 'address': str}"""
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
            # normalize multiline fields
            row['bank_details'] = _normalize_multiline(row.get('bank_details', ''))
            row['address'] = _normalize_multiline(row.get('address', ''))
            row['notes'] = (row.get('notes') or '').strip()
            consultancies.append(row)
    return consultancies

def save_consultancy(name, bank_details='', address='', notes=''):
    fieldnames = ['consultancy_id', 'name', 'bank_details', 'address', 'notes']
    consultancies = load_consultancies()
    next_id = 1
    if consultancies:
        try:
            next_id = max([c.get('consultancy_id') or 0 for c in consultancies]) + 1
        except Exception:
            next_id = len(consultancies) + 1
    row = {
        'consultancy_id': next_id, 
        'name': name,
        'bank_details': _normalize_multiline(bank_details),
        'address': _normalize_multiline(address),
        'notes': (notes or '').strip()
    }
    file_exists = os.path.exists(CONSULTANCIES_FILE)
    with open(CONSULTANCIES_FILE, 'a', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

def rewrite_consultancies(consultancies_list):
    """Overwrite consultancies CSV with provided list."""
    fieldnames = ['consultancy_id', 'name', 'bank_details', 'address', 'notes']
    with open(CONSULTANCIES_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for c in consultancies_list:
            writer.writerow({
                'consultancy_id': c.get('consultancy_id') or '',
                'name': c.get('name',''),
                'bank_details': c.get('bank_details',''),
                'address': c.get('address',''),
                'notes': c.get('notes','')
            })


@app.route('/')
def index():
    bills = load_bills()
    companies = load_companies()
    consultancies = load_consultancies()
    # Convert to a concrete list in reversed order so templates (and tojson) can serialize it
    bills_rev = list(reversed(bills))
    return render_template('index.html', bills=bills_rev, companies=companies, consultancies=consultancies)

@app.route('/generate', methods=['POST'])
def generate_bill():
    # Get form data
    client_name = request.form.get('client_name') or ''
    consultancy_name = ''
    consultancy_id = request.form.get('consultancy_id') or ''
    
    # Get consultancy info for billing
    selected_consultancy = None
    if consultancy_id and consultancy_id != 'custom':
        for c in load_consultancies():
            try:
                if str(c.get('consultancy_id')) == str(consultancy_id):
                    consultancy_name = c.get('name') or ''
                    selected_consultancy = c
                    break
            except Exception:
                continue
    
    if not consultancy_name:
        consultancy_name = request.form.get('consultancy_name') or request.form.get('client_name') or ''
        consultancy_id = 'custom'  # Use 'custom' for manually entered consultancies
    
    # Generate bill number using consultancy-specific counter
    bill_number = get_next_bill_number(consultancy_id)
    # Format bill number with consultancy prefix
    formatted_bill_number = f"{consultancy_id}-{bill_number:04d}" if consultancy_id != 'custom' else str(bill_number)

    # Get other form data
    bank_details = _normalize_multiline(request.form.get('bank_details', ''))
    billed_for = request.form.get('billed_for', '')
    
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
    
    # Create bill data with formatted number and consultancy address if available
    bill_data = {
        'bill_number': formatted_bill_number,
        'consultancy_name': consultancy_name,
        'client_name': client_name,
        'billed_for': billed_for,
        'date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'items': items,
        'total': total,
        'bank_details': bank_details,
        'address': selected_consultancy.get('address', '') if selected_consultancy else ''
    }
    
    save_bill(bill_data)
    return render_template('bill_display.html', bill=bill_data)

@app.route('/download_csv')
def download_csv():
    return send_file(BILLS_FILE, as_attachment=True)

@app.route('/bill/<bill_number>')  # Remove int: converter to accept any string
def show_bill(bill_number):
    bills = load_bills()
    for b in bills:
        # Direct string comparison for bill numbers
        if str(b.get('bill_number')) == str(bill_number):
            return render_template('bill_display.html', bill=b)
    # not found
    abort(404)

# Companies management
@app.route('/companies', methods=['GET', 'POST'])
def companies_view():
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        consultancy_id = request.form.get('consultancy_id')
        if name:
            save_company(name, consultancy_id)
        return redirect(url_for('index'))
    companies = load_companies()
    consultancies = load_consultancies()
    return render_template('companies.html', companies=companies, consultancies=consultancies)

@app.route('/api/companies/<consultancy_id>')
def get_companies_for_consultancy(consultancy_id):
    """API endpoint to get companies for a consultancy"""
    companies = load_companies()
    filtered = [c for c in companies if str(c.get('consultancy_id')) == str(consultancy_id)]
    return {'companies': filtered}

# Consultancies management
@app.route('/consultancies', methods=['GET', 'POST'])
def consultancies_view():
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        bank_details = request.form.get('bank_details','')
        address = request.form.get('address','')
        notes = request.form.get('notes','')
        if name:
            save_consultancy(name, bank_details, address, notes)
        return redirect(url_for('index'))
    consultancies = load_consultancies()
    return render_template('consultancies.html', consultancies=consultancies)

def rewrite_bills(bills_list):
    """Overwrite the bills CSV with the provided list of bill dicts."""
    fieldnames = ['bill_number', 'consultancy_name', 'client_name', 'date', 'billed_for', 'items', 'total', 'bank_details']
    with open(BILLS_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in bills_list:
            # items may be a list (loaded) or already a string
            items = row.get('items', '')
            if isinstance(items, list):
                items_str = ';'.join([f"{it.get('description','')}:{it.get('cost',0)}" for it in items])
            else:
                items_str = items
            writer.writerow({
                'bill_number': row.get('bill_number') or '',
                'consultancy_name': row.get('consultancy_name',''),
                'client_name': row.get('client_name',''),
                'date': row.get('date',''),
                'billed_for': row.get('billed_for',''),
                'items': items_str,
                'total': row.get('total',0),
                'bank_details': row.get('bank_details','')
            })


@app.route('/delete_bill/<bill_number>', methods=['POST'])  # Remove int: converter here too
def delete_bill(bill_number):
    bills = load_bills()
    remaining = []
    deleted = False
    for b in bills:
        if str(b.get('bill_number')) == str(bill_number):
            deleted = True
            continue
        remaining.append(b)
    if not deleted:
        abort(404)
    rewrite_bills(remaining)
    return redirect(url_for('index'))

@app.route('/consultancies/edit/<int:consultancy_id>', methods=['GET', 'POST'])
def edit_consultancy(consultancy_id):
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        bank_details = request.form.get('bank_details','')
        address = request.form.get('address','')
        notes = request.form.get('notes','')
        consultancies = load_consultancies()
        updated = False
        for c in consultancies:
            try:
                cid = int(c.get('consultancy_id')) if c.get('consultancy_id') not in (None, '') else None
            except Exception:
                cid = c.get('consultancy_id')
            if cid == consultancy_id:
                c['name'] = name
                c['bank_details'] = _normalize_multiline(bank_details)
                c['address'] = _normalize_multiline(address)
                c['notes'] = (notes or '').strip()
                updated = True
                break
        if not updated:
            abort(404)
        rewrite_consultancies(consultancies)
        return redirect(url_for('consultancies_view'))

    # GET: render edit form
    consultancies = load_consultancies()
    for c in consultancies:
        try:
            cid = int(c.get('consultancy_id')) if c.get('consultancy_id') not in (None, '') else None
        except Exception:
            cid = c.get('consultancy_id')
        if cid == consultancy_id:
            return render_template('consultancies_edit.html', consultancy=c)
    abort(404)

@app.route('/companies/edit/<int:company_id>', methods=['GET', 'POST'])
def edit_company(company_id):
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        consultancy_id = request.form.get('consultancy_id')
        companies = load_companies()
        updated = False
        for c in companies:
            if c.get('company_id') == company_id:
                c['name'] = name
                c['consultancy_id'] = consultancy_id
                updated = True
                break
        if not updated:
            abort(404)
        rewrite_companies(companies)
        return redirect(url_for('companies_view'))

    # GET: render edit form
    companies = load_companies()
    consultancies = load_consultancies()
    for c in companies:
        if c.get('company_id') == company_id:
            return render_template('companies_edit.html', company=c, consultancies=consultancies)
    abort(404)

def rewrite_companies(companies_list):
    """Overwrite companies CSV with provided list."""
    fieldnames = ['company_id', 'name', 'consultancy_id']
    with open(COMPANIES_FILE, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for c in companies_list:
            writer.writerow({
                'company_id': c.get('company_id') or '',
                'name': c.get('name',''),
                'consultancy_id': c.get('consultancy_id','')
            })


if __name__ == '__main__':
    app.run(debug=True)
