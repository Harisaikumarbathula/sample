from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, jsonify
import os
import pandas as pd
import numpy as np
import sqlite3
import json
import threading
from datetime import datetime
from utils.file_handler import load_data, save_data
from modules.validation import suggest_validation_rules, predict_potential_errors, detect_duplicates
from modules.cleaning import handle_missing_values, remove_duplicates
from modules.anomaly import detect_anomalies
from modules.scoring import calculate_quality_score, column_wise_metrics
from utils.report_generator import generate_report
from utils.large_file_handler import analyze_large_file_async, clean_large_file_async, get_file_preview

app = Flask(__name__)
app.secret_key = 'enterprise_data_quality_management_secret_key'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['DATABASE'] = 'database.db'

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

def get_db():
    conn = sqlite3.connect(app.config['DATABASE'], timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                quality_score REAL,
                row_count INTEGER,
                col_count INTEGER
            )
        ''')
        
        # Add columns dynamically if they do not exist
        columns_to_add = {
            'status': 'TEXT DEFAULT "completed"',
            'progress': 'REAL DEFAULT 100.0',
            'error_message': 'TEXT',
            'file_path': 'TEXT',
            'is_large_file': 'INTEGER DEFAULT 0',
            'column_metrics': 'TEXT',
            'suggestions': 'TEXT',
            'anomalies_count': 'INTEGER DEFAULT 0',
            'duplicate_count': 'INTEGER DEFAULT 0',
            'errors': 'TEXT'
        }
        for col_name, col_type in columns_to_add.items():
            try:
                conn.execute(f"ALTER TABLE uploads ADD COLUMN {col_name} {col_type}")
            except sqlite3.OperationalError:
                # Column already exists
                pass
        conn.commit()

init_db()

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

@app.route('/')
def index():
    return render_template('index.html', active_page='upload')

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('No file part', 'danger')
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No selected file', 'danger')
        return redirect(url_for('index'))
    
    if file:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(filepath)
        
        # Save to DB as pending background job
        with get_db() as conn:
            cursor = conn.execute(
                'INSERT INTO uploads (filename, file_path, status, progress, is_large_file) VALUES (?, ?, ?, ?, ?)',
                (file.filename, filepath, 'pending', 0.0, 0)
            )
            upload_id = cursor.lastrowid
            conn.commit()
            
        session['current_file'] = filepath
        session['upload_id'] = upload_id
        
        # Start analysis thread
        threading.Thread(target=analyze_large_file_async, args=(app.config['DATABASE'], upload_id, filepath)).start()
        
        flash(f'File {file.filename} uploaded. Analysis started!', 'info')
        return redirect(url_for('progress_page', upload_id=upload_id))
            
    flash('File upload failed', 'danger')
    return redirect(url_for('index'))

@app.route('/upload_local', methods=['POST'])
def upload_local():
    filepath = request.form.get('filepath')
    if not filepath or not os.path.exists(filepath):
        flash('Invalid or non-existent file path.', 'danger')
        return redirect(url_for('index'))
    
    filename = os.path.basename(filepath)
    
    # Save to DB as pending background job
    with get_db() as conn:
        cursor = conn.execute(
            'INSERT INTO uploads (filename, file_path, status, progress, is_large_file) VALUES (?, ?, ?, ?, ?)',
            (filename, filepath, 'pending', 0.0, 1)
        )
        upload_id = cursor.lastrowid
        conn.commit()
        
    session['current_file'] = filepath
    session['upload_id'] = upload_id
    
    # Start analysis thread
    threading.Thread(target=analyze_large_file_async, args=(app.config['DATABASE'], upload_id, filepath)).start()
    
    flash(f'Local file analysis started for {filename}!', 'info')
    return redirect(url_for('progress_page', upload_id=upload_id))

@app.route('/progress/<int:upload_id>')
def progress_page(upload_id):
    with get_db() as conn:
        upload = conn.execute('SELECT * FROM uploads WHERE id = ?', (upload_id,)).fetchone()
    if not upload:
        flash('Job not found.', 'danger')
        return redirect(url_for('index'))
    return render_template('progress.html', upload_id=upload_id, filename=upload['filename'], active_page='upload')

@app.route('/job_status/<int:upload_id>')
def job_status(upload_id):
    with get_db() as conn:
        upload = conn.execute('SELECT * FROM uploads WHERE id = ?', (upload_id,)).fetchone()
    if not upload:
        return jsonify({'error': 'Job not found'}), 404
        
    return jsonify({
        'status': upload['status'],
        'progress': upload['progress'],
        'error_message': upload['error_message']
    })

@app.route('/dashboard')
def dashboard():
    if 'upload_id' not in session:
        if 'current_file' in session:
            filepath = session['current_file']
            with get_db() as conn:
                upload = conn.execute('SELECT * FROM uploads WHERE file_path = ? ORDER BY id DESC', (filepath,)).fetchone()
                if upload:
                    session['upload_id'] = upload['id']
                else:
                    flash('No analysis record found.', 'warning')
                    return redirect(url_for('index'))
        else:
            flash('Please upload a file first', 'warning')
            return redirect(url_for('index'))
            
    upload_id = session['upload_id']
    with get_db() as conn:
        upload = conn.execute('SELECT * FROM uploads WHERE id = ?', (upload_id,)).fetchone()
        
    if not upload:
        flash('Analysis record not found.', 'danger')
        return redirect(url_for('index'))
        
    if upload['status'] == 'processing' or upload['status'] == 'pending':
        return redirect(url_for('progress_page', upload_id=upload_id))
        
    if upload['status'] == 'failed':
        flash(f"Analysis failed: {upload['error_message']}", 'danger')
        return redirect(url_for('index'))
        
    filepath = upload['file_path']
    quality_score = upload['quality_score']
    row_count = upload['row_count']
    col_count = upload['col_count']
    total_anomalies = upload['anomalies_count']
    total_duplicates = upload['duplicate_count']
    
    # Load JSON metrics, suggestions, errors
    metrics = json.loads(upload['column_metrics']) if upload['column_metrics'] else {}
    suggestions = json.loads(upload['suggestions']) if upload['suggestions'] else {}
    errors = json.loads(upload['errors']) if upload['errors'] else []
    
    # Prepare chart data
    missing_labels = list(metrics.keys())
    missing_values = [m['missing_count'] for m in metrics.values()]
    
    total_cells = row_count * col_count
    total_missing = sum(missing_values)
    missing_percent = round((total_missing / total_cells) * 100, 2) if total_cells > 0 else 0
    duplicate_percent = round((total_duplicates / row_count) * 100, 2) if row_count > 0 else 0

    # Get preview without loading entire 30GB
    table_html = get_file_preview(filepath, nrows=10)

    return render_template('dashboard.html', 
                           active_page='dashboard',
                           file_name=os.path.basename(filepath),
                           row_count=row_count,
                           col_count=col_count,
                           quality_score=quality_score,
                           total_missing=total_missing,
                           missing_percent=missing_percent,
                           total_duplicates=total_duplicates,
                           duplicate_percent=duplicate_percent,
                           total_anomalies=total_anomalies,
                           suggestions=suggestions,
                           missing_labels=missing_labels,
                           missing_values=missing_values,
                           table_html=table_html)

@app.route('/cleaning', methods=['GET', 'POST'])
def cleaning():
    if 'upload_id' not in session:
        flash('Please upload a file first', 'warning')
        return redirect(url_for('index'))
        
    upload_id = session['upload_id']
    with get_db() as conn:
        upload = conn.execute('SELECT * FROM uploads WHERE id = ?', (upload_id,)).fetchone()
        
    if not upload:
        flash('Analysis record not found.', 'danger')
        return redirect(url_for('index'))
        
    if upload['status'] == 'processing' or upload['status'] == 'pending':
        return redirect(url_for('progress_page', upload_id=upload_id))
        
    filepath = upload['file_path']
    metrics = json.loads(upload['column_metrics']) if upload['column_metrics'] else {}
    columns = list(metrics.keys())
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        # Prepare output path
        dir_name = app.config['OUTPUT_FOLDER']
        base_name = os.path.basename(filepath)
        if not base_name.startswith('cleaned_'):
            output_filename = f"cleaned_{base_name}"
        else:
            output_filename = base_name
        output_filepath = os.path.join(dir_name, output_filename)
        
        # If output filepath exists, we delete it to start fresh
        if os.path.exists(output_filepath):
            try:
                os.remove(output_filepath)
            except Exception:
                pass
                
        operations = {}
        if action == 'remove_duplicates':
            operations['remove_duplicates'] = True
            flash('Deduplication job started in background!', 'info')
        elif action == 'fill_missing':
            col = request.form.get('column')
            strategy = request.form.get('strategy')
            operations['fill_missing'] = {'column': col, 'strategy': strategy}
            flash(f'Missing value imputation job for column {col} started in background!', 'info')
            
        # Update job status in database to trigger progress screen
        with get_db() as conn:
            conn.execute('UPDATE uploads SET status = "processing", progress = 0.0 WHERE id = ?', (upload_id,))
            conn.commit()
            
        # Spawn cleaning background thread
        threading.Thread(
            target=clean_large_file_async,
            args=(app.config['DATABASE'], upload_id, filepath, output_filepath, operations)
        ).start()
        
        return redirect(url_for('progress_page', upload_id=upload_id))
        
    # GET: render preview of first 10 rows
    table_html = get_file_preview(filepath, nrows=10)
    return render_template('cleaning.html', 
                           active_page='cleaning',
                           columns=columns,
                           table_html=table_html)

@app.route('/reports')
def reports():
    if 'upload_id' not in session:
        flash('Please upload a file first', 'warning')
        return redirect(url_for('index'))
        
    upload_id = session['upload_id']
    with get_db() as conn:
        upload = conn.execute('SELECT * FROM uploads WHERE id = ?', (upload_id,)).fetchone()
        
    if not upload:
        flash('Analysis record not found.', 'danger')
        return redirect(url_for('index'))
        
    if upload['status'] == 'processing' or upload['status'] == 'pending':
        return redirect(url_for('progress_page', upload_id=upload_id))
        
    filepath = upload['file_path']
    quality_score = upload['quality_score']
    row_count = upload['row_count']
    col_count = upload['col_count']
    duplicate_count = upload['duplicate_count']
    
    metrics = json.loads(upload['column_metrics']) if upload['column_metrics'] else {}
    errors = json.loads(upload['errors']) if upload['errors'] else []
    
    report_path = generate_report(
        os.path.basename(filepath),
        metrics,
        quality_score,
        errors,
        row_count,
        col_count,
        duplicate_count
    )
    
    return render_template('reports.html', 
                           active_page='reports',
                           report_ready=True,
                           report_filename=os.path.basename(report_path))

@app.route('/download_report/<filename>')
def download_report(filename):
    return send_file(os.path.join(app.config['OUTPUT_FOLDER'], filename), as_attachment=True)

@app.route('/download_data')
def download_data():
    if 'upload_id' not in session:
        return redirect(url_for('index'))
    with get_db() as conn:
        upload = conn.execute('SELECT * FROM uploads WHERE id = ?', (session['upload_id'],)).fetchone()
    if not upload or not upload['file_path']:
        return redirect(url_for('index'))
    return send_file(upload['file_path'], as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
